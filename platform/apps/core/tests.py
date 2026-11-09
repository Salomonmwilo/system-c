"""Tests du socle : authentification, permissions, organisations, audit, sécurité, i18n."""

import re
from pathlib import Path

from django.conf import settings
from django.core.cache import cache
from django.db import DatabaseError, connection, transaction
from django.test import TestCase, override_settings
from django.urls import URLPattern, URLResolver, get_resolver, reverse
from django.utils import translation

from apps.core import audit
from apps.core.models import AuditLog, Membership, OrganizationSettings, Role, User
from apps.core.permissions import PERMISSIONS, OrgPermissionRequiredMixin, roles_have_perm
from apps.core.testing import PASSWORD, login, make_org, make_user


class AuthenticationTests(TestCase):
    def setUp(self):
        cache.clear()
        self.org = make_org()
        self.user = make_user(self.org, Role.CRM_ADMIN, email="Admin@Example.org", language="en")

    def test_login_success_redirects_and_sets_language(self):
        response = self.client.post(reverse("core:login"), {"email": "admin@example.org", "password": PASSWORD})
        self.assertRedirects(response, reverse("core:dashboard"), fetch_redirect_response=False)
        self.assertEqual(response.cookies[settings.LANGUAGE_COOKIE_NAME].value, "en")
        self.assertTrue(AuditLog.objects.filter(action="login", actor=self.user).exists())

    def test_login_is_case_insensitive(self):
        response = self.client.post(reverse("core:login"), {"email": "ADMIN@example.ORG", "password": PASSWORD})
        self.assertEqual(response.status_code, 302)

    def test_wrong_password_and_unknown_account_give_same_message(self):
        wrong = self.client.post(reverse("core:login"), {"email": "admin@example.org", "password": "nope-nope-nope"})
        unknown = self.client.post(reverse("core:login"), {"email": "ghost@example.org", "password": "nope-nope-nope"})
        self.assertEqual(wrong.status_code, 200)
        self.assertEqual(wrong.context["form"].non_field_errors(), unknown.context["form"].non_field_errors())

    @override_settings(LOGIN_MAX_ATTEMPTS_PER_ACCOUNT=3)
    def test_login_is_throttled_after_repeated_failures(self):
        for _ in range(3):
            self.client.post(reverse("core:login"), {"email": "admin@example.org", "password": "bad-password-x"})
        response = self.client.post(reverse("core:login"), {"email": "admin@example.org", "password": PASSWORD})
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.wsgi_request.user.is_authenticated)
        self.assertTrue(AuditLog.objects.filter(action="login_throttled").exists())

    def test_inactive_user_cannot_sign_in(self):
        self.user.is_active = False
        self.user.save()
        response = self.client.post(reverse("core:login"), {"email": "admin@example.org", "password": PASSWORD})
        self.assertEqual(response.status_code, 200)

    def test_logout_requires_post(self):
        login(self.client, self.user, self.org)
        self.assertEqual(self.client.get(reverse("core:logout")).status_code, 405)
        response = self.client.post(reverse("core:logout"))
        self.assertRedirects(response, reverse("core:login"), fetch_redirect_response=False)
        self.assertEqual(self.client.get(reverse("core:dashboard")).status_code, 302)

    def test_passwords_are_hashed_with_argon2(self):
        self.assertTrue(self.user.password.startswith("argon2"))

    def test_login_redirect_ignores_external_next(self):
        response = self.client.post(
            reverse("core:login"), {"email": "admin@example.org", "password": PASSWORD, "next": "https://evil.example/"}
        )
        self.assertEqual(response["Location"], reverse("core:dashboard"))


def iter_patterns(resolver=None, prefix=""):
    resolver = resolver or get_resolver()
    for pattern in resolver.url_patterns:
        if isinstance(pattern, URLResolver):
            yield from iter_patterns(pattern, prefix + str(pattern.pattern))
        elif isinstance(pattern, URLPattern):
            yield prefix + str(pattern.pattern), pattern


