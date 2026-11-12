"""Tests du module partners : fiches, parcours, interactions, relances, alertes, isolation."""

import ast
import datetime as dt
from pathlib import Path

from django.core.exceptions import ValidationError
from django.db import DatabaseError, transaction
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.core.models import AuditLog, OrganizationSettings, Role
from apps.core.testing import login, make_org, make_user

from . import services
from .models import Affiliate, FollowUp, Interaction, TrackEvent


def make_affiliate(org, actor, **fields) -> Affiliate:
    data = {"display_name": fields.pop("display_name", "Affilié test"), **fields}
    return services.create_affiliate(organization=org, actor=actor, data=data)


class AffiliateCrudTests(TestCase):
    def setUp(self):
        self.org = make_org()
        self.manager = make_user(self.org, Role.PARTNER_MANAGER)
        login(self.client, self.manager, self.org)

    def test_create_affiliate_through_the_form(self):
        response = self.client.post(
            reverse("partners:affiliate_create"),
            {"display_name": "Grace M.", "email": "Grace@Example.org", "phone": "+243 000", "country": "cd",
             "preferred_language": "fr", "status": "active"},
        )
        affiliate = Affiliate.objects.get(display_name="Grace M.")
        self.assertRedirects(response, reverse("partners:affiliate_detail", args=[affiliate.pk]), fetch_redirect_response=False)
        self.assertEqual(affiliate.organization, self.org)
        self.assertEqual(affiliate.email, "grace@example.org")
        self.assertEqual(affiliate.country, "CD")
        self.assertTrue(AuditLog.objects.filter(action="affiliate_created", target_id=str(affiliate.pk)).exists())

    def test_duplicate_email_rejected_in_same_organization_only(self):
        make_affiliate(self.org, self.manager, email="same@example.org")
        response = self.client.post(
            reverse("partners:affiliate_create"),
            {"display_name": "Doublon", "email": "SAME@example.org", "preferred_language": "fr", "status": "active"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Affiliate.objects.filter(email__iexact="same@example.org").count(), 1)
        other = make_org()
        make_affiliate(other, make_user(other, Role.PARTNER_MANAGER), email="same@example.org")
        self.assertEqual(Affiliate.objects.filter(email__iexact="same@example.org").count(), 2)

    def test_update_records_changed_field_names_only(self):
        affiliate = make_affiliate(self.org, self.manager, email="a@example.org")
        self.client.post(
            reverse("partners:affiliate_update", args=[affiliate.pk]),
            {"display_name": "Nouveau nom", "email": "a@example.org", "preferred_language": "en", "status": "active"},
        )
        affiliate.refresh_from_db()
        self.assertEqual(affiliate.display_name, "Nouveau nom")
        entry = AuditLog.objects.get(action="affiliate_updated")
        self.assertEqual(sorted(entry.summary["fields"]), ["display_name", "preferred_language"])
        self.assertNotIn("Nouveau nom", str(entry.summary))

    def test_archive_and_restore(self):
        affiliate = make_affiliate(self.org, self.manager)
        self.client.post(reverse("partners:affiliate_archive", args=[affiliate.pk]), {"action": "archive"})
        affiliate.refresh_from_db()
        self.assertIsNotNone(affiliate.archived_at)
        self.assertNotContains(self.client.get(reverse("partners:affiliate_list")), affiliate.display_name)
        self.assertContains(self.client.get(reverse("partners:affiliate_list") + "?archived=on"), affiliate.display_name)
        self.client.post(reverse("partners:affiliate_archive", args=[affiliate.pk]), {"action": "restore"})
        affiliate.refresh_from_db()
        self.assertIsNone(affiliate.archived_at)

    def test_detail_page_shows_history(self):
        affiliate = make_affiliate(self.org, self.manager, display_name="Fiche complète")
        services.add_interaction(affiliate=affiliate, actor=self.manager, kind="call", occurred_at=timezone.now(), summary="Premier appel")
        response = self.client.get(reverse("partners:affiliate_detail", args=[affiliate.pk]))
        self.assertContains(response, "Fiche complète")
        self.assertContains(response, "Premier appel")


class VisibilityTests(TestCase):
    def setUp(self):
        self.org = make_org()
        self.manager = make_user(self.org, Role.PARTNER_MANAGER)
        self.advisor = make_user(self.org, Role.PARTNER_ADVISOR)
        self.mine = make_affiliate(self.org, self.manager, display_name="Suivi par moi", assigned_to=self.advisor)
        self.other = make_affiliate(self.org, self.manager, display_name="Pas pour moi", email="hidden@example.org")

    def test_advisor_sees_only_assigned_affiliates(self):
        login(self.client, self.advisor, self.org)
        listing = self.client.get(reverse("partners:affiliate_list"))
        self.assertContains(listing, "Suivi par moi")
        self.assertNotContains(listing, "Pas pour moi")
        self.assertEqual(self.client.get(reverse("partners:affiliate_detail", args=[self.other.pk])).status_code, 404)
        self.assertEqual(self.client.get(reverse("partners:affiliate_detail", args=[self.mine.pk])).status_code, 200)

    def test_viewer_sees_masked_personal_data_and_cannot_create(self):
        viewer = make_user(self.org, Role.CRM_VIEWER)
        login(self.client, viewer, self.org)
        listing = self.client.get(reverse("partners:affiliate_list"))
        self.assertContains(listing, "h•••@example.org")
        self.assertNotContains(listing, "hidden@example.org")
        self.assertEqual(self.client.get(reverse("partners:affiliate_create")).status_code, 403)
        self.assertEqual(self.client.post(reverse("partners:affiliate_update", args=[self.other.pk]), {}).status_code, 403)

    def test_viewer_search_does_not_match_on_hidden_email(self):
        viewer = make_user(self.org, Role.CRM_VIEWER)
        login(self.client, viewer, self.org)
        self.assertNotContains(self.client.get(reverse("partners:affiliate_list") + "?q=hidden"), "Pas pour moi")


class TrackTests(TestCase):
    def setUp(self):
        self.org = make_org()
        self.operator = make_user(self.org, Role.CRM_OPERATOR, Role.PARTNER_MANAGER)
        self.affiliate = make_affiliate(self.org, self.operator)

    def test_record_track_updates_current_status_and_history(self):
        services.record_track(
            affiliate=self.affiliate, actor=self.operator, track="verification", value="in_progress",
            declared_on=timezone.localdate(), source="deriv_support", note="Pièces envoyées",
        )
        self.affiliate.refresh_from_db()
        self.assertEqual(self.affiliate.verification_status, "in_progress")
        event = TrackEvent.objects.get(affiliate=self.affiliate)
        self.assertEqual((event.previous_value, event.value), ("not_requested", "in_progress"))

    def test_invalid_value_and_future_date_are_rejected(self):
        with self.assertRaises(ValidationError):
            services.record_track(affiliate=self.affiliate, actor=self.operator, track="verification",
                                  value="account_created", declared_on=timezone.localdate(), source="administrator")
        with self.assertRaises(ValidationError):
            services.record_track(affiliate=self.affiliate, actor=self.operator, track="registration", value="declared_by_affiliate",
                                  declared_on=timezone.localdate() + dt.timedelta(days=1), source="administrator")

    def test_track_view_with_prefixed_form(self):
        login(self.client, self.operator, self.org)
        self.client.post(
            reverse("partners:affiliate_track", args=[self.affiliate.pk, "registration"]),
            {"track-registration-value": "account_created", "track-registration-declared_on": timezone.localdate().isoformat(),
             "track-registration-source": "affiliate", "track-registration-note": ""},
        )
        self.affiliate.refresh_from_db()
        self.assertEqual(self.affiliate.registration_status, "account_created")

    def test_history_is_append_only(self):
        event = services.record_track(affiliate=self.affiliate, actor=self.operator, track="demo", value="opened",
                                      declared_on=timezone.localdate(), source="affiliate")
        with self.assertRaises(DatabaseError), transaction.atomic():
            TrackEvent.objects.filter(pk=event.pk).update(value="not_opened")


class InteractionAndFollowUpTests(TestCase):
    def setUp(self):
        self.org = make_org()
        self.operator = make_user(self.org, Role.CRM_OPERATOR)
        self.affiliate = make_affiliate(self.org, make_user(self.org, Role.PARTNER_MANAGER))

    def test_contacts_update_last_contact_but_internal_notes_do_not(self):
        services.add_interaction(affiliate=self.affiliate, actor=self.operator, kind="note",
                                 occurred_at=timezone.now(), summary="Note interne")
        self.assertIsNone(self.affiliate.last_contact_at)
        when = timezone.now() - dt.timedelta(hours=2)
        services.add_interaction(affiliate=self.affiliate, actor=self.operator, kind="call", occurred_at=when, summary="Appel")
        self.assertEqual(self.affiliate.last_contact_at, when)
        older = when - dt.timedelta(days=3)
        services.add_interaction(affiliate=self.affiliate, actor=self.operator, kind="message", occurred_at=older, summary="Ancien")
        self.assertEqual(self.affiliate.last_contact_at, when)

    def test_interactions_are_append_only(self):
        interaction = services.add_interaction(affiliate=self.affiliate, actor=self.operator, kind="call",
                                               occurred_at=timezone.now(), summary="x")
        with self.assertRaises(DatabaseError), transaction.atomic():
            Interaction.objects.filter(pk=interaction.pk).delete()

    def test_schedule_and_close_followup_through_views(self):
        login(self.client, self.operator, self.org)
        self.client.post(reverse("partners:followup_create", args=[self.affiliate.pk]),
                         {"title": "Rappeler", "due_on": timezone.localdate().isoformat(), "note": ""})
        followup = FollowUp.objects.get(affiliate=self.affiliate)
        self.assertContains(self.client.get(reverse("partners:followup_list")), "Rappeler")
        self.client.post(reverse("partners:followup_close", args=[followup.pk]), {"status": "done"})
        followup.refresh_from_db()
        self.assertEqual(followup.status, FollowUp.Status.DONE)
        with self.assertRaises(ValidationError):
            services.close_followup(followup=followup, actor=self.operator, status="done")


class AlertTests(TestCase):
    def setUp(self):
        self.org = make_org()
        self.user = make_user(self.org, Role.PARTNER_MANAGER)
        self.settings = OrganizationSettings.for_organization(self.org)

    def _aged(self, days, **fields):
        affiliate = make_affiliate(self.org, self.user, **fields)
        Affiliate.objects.filter(pk=affiliate.pk).update(created_at=timezone.now() - dt.timedelta(days=days))
        return Affiliate.objects.get(pk=affiliate.pk)

    def test_contact_stale_respects_threshold(self):
        old = self._aged(40, display_name="Ancien")
        recent = self._aged(40, display_name="Contacté")
        services.add_interaction(affiliate=recent, actor=self.user, kind="call", occurred_at=timezone.now(), summary="ok")
        self._aged(5, display_name="Nouveau")
        qs = Affiliate.objects.filter(organization=self.org)
        self.assertEqual(list(services.contact_stale(qs, self.settings)), [old])
        self.settings.contact_stale_days = 60
        self.assertEqual(list(services.contact_stale(qs, self.settings)), [])

    def test_registration_and_verification_stuck(self):
        stuck = self._aged(20, display_name="Bloqué")
        verif = self._aged(30, display_name="Vérif")
        services.record_track(affiliate=verif, actor=self.user, track="registration", value="account_created",
                              declared_on=timezone.localdate() - dt.timedelta(days=25), source="affiliate")
        services.record_track(affiliate=verif, actor=self.user, track="verification", value="requested",
                              declared_on=timezone.localdate() - dt.timedelta(days=20), source="affiliate")
        qs = Affiliate.objects.filter(organization=self.org)
        self.assertEqual(list(services.registration_stuck(qs, self.settings)), [stuck])
        self.assertEqual(list(services.verification_stuck(qs, self.settings)), [verif])

    def test_dashboard_shows_real_counts(self):
        make_affiliate(self.org, self.user, status="active")
        make_affiliate(self.org, self.user, status="prospect")
        archived = make_affiliate(self.org, self.user, status="active")
        services.set_archived(affiliate=archived, actor=self.user, archived=True)
        login(self.client, self.user, self.org)
        response = self.client.get(reverse("core:dashboard"))
        section = next(s for s in response.context["sections"] if s["template"] == "partners/dashboard_section.html")
        self.assertEqual(section["context"]["total"], 2)
        self.assertEqual(section["context"]["active"], 1)
        self.assertEqual(section["context"]["prospects"], 1)
        self.assertEqual(section["context"]["registration_pending"], 2)


class IsolationTests(TestCase):
    """Un utilisateur d'une autre organisation reçoit 404 sur chaque ressource."""

    def setUp(self):
        self.org_a, self.org_b = make_org(), make_org()
        owner = make_user(self.org_a, Role.PARTNER_MANAGER)
        self.affiliate = make_affiliate(self.org_a, owner)
        self.followup = services.create_followup(affiliate=self.affiliate, actor=owner, title="x", due_on=timezone.localdate())
        self.intruder = make_user(self.org_b, Role.CRM_ADMIN, Role.ORG_ADMIN)
        login(self.client, self.intruder, self.org_b)

    def test_foreign_affiliate_is_invisible(self):
        pk = self.affiliate.pk
        self.assertEqual(self.client.get(reverse("partners:affiliate_detail", args=[pk])).status_code, 404)
        self.assertEqual(self.client.get(reverse("partners:affiliate_update", args=[pk])).status_code, 404)
        self.assertEqual(self.client.post(reverse("partners:affiliate_archive", args=[pk])).status_code, 404)
        self.assertEqual(self.client.post(reverse("partners:affiliate_track", args=[pk, "registration"])).status_code, 404)
        self.assertEqual(self.client.post(reverse("partners:interaction_create", args=[pk])).status_code, 404)
        self.assertEqual(self.client.post(reverse("partners:followup_create", args=[pk])).status_code, 404)
        self.assertEqual(self.client.post(reverse("partners:followup_close", args=[self.followup.pk]), {"status": "done"}).status_code, 404)
        self.assertNotContains(self.client.get(reverse("partners:affiliate_list")), self.affiliate.display_name)

    def test_cannot_attach_foreign_referral_link_or_assignee(self):
        from .models import ReferralLink

        link = ReferralLink.objects.create(organization=self.org_a, label="A", url="https://t.example/a", created_by=self.affiliate.created_by)
        response = self.client.post(
            reverse("partners:affiliate_create"),
            {"display_name": "Test", "preferred_language": "fr", "status": "active", "referral_link": str(link.pk),
             "assigned_to": str(self.affiliate.created_by.pk)},
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Affiliate.objects.filter(organization=self.org_b).exists())


class ModuleBoundaryTests(TestCase):
    def test_partners_does_not_import_bots_or_academy(self):
        root = Path(__file__).resolve().parent
        offenders = []
        for path in root.rglob("*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                names = []
                if isinstance(node, ast.Import):
                    names = [alias.name for alias in node.names]
                elif isinstance(node, ast.ImportFrom) and node.module:
                    names = [node.module]
                for name in names:
                    if name.startswith(("apps.bots", "apps.academy")):
                        offenders.append(f"{path.name}: {name}")
        self.assertEqual(offenders, [])