class RouteProtectionTests(TestCase):
    """Chaque route est soit explicitement publique, soit protégée par une permission déclarée."""

    def test_every_route_declares_its_protection(self):
        unprotected = []
        for route, pattern in iter_patterns():
            callback = pattern.callback
            view_class = getattr(callback, "view_class", None)
            if getattr(callback, "public", False) or getattr(view_class, "public", False):
                continue
            if view_class is not None and issubclass(view_class, OrgPermissionRequiredMixin):
                perms = view_class.permission_required
                perms = (perms,) if isinstance(perms, str) else perms
                if perms and all(p in PERMISSIONS for p in perms):
                    continue
            unprotected.append(route)
        self.assertEqual(unprotected, [], "Routes sans permission déclarée")

    def test_anonymous_users_are_redirected_to_login(self):
        dummy = "00000000-0000-0000-0000-000000000000"
        for route, pattern in iter_patterns():
            view_class = getattr(pattern.callback, "view_class", None)
            if view_class is None or not issubclass(view_class, OrgPermissionRequiredMixin):
                continue
            url = "/" + re.sub(r"<uuid:\w+>", dummy, re.sub(r"<int:\w+>", "1", re.sub(r"<str:\w+>", "x", route)))
            for method in ("get", "post"):
                response = getattr(self.client, method)(url)
                self.assertIn(response.status_code, (302, 405), f"{method.upper()} {url}")
                if response.status_code == 302:
                    self.assertTrue(response["Location"].startswith(reverse("core:login")), url)


class OrganizationAccessTests(TestCase):
    def test_user_without_membership_has_no_access(self):
        user = make_user()
        login(self.client, user)
        response = self.client.get(reverse("core:dashboard"))
        self.assertRedirects(response, reverse("core:no_organization"), fetch_redirect_response=False)

    def test_superuser_status_gives_no_organization_data(self):
        org = make_org()
        superuser = User.objects.create_superuser(email="root@example.org", password=PASSWORD, full_name="Root")
        login(self.client, superuser)
        self.assertRedirects(self.client.get(reverse("partners:affiliate_list")), reverse("core:no_organization"), fetch_redirect_response=False)
        self.assertFalse(Membership.objects.filter(user=superuser, organization=org).exists())

    def test_cannot_switch_to_an_organization_without_membership(self):
        org_a, org_b = make_org(), make_org()
        user = make_user(org_a, Role.CRM_ADMIN)
        login(self.client, user, org_a)
        self.client.post(reverse("core:switch_organization"), {"organization": str(org_b.pk)})
        response = self.client.get(reverse("core:dashboard"))
        self.assertEqual(response.wsgi_request.organization, org_a)

    def test_switch_between_own_organizations(self):
        org_a, org_b = make_org("A"), make_org("B")
        user = make_user(org_a, Role.CRM_ADMIN)
        Membership.objects.create(user=user, organization=org_b, role=Role.CRM_VIEWER)
        login(self.client, user, org_a)
        self.client.post(reverse("core:switch_organization"), {"organization": str(org_b.pk)})
        response = self.client.get(reverse("core:dashboard"))
        self.assertEqual(response.wsgi_request.organization, org_b)
        self.assertEqual(response.wsgi_request.org_roles, frozenset({Role.CRM_VIEWER}))

    def test_roles_from_another_organization_do_not_apply(self):
        org_a, org_b = make_org(), make_org()
        user = make_user(org_a, Role.CRM_ADMIN)
        Membership.objects.create(user=user, organization=org_b, role=Role.ACADEMY_STUDENT)
        login(self.client, user, org_b)
        self.assertEqual(self.client.get(reverse("partners:affiliate_list")).status_code, 403)


class PermissionPolicyTests(TestCase):
    def test_unknown_permission_is_denied(self):
        self.assertFalse(roles_have_perm({Role.CRM_ADMIN, Role.ORG_ADMIN}, "bots.launch_rocket"))

    def test_only_crm_admin_can_manage_real_accounts(self):
        allowed = [role for role in Role.values if roles_have_perm({role}, "bots.manage_real")]
        self.assertEqual(allowed, [Role.CRM_ADMIN])

    def test_validation_reserved_to_crm_admin(self):
        allowed = [role for role in Role.values if roles_have_perm({role}, "bots.validate_version")]
        self.assertEqual(allowed, [Role.CRM_ADMIN])

    def test_viewer_is_read_only(self):
        write_perms = [p for p in PERMISSIONS if not p.split(".")[1].startswith("view")]
        granted = [p for p in write_perms if roles_have_perm({Role.CRM_VIEWER}, p)]
        self.assertEqual(granted, [])

    def test_academy_roles_have_no_crm_access(self):
        for role in (Role.ACADEMY_STUDENT, Role.ACADEMY_INSTRUCTOR):
            granted = [p for p in PERMISSIONS if roles_have_perm({role}, p)]
            self.assertEqual(granted, ["academy.view"])

    def test_student_gets_403_on_crm_pages(self):
        org = make_org()
        student = make_user(org, Role.ACADEMY_STUDENT)
        login(self.client, student, org)
        self.assertEqual(self.client.get(reverse("academy:home")).status_code, 200)
        for name in ("core:dashboard", "partners:affiliate_list", "bots:botuser_list", "core:members"):
            self.assertEqual(self.client.get(reverse(name)).status_code, 403, name)


class MemberManagementTests(TestCase):
    def setUp(self):
        self.org = make_org()
        self.admin = make_user(self.org, Role.ORG_ADMIN)

    def test_org_admin_creates_member_with_roles(self):
        login(self.client, self.admin, self.org)
        response = self.client.post(
            reverse("core:member_create"),
            {"email": "New@Example.org", "full_name": "Nouvelle Personne", "preferred_language": "fr",
             "roles": [Role.CRM_OPERATOR], "password": "A-strong-pass-2026"},
        )
        self.assertRedirects(response, reverse("core:members"), fetch_redirect_response=False)
        user = User.objects.get(email="new@example.org")
        self.assertEqual(set(user.memberships.values_list("role", flat=True)), {Role.CRM_OPERATOR})
        self.assertTrue(AuditLog.objects.filter(action="member_created", organization=self.org).exists())

    def test_weak_password_rejected(self):
        login(self.client, self.admin, self.org)
        response = self.client.post(
            reverse("core:member_create"),
            {"email": "weak@example.org", "full_name": "Weak", "preferred_language": "fr", "roles": [Role.CRM_VIEWER], "password": "12345678"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(email="weak@example.org").exists())

    def test_non_admin_cannot_manage_members(self):
        operator = make_user(self.org, Role.CRM_ADMIN)
        login(self.client, operator, self.org)
        self.assertEqual(self.client.get(reverse("core:members")).status_code, 403)

    def test_admin_cannot_remove_own_admin_role(self):
        login(self.client, self.admin, self.org)
        self.client.post(reverse("core:member_roles", args=[self.admin.pk]), {"roles": [Role.CRM_VIEWER]})
        self.assertTrue(Membership.objects.filter(user=self.admin, role=Role.ORG_ADMIN).exists())

    def test_roles_page_of_foreign_user_is_404(self):
        other_org = make_org()
        stranger = make_user(other_org, Role.CRM_ADMIN)
        login(self.client, self.admin, self.org)
        self.assertEqual(self.client.get(reverse("core:member_roles", args=[stranger.pk])).status_code, 404)


class ThresholdTests(TestCase):
    def setUp(self):
        self.org = make_org()
        self.admin = make_user(self.org, Role.CRM_ADMIN)
        self.data = {"contact_stale_days": 45, "modification_pending_days": 5, "configuration_review_days": 60,
                     "registration_stuck_days": 10, "verification_stuck_days": 20, "default_currency": "usd"}

    def test_crm_admin_updates_thresholds_and_change_is_audited(self):
        login(self.client, self.admin, self.org)
        self.client.post(reverse("core:thresholds"), self.data)
        settings_obj = OrganizationSettings.for_organization(self.org)
        self.assertEqual(settings_obj.contact_stale_days, 45)
        self.assertEqual(settings_obj.default_currency, "USD")
        entry = AuditLog.objects.get(action="thresholds_changed")
        self.assertEqual(entry.summary["contact_stale_days_after"], 45)

    def test_out_of_bounds_threshold_rejected(self):
        login(self.client, self.admin, self.org)
        response = self.client.post(reverse("core:thresholds"), dict(self.data, contact_stale_days=2))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(OrganizationSettings.for_organization(self.org).contact_stale_days, 30)

    def test_operator_cannot_change_thresholds(self):
        operator = make_user(self.org, Role.CRM_OPERATOR)
        login(self.client, operator, self.org)
        self.assertEqual(self.client.post(reverse("core:thresholds"), self.data).status_code, 403)


class AuditLogTests(TestCase):
    def test_sanitize_drops_secret_like_keys_and_notes(self):
        clean = audit.sanitize({"token": "abc", "api_key": "x", "Password": "y", "note": "long", "fields": ["a"], "n": 3})
        self.assertEqual(clean, {"fields": ["a"], "n": 3})

    def test_audit_entries_are_append_only_in_python(self):
        entry = audit.record("test_action")
        with self.assertRaises(PermissionError):
            entry.save()
        with self.assertRaises(PermissionError):
            entry.delete()

    def test_audit_entries_are_append_only_in_database(self):
        entry = audit.record("test_action")
        with self.assertRaises(DatabaseError), transaction.atomic():
            AuditLog.objects.filter(pk=entry.pk).update(action="tampered")
        with self.assertRaises(DatabaseError), transaction.atomic():
            with connection.cursor() as cursor:
                cursor.execute("DELETE FROM core_auditlog WHERE id = %s", [entry.pk])
        self.assertEqual(AuditLog.objects.get(pk=entry.pk).action, "test_action")


class SecurityHeaderTests(TestCase):
    def test_security_headers_on_public_and_private_pages(self):
        response = self.client.get(reverse("core:login"))
        self.assertIn("default-src 'self'", response["Content-Security-Policy"])
        self.assertIn("frame-ancestors 'none'", response["Content-Security-Policy"])
        self.assertEqual(response["X-Frame-Options"], "DENY")
        self.assertEqual(response["X-Content-Type-Options"], "nosniff")
        org = make_org()
        login(self.client, make_user(org, Role.CRM_ADMIN), org)
        self.assertEqual(self.client.get(reverse("core:dashboard"))["Cache-Control"], "no-store")

    def test_templates_have_no_inline_script_or_style(self):
        base = Path(settings.BASE_DIR)
        offenders = []
        for path in list((base / "templates").rglob("*.html")) + list((base / "apps").rglob("templates/**/*.html")):
            text = path.read_text(encoding="utf-8")
            if re.search(r"<script(?![^>]*\bsrc=)[^>]*>", text) or re.search(r'\sstyle="', text) or re.search(r"\son[a-z]+=", text):
                offenders.append(str(path.relative_to(base)))
        self.assertEqual(offenders, [])


class LanguageTests(TestCase):
    def setUp(self):
        self.org = make_org()
        self.user = make_user(self.org, Role.CRM_ADMIN, language="fr")
        login(self.client, self.user, self.org)

    def test_french_is_the_default(self):
        response = self.client.get(reverse("core:dashboard"))
        self.assertContains(response, "Tableau de bord")
        self.assertContains(response, 'lang="fr"')

    def test_switch_to_english_updates_preference_and_cookie(self):
        response = self.client.post(reverse("core:switch_language"), {"language": "en", "next": reverse("partners:affiliate_list")})
        self.assertRedirects(response, reverse("partners:affiliate_list"), fetch_redirect_response=False)
        self.user.refresh_from_db()
        self.assertEqual(self.user.preferred_language, "en")
        page = self.client.get(reverse("core:dashboard"))
        self.assertContains(page, "Dashboard")
        self.assertContains(page, 'lang="en"')

    def test_language_switch_rejects_external_redirect(self):
        response = self.client.post(reverse("core:switch_language"), {"language": "en", "next": "https://evil.example/"})
        self.assertEqual(response["Location"], reverse("core:dashboard"))

    def test_french_catalog_is_complete(self):
        po = Path(settings.BASE_DIR) / "locale" / "fr" / "LC_MESSAGES" / "django.po"
        text = po.read_text(encoding="utf-8")
        self.assertNotIn("#, fuzzy\nmsgid \"", text.split("\n\n", 1)[1])
        empty = re.findall(r'\nmsgid "(.+)"\nmsgstr ""\n(?!")', text)
        self.assertEqual(empty, [])
        self.assertTrue((po.with_suffix(".mo")).exists())
        with translation.override("fr"):
            self.assertEqual(translation.gettext("Robot users"), "Utilisateurs de robots")


class DesignRevisionTests(TestCase):
    """Garde-fous issus de l'audit d'ergonomie (docs/platform/DESIGN_AUDIT.md)."""

    def setUp(self):
        self.org = make_org()
        self.admin = make_user(self.org, Role.CRM_ADMIN, Role.ORG_ADMIN)
        login(self.client, self.admin, self.org)

    def test_dashboard_ledger_lists_actions_first_by_urgency(self):
        from django.utils import timezone

        from apps.partners import services as partner_services

        affiliate = partner_services.create_affiliate(organization=self.org, actor=self.admin, data={"display_name": "Relance"})
        partner_services.create_followup(affiliate=affiliate, actor=self.admin, title="x",
                                         due_on=timezone.localdate() - timezone.timedelta(days=2))
        response = self.client.get(reverse("core:dashboard"))
        priorities = response.context["priorities"]
        self.assertEqual(priorities[0]["count"], 1)
        self.assertTrue(priorities[0]["urgent"])
        self.assertEqual(priorities[0]["rank"], 10)
        counts = [item["count"] for item in priorities]
        self.assertEqual(counts, sorted(counts, key=lambda c: c == 0))
        self.assertContains(response, "À traiter")
        self.assertContains(response, "Relance à effectuer aujourd")

    def test_irreversible_actions_ask_for_confirmation(self):
        base = Path(settings.BASE_DIR)
        expected = {
            "apps/bots/templates/bots/version_form.html": "bots:version_delete",
            "apps/bots/templates/bots/botuser_detail.html": "'disable'",
            "apps/bots/templates/bots/version_detail.html": "bots:declaration_correct",
            "apps/partners/templates/partners/affiliate_detail.html": 'value="archive"',
        }
        for path, marker in expected.items():
            text = (base / path).read_text(encoding="utf-8")
            line = next(line for line in text.splitlines() if marker in line)
            self.assertIn("data-confirm=", line, path)
        script = (base / "static/js/systemc.js").read_text(encoding="utf-8")
        self.assertIn("window.confirm", script)

    def test_fonts_are_local_and_licensed(self):
        base = Path(settings.BASE_DIR) / "static"
        css = (base / "css/systemc.css").read_text(encoding="utf-8")
        for url in re.findall(r'url\("([^"]+)"\)', css):
            self.assertFalse(url.startswith(("http:", "https:", "//")), url)
            self.assertTrue((base / "css" / url).resolve().exists(), url)
        self.assertTrue((base / "vendor/fonts/LICENSE-IBM-Plex-Sans.txt").exists())
        self.assertTrue((base / "vendor/fonts/LICENSE-Source-Serif-4.txt").exists())
