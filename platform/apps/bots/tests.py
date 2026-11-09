"""Tests du CRM bots : statuts, versions immuables, compte réel, déclarations, sécurité, isolation."""

import ast
import datetime as dt
from decimal import Decimal
from pathlib import Path

from django.apps import apps as django_apps
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import DatabaseError, IntegrityError, connection, transaction
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.core.models import AuditLog, OrganizationSettings, Role
from apps.core.testing import fake_request, login, make_org, make_user
from apps.partners import services as partner_services

from . import services
from .models import (
    PARAMETER_KEYS,
    ApplicationDeclaration,
    BotStatus,
    BotUser,
    ConfigurationVersion,
    Override,
    ParameterDefinition,
    ParameterValue,
    StatusEvent,
)

TODAY = timezone.localdate


class BotsTestCase(TestCase):
    def setUp(self):
        self.org = make_org()
        self.admin = make_user(self.org, Role.CRM_ADMIN)
        self.operator = make_user(self.org, Role.CRM_OPERATOR)
        self.viewer = make_user(self.org, Role.CRM_VIEWER)
        self.affiliate = partner_services.create_affiliate(
            organization=self.org, actor=self.admin, data={"display_name": "Affilié robot"}
        )
        self.bot = services.create_bot_user(
            organization=self.org, affiliate=self.affiliate, actor=self.operator,
            data={"wants_bot": True, "robot_type": "DIFFERS", "vps_label": "bot_user_1"},
        )

    def req(self, user):
        return fake_request(user, self.org)

    def draft(self, user=None, *, capital="100", params=None, account_type="demo", note=""):
        user = user or self.operator
        version = services.start_version(request=self.req(user), bot_user=self.bot)
        services.update_draft(
            request=self.req(user), version=version,
            data={"account_type": account_type, "reference_capital": Decimal(capital), "currency": "USD", "admin_note": note},
            parameters={k: Decimal(v) for k, v in (params or {"STAKE": "0.35"}).items()},
        )
        version.refresh_from_db()
        return version

    def validate(self, version, real=None):
        return services.validate_version(request=self.req(self.admin), version=version, real_declaration=real)

    def apply(self, version, user=None, on=None):
        return services.declare_applied(request=self.req(user or self.operator), version=version, applied_on=on or TODAY())

    def status(self):
        self.bot.refresh_from_db()
        return self.bot.status


class StatusTruthTableTests(BotsTestCase):
    def test_new_record_is_to_configure(self):
        self.assertEqual(self.status(), BotStatus.TO_CONFIGURE)

    def test_draft_never_changes_status(self):
        self.draft()
        self.assertEqual(self.status(), BotStatus.TO_CONFIGURE)

    def test_validated_but_never_applied_stays_to_configure(self):
        self.validate(self.draft())
        self.assertEqual(self.status(), BotStatus.TO_CONFIGURE)
        self.assertIsNotNone(self.bot.pending_since)

    def test_declared_applied(self):
        v1 = self.validate(self.draft())
        self.apply(v1, on=TODAY() - dt.timedelta(days=2))
        self.assertEqual(self.status(), BotStatus.APPLIED)
        self.assertEqual(self.bot.last_applied_on, TODAY() - dt.timedelta(days=2))
        self.assertIsNone(self.bot.pending_since)

    def test_new_validated_version_after_application_is_modification_requested(self):
        v1 = self.validate(self.draft())
        self.apply(v1)
        v2 = self.validate(self.draft(params={"STAKE": "0.50"}))
        self.assertEqual(self.status(), BotStatus.MODIFICATION_REQUESTED)
        self.apply(v2)
        self.assertEqual(self.status(), BotStatus.APPLIED)

    def test_correction_neutralises_a_declaration(self):
        v1 = self.validate(self.draft())
        declaration = self.apply(v1)
        services.correct_declaration(request=self.req(self.operator), declaration=declaration, reason="Saisie erronée")
        self.assertEqual(self.status(), BotStatus.TO_CONFIGURE)
        self.assertTrue(ApplicationDeclaration.objects.filter(pk=declaration.pk).exists())
        with self.assertRaises(ValidationError):
            services.correct_declaration(request=self.req(self.operator), declaration=declaration, reason="encore")

    def test_pause_disable_reactivate(self):
        v1 = self.validate(self.draft())
        self.apply(v1)
        services.set_override(request=self.req(self.operator), bot_user=self.bot, override=Override.PAUSED, reason="Congés")
        self.assertEqual(self.status(), BotStatus.PAUSED)
        with self.assertRaises(PermissionDenied):
            services.set_override(request=self.req(self.operator), bot_user=self.bot, override=Override.DISABLED, reason="x")
        services.set_override(request=self.req(self.admin), bot_user=self.bot, override=Override.DISABLED, reason="Fin")
        self.assertEqual(self.status(), BotStatus.DISABLED)
        with self.assertRaises(ValidationError):
            services.start_version(request=self.req(self.operator), bot_user=self.bot)
        services.set_override(request=self.req(self.admin), bot_user=self.bot, override=Override.NONE, reason="Reprise")
        self.assertEqual(self.status(), BotStatus.APPLIED)
        self.assertEqual(StatusEvent.objects.filter(bot_user=self.bot).count(), 3)

    def test_reason_required_for_status_change(self):
        with self.assertRaises(ValidationError):
            services.set_override(request=self.req(self.admin), bot_user=self.bot, override=Override.PAUSED, reason="  ")


class VersionTests(BotsTestCase):
    def test_numbering_copy_and_single_draft(self):
        v1 = self.validate(self.draft(params={"STAKE": "0.35", "MAX_TRADES": "10"}))
        v2 = services.start_version(request=self.req(self.operator), bot_user=self.bot)
        self.assertEqual(v2.number, v1.number + 1)
        self.assertEqual(
            {p.key: p.value for p in v2.parameters.all()}, {"STAKE": Decimal("0.35"), "MAX_TRADES": Decimal("10")}
        )
        self.assertEqual(v2.reference_capital, v1.reference_capital)
        again = services.start_version(request=self.req(self.operator), bot_user=self.bot)
        self.assertEqual(again.pk, v2.pk)
        with self.assertRaises(IntegrityError), transaction.atomic():
            ConfigurationVersion.objects.create(
                organization=self.org, bot_user=self.bot, number=99, robot_type="DIFFERS", created_by=self.admin
            )

    def test_validated_version_is_immutable_in_python_services(self):
        v1 = self.validate(self.draft())
        with self.assertRaises(ValidationError):
            services.update_draft(request=self.req(self.admin), version=v1, data={"admin_note": "x"}, parameters={})
        with self.assertRaises(ValidationError):
            services.delete_draft(request=self.req(self.admin), version=v1)
        with self.assertRaises(ValidationError):
            self.validate(v1)

    def test_validated_version_is_immutable_in_database(self):
        v1 = self.validate(self.draft())
        with self.assertRaises(DatabaseError), transaction.atomic():
            ConfigurationVersion.objects.filter(pk=v1.pk).update(reference_capital=Decimal("999"))
        with self.assertRaises(DatabaseError), transaction.atomic():
            ConfigurationVersion.objects.filter(pk=v1.pk).delete()
        with self.assertRaises(DatabaseError), transaction.atomic():
            ParameterValue.objects.filter(version=v1).update(value=Decimal("42"))
        with self.assertRaises(DatabaseError), transaction.atomic():
            ParameterValue.objects.create(version=v1, key="INTERVAL", value=Decimal("1"))
        with self.assertRaises(DatabaseError), transaction.atomic():
            ParameterValue.objects.filter(version=v1).delete()
        v1.refresh_from_db()
        self.assertEqual(v1.reference_capital, Decimal("100"))

    def test_capital_required_before_validation(self):
        version = services.start_version(request=self.req(self.operator), bot_user=self.bot)
        with self.assertRaises(ValidationError):
            self.validate(version)

    def test_operator_cannot_validate(self):
        version = self.draft()
        with self.assertRaises(PermissionDenied):
            services.validate_version(request=self.req(self.operator), version=version)

    def test_draft_can_be_deleted(self):
        version = self.draft()
        services.delete_draft(request=self.req(self.operator), version=version)
        self.assertFalse(ConfigurationVersion.objects.filter(pk=version.pk).exists())

    def test_robot_type_required(self):
        BotUser.objects.filter(pk=self.bot.pk).update(robot_type="")
        self.bot.refresh_from_db()
        with self.assertRaises(ValidationError):
            services.start_version(request=self.req(self.operator), bot_user=self.bot)


class WhitelistTests(BotsTestCase):
    def test_catalog_contains_exactly_the_twelve_keys_for_each_robot(self):
        for robot in ("DIFFERS", "OVER_UNDER"):
            keys = set(ParameterDefinition.objects.filter(organization=self.org, robot_type=robot).values_list("key", flat=True))
            self.assertEqual(keys, set(PARAMETER_KEYS))
        self.assertFalse(ParameterDefinition.objects.filter(organization=self.org, verified=True).exists())

    def test_unknown_key_rejected_by_service_and_database(self):
        version = services.start_version(request=self.req(self.operator), bot_user=self.bot)
        with self.assertRaises(ValidationError):
            services.update_draft(request=self.req(self.operator), version=version,
                                  data={"reference_capital": Decimal("1")}, parameters={"DERIV_TOKEN": Decimal("1")})
        with self.assertRaises(IntegrityError), transaction.atomic():
            ParameterValue.objects.create(version=version, key="API_TOKEN", value=Decimal("1"))

    def test_disabled_key_rejected(self):
        ParameterDefinition.objects.filter(organization=self.org, robot_type="DIFFERS", key="INTERVAL").update(enabled=False)
        version = services.start_version(request=self.req(self.operator), bot_user=self.bot)
        with self.assertRaises(ValidationError):
            services.update_draft(request=self.req(self.operator), version=version,
                                  data={"reference_capital": Decimal("1")}, parameters={"INTERVAL": Decimal("2")})

    def test_bounds_are_enforced(self):
        ParameterDefinition.objects.filter(organization=self.org, robot_type="DIFFERS", key="STAKE").update(
            min_value=Decimal("0.35"), max_value=Decimal("5")
        )
        version = services.start_version(request=self.req(self.operator), bot_user=self.bot)
        for value in ("0.10", "6"):
            with self.assertRaises(ValidationError):
                services.update_draft(request=self.req(self.operator), version=version,
                                      data={"reference_capital": Decimal("1")}, parameters={"STAKE": Decimal(value)})

    def test_parameter_values_are_numeric_only(self):
        field = ParameterValue._meta.get_field("value")
        self.assertEqual(field.get_internal_type(), "DecimalField")

    def test_no_secret_field_anywhere_in_business_models(self):
        forbidden = ("token", "password", "passwd", "secret", "api_key", "apikey", "credential", "private_key")
        offenders = []
        for model in django_apps.get_models():
            if model._meta.app_label not in ("core", "partners", "bots", "academy"):
                continue
            for field in model._meta.get_fields():
                name = field.name.lower()
                if model._meta.label == "core.User" and name == "password":
                    continue  # mot de passe de connexion, haché en Argon2
                if any(part in name for part in forbidden):
                    offenders.append(f"{model._meta.label}.{field.name}")
        self.assertEqual(offenders, [])

    def test_parameter_catalog_page_requires_crm_admin(self):
        login(self.client, self.operator, self.org)
        self.assertEqual(self.client.get(reverse("bots:parameters")).status_code, 403)
        login(self.client, self.admin, self.org)
        self.assertContains(self.client.get(reverse("bots:parameters")), "DAILY_MAX_LOSS_DEMO")

    def test_marking_verified_requires_a_reference(self):
        login(self.client, self.admin, self.org)
        definitions = list(ParameterDefinition.objects.filter(organization=self.org, robot_type="DIFFERS").order_by("key"))
        data = {"robot": "DIFFERS", "form-TOTAL_FORMS": str(len(definitions)), "form-INITIAL_FORMS": str(len(definitions))}
        for i, d in enumerate(definitions):
            data.update({f"form-{i}-id": str(d.pk), f"form-{i}-enabled": "on", f"form-{i}-unit": "", f"form-{i}-min_value": "0",
                         f"form-{i}-max_value": "", f"form-{i}-verification_reference": ""})
        data["form-0-verified"] = "on"
        response = self.client.post(reverse("bots:parameters"), data)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(ParameterDefinition.objects.filter(organization=self.org, verified=True).exists())
        data["form-0-verification_reference"] = "differs/main.py:42, 2026-11-09, admin"
        self.client.post(reverse("bots:parameters"), data)
        self.assertEqual(ParameterDefinition.objects.filter(organization=self.org, verified=True).count(), 1)
        self.assertTrue(AuditLog.objects.filter(action="parameter_catalog_changed").exists())


class RealAccountTests(BotsTestCase):
    REAL = {"confirmed": True, "declared_on": None, "note": "Compte réel confirmé par l'affilié"}

    def real(self):
        return dict(self.REAL, declared_on=TODAY())

    def test_operator_cannot_declare_real(self):
        version = services.start_version(request=self.req(self.operator), bot_user=self.bot)
        with self.assertRaises(PermissionDenied):
            services.update_draft(request=self.req(self.operator), version=version,
                                  data={"account_type": "real", "reference_capital": Decimal("50")}, parameters={})
        version.refresh_from_db()
        self.assertEqual(version.account_type, "demo")

    def test_operator_cannot_reach_real_choice_in_form(self):
        version = services.start_version(request=self.req(self.operator), bot_user=self.bot)
        login(self.client, self.operator, self.org)
        response = self.client.get(reverse("bots:version_edit", args=[version.pk]))
        self.assertEqual([c[0] for c in response.context["form"].fields["account_type"].choices], ["demo"])
        response = self.client.post(reverse("bots:version_edit", args=[version.pk]),
                                    {"account_type": "real", "reference_capital": "50", "currency": "USD"})
        version.refresh_from_db()
        self.assertEqual(version.account_type, "demo")

    def test_real_validation_requires_confirmation_date_and_note(self):
        version = self.draft(self.admin, account_type="real")
        with self.assertRaises(ValidationError):
            self.validate(version)
        with self.assertRaises(ValidationError):
            self.validate(version, dict(self.real(), confirmed=False))
        with self.assertRaises(ValidationError):
            self.validate(version, dict(self.real(), note=" "))
        with self.assertRaises(ValidationError):
            self.validate(version, dict(self.real(), declared_on=TODAY() + dt.timedelta(days=1)))
        version.refresh_from_db()
        self.assertEqual(version.state, "draft")

    def test_real_declaration_by_crm_admin_is_recorded_and_audited(self):
        version = self.validate(self.draft(self.admin, account_type="real"), self.real())
        self.assertEqual(version.real_confirmed_by, self.admin)
        self.assertIn("REAL", version.real_confirmation_wording.upper().replace("RÉEL", "REAL"))
        self.assertTrue(AuditLog.objects.filter(action="real_account_declared", target_id=str(version.pk)).exists())
        self.bot.refresh_from_db()
        self.assertEqual(self.bot.current_account_type, "real")

    def test_database_refuses_real_validation_without_declaration(self):
        version = self.draft(self.admin, account_type="real")
        with self.assertRaises(IntegrityError), transaction.atomic():
            ConfigurationVersion.objects.filter(pk=version.pk).update(state="validated", validated_at=timezone.now())

    def test_real_configuration_actions_reserved_to_crm_admin(self):
        v1 = self.validate(self.draft(self.admin, account_type="real"), self.real())
        with self.assertRaises(PermissionDenied):
            self.apply(v1, user=self.operator)
        declaration = self.apply(v1, user=self.admin)
        with self.assertRaises(PermissionDenied):
            services.correct_declaration(request=self.req(self.operator), declaration=declaration, reason="x")
        with self.assertRaises(PermissionDenied):
            services.start_version(request=self.req(self.operator), bot_user=self.bot)

    def test_real_validation_page_forbidden_for_operator(self):
        version = self.draft(self.admin, account_type="real")
        login(self.client, self.operator, self.org)
        self.assertEqual(self.client.get(reverse("bots:version_validate", args=[version.pk])).status_code, 403)
        self.assertEqual(self.client.post(reverse("bots:version_edit", args=[version.pk]), {}).status_code, 403)

    def test_real_validation_through_the_view(self):
        version = self.draft(self.admin, account_type="real")
        login(self.client, self.admin, self.org)
        page = self.client.get(reverse("bots:version_validate", args=[version.pk]))
        self.assertContains(page, "RÉEL")
        self.client.post(reverse("bots:version_validate", args=[version.pk]), {"declared_on": TODAY().isoformat(), "note": "ok"})
        version.refresh_from_db()
        self.assertEqual(version.state, "draft")  # case de confirmation absente
        self.client.post(reverse("bots:version_validate", args=[version.pk]),
                         {"confirmed": "on", "declared_on": TODAY().isoformat(), "note": "Confirmé"})
        version.refresh_from_db()
        self.assertEqual(version.state, "validated")

    def test_declaring_real_never_calls_the_network(self):
        import socket

        original = socket.socket.connect

        def forbidden(*args, **kwargs):
            raise AssertionError("Connexion réseau interdite")

        socket.socket.connect = forbidden
        try:
            version = self.validate(self.draft(self.admin, account_type="real"), self.real())
            self.apply(version, user=self.admin)
        finally:
            socket.socket.connect = original


class DeclarationTests(BotsTestCase):
    def test_only_latest_validated_version_can_be_declared(self):
        v1 = self.validate(self.draft())
        self.validate(self.draft(params={"STAKE": "1"}))
        with self.assertRaises(ValidationError):
            self.apply(v1)

    def test_draft_cannot_be_declared_even_in_database(self):
        version = self.draft()
        with self.assertRaises(ValidationError):
            self.apply(version)
        with self.assertRaises(DatabaseError), transaction.atomic():
            ApplicationDeclaration.objects.create(organization=self.org, version=version, kind="applied",
                                                  applied_on=TODAY(), recorded_by=self.admin)

    def test_future_date_and_double_declaration_rejected(self):
        v1 = self.validate(self.draft())
        with self.assertRaises(ValidationError):
            self.apply(v1, on=TODAY() + dt.timedelta(days=1))
        self.apply(v1, on=TODAY() - dt.timedelta(days=400))  # reprise d'un historique ancien : autorisé
        with self.assertRaises(ValidationError):
            self.apply(v1)

    def test_declarations_are_append_only(self):
        declaration = self.apply(self.validate(self.draft()))
        with self.assertRaises(DatabaseError), transaction.atomic():
            ApplicationDeclaration.objects.filter(pk=declaration.pk).update(applied_on=TODAY() - dt.timedelta(days=9))
        with self.assertRaises(DatabaseError), transaction.atomic():
            with connection.cursor() as cursor:
                cursor.execute("DELETE FROM bots_applicationdeclaration WHERE id = %s", [declaration.pk])

    def test_viewer_cannot_declare_or_pause(self):
        v1 = self.validate(self.draft())
        with self.assertRaises(PermissionDenied):
            self.apply(v1, user=self.viewer)
        login(self.client, self.viewer, self.org)
        response = self.client.post(reverse("bots:botuser_override", args=[self.bot.pk, "pause"]), {"reason": "x"})
        self.assertEqual(response.status_code, 403)
        self.assertEqual(self.status(), BotStatus.TO_CONFIGURE)


class FullFlowViewTests(BotsTestCase):
    def test_complete_flow_through_the_interface(self):
        affiliate = partner_services.create_affiliate(organization=self.org, actor=self.admin, data={"display_name": "Parcours UI"})
        login(self.client, self.operator, self.org)
        response = self.client.post(reverse("bots:botuser_create"),
                                    {"affiliate": str(affiliate.pk), "wants_bot": "on", "robot_type": "OVER_UNDER", "vps_label": "ui_user"})
        bot = BotUser.objects.get(affiliate=affiliate)
        self.assertRedirects(response, reverse("bots:botuser_detail", args=[bot.pk]), fetch_redirect_response=False)
        self.client.post(reverse("bots:version_start", args=[bot.pk]))
        version = ConfigurationVersion.objects.get(bot_user=bot)
        self.client.post(reverse("bots:version_edit", args=[version.pk]),
                         {"account_type": "demo", "reference_capital": "250", "currency": "usd", "param_STAKE": "0.5", "param_DURATION": "5"})
        version.refresh_from_db()
        self.assertEqual(version.currency, "USD")
        self.assertEqual(version.parameters.count(), 2)
        login(self.client, self.admin, self.org)
        self.client.post(reverse("bots:version_validate", args=[version.pk]))
        login(self.client, self.operator, self.org)
        self.client.post(reverse("bots:version_declare_applied", args=[version.pk]), {"applied_on": TODAY().isoformat(), "note": ""})
        bot.refresh_from_db()
        self.assertEqual(bot.status, BotStatus.APPLIED)
        detail = self.client.get(reverse("bots:botuser_detail", args=[bot.pk]))
        self.assertContains(detail, "OVER/UNDER")
        self.assertContains(detail, "0,5")  # séparateur décimal français
        self.assertContains(self.client.get(reverse("partners:affiliate_detail", args=[affiliate.pk])), "Ouvrir la fiche robot")

    def test_one_robot_record_per_affiliate(self):
        with self.assertRaises(ValidationError):
            services.create_bot_user(organization=self.org, affiliate=self.affiliate, actor=self.admin, data={})

    def test_invalid_vps_label_rejected(self):
        affiliate = partner_services.create_affiliate(organization=self.org, actor=self.admin, data={"display_name": "Label"})
        with self.assertRaises(ValidationError):
            services.create_bot_user(organization=self.org, affiliate=affiliate, actor=self.admin,
                                     data={"robot_type": "DIFFERS", "vps_label": "user:password@host"})

    def test_dashboard_counts_come_from_records(self):
        affiliate = partner_services.create_affiliate(organization=self.org, actor=self.admin, data={"display_name": "Second"})
        services.create_bot_user(organization=self.org, affiliate=affiliate, actor=self.admin, data={"robot_type": "DIFFERS"})
        v1 = self.validate(self.draft())
        self.apply(v1)
        self.validate(self.draft(params={"STAKE": "2"}))
        login(self.client, self.admin, self.org)
        response = self.client.get(reverse("core:dashboard"))
        section = next(s for s in response.context["sections"] if s["template"] == "bots/dashboard_section.html")
        self.assertEqual(section["context"]["total"], 2)
        self.assertEqual(section["context"]["to_apply"], 1)
        self.assertEqual(section["context"]["modification_requested"], 1)

    def test_alerts_follow_thresholds(self):
        v1 = self.validate(self.draft())
        self.apply(v1, on=TODAY() - dt.timedelta(days=45))
        settings_obj = OrganizationSettings.for_organization(self.org)
        queryset = BotUser.objects.filter(organization=self.org)
        self.assertEqual(list(services.configuration_review_due(queryset, settings_obj)), [self.bot])
        self.validate(self.draft(params={"STAKE": "3"}))
        BotUser.objects.filter(pk=self.bot.pk).update(pending_since=timezone.now() - dt.timedelta(days=10))
        self.assertEqual(list(services.modification_pending(queryset, settings_obj)), [self.bot])
        settings_obj.modification_pending_days = 20
        self.assertEqual(list(services.modification_pending(queryset, settings_obj)), [])

    def test_english_interface(self):
        login(self.client, self.admin, self.org)
        self.client.post(reverse("core:switch_language"), {"language": "en"})
        response = self.client.get(reverse("bots:botuser_detail", args=[self.bot.pk]))
        self.assertContains(response, "Declared by an administrator, not checked on the VPS")
        self.assertContains(response, 'lang="en"')


class IsolationTests(BotsTestCase):
    def setUp(self):
        super().setUp()
        self.v1 = self.validate(self.draft())
        self.declaration = self.apply(self.v1)
        self.other_org = make_org()
        self.intruder = make_user(self.other_org, Role.CRM_ADMIN)
        login(self.client, self.intruder, self.other_org)

    def test_foreign_records_return_404(self):
        urls = [
            ("get", reverse("bots:botuser_detail", args=[self.bot.pk])),
            ("get", reverse("bots:botuser_update", args=[self.bot.pk])),
            ("post", reverse("bots:version_start", args=[self.bot.pk])),
            ("post", reverse("bots:botuser_override", args=[self.bot.pk, "pause"])),
            ("get", reverse("bots:version_detail", args=[self.v1.pk])),
            ("get", reverse("bots:version_validate", args=[self.v1.pk])),
            ("post", reverse("bots:version_declare_applied", args=[self.v1.pk])),
            ("post", reverse("bots:declaration_correct", args=[self.declaration.pk])),
        ]
        for method, url in urls:
            self.assertEqual(getattr(self.client, method)(url, {"reason": "x"}).status_code, 404, url)
        self.assertNotContains(self.client.get(reverse("bots:botuser_list")), "Affilié robot")

    def test_cannot_create_robot_record_for_foreign_affiliate(self):
        other_affiliate = partner_services.create_affiliate(
            organization=self.org, actor=self.admin, data={"display_name": "Étranger"}
        )
        response = self.client.post(reverse("bots:botuser_create"), {"affiliate": str(other_affiliate.pk), "robot_type": "DIFFERS"})
        self.assertEqual(response.status_code, 200)
        self.assertFalse(BotUser.objects.filter(affiliate=other_affiliate).exists())
        with self.assertRaises(PermissionDenied):
            services.create_bot_user(organization=self.other_org, affiliate=other_affiliate, actor=self.intruder, data={})

    def test_database_refuses_cross_organization_records(self):
        other_affiliate = partner_services.create_affiliate(organization=self.org, actor=self.admin, data={"display_name": "Croisé"})
        with self.assertRaises(DatabaseError), transaction.atomic():
            BotUser.objects.create(organization=self.other_org, affiliate=other_affiliate, created_by=self.intruder)
        with self.assertRaises(DatabaseError), transaction.atomic():
            ConfigurationVersion.objects.create(organization=self.other_org, bot_user=self.bot, number=50,
                                                robot_type="DIFFERS", created_by=self.intruder)


class SafetyBoundaryTests(TestCase):
    """Le module ne contient aucun code de communication avec le VPS ou Deriv."""

    FORBIDDEN_IMPORTS = ("requests", "urllib", "http.client", "httpx", "socket", "paramiko", "subprocess",
                         "websocket", "websockets", "asyncssh", "fabric", "ftplib", "smtplib", "telnetlib")

    def test_bots_module_has_no_network_or_shell_code(self):
        root = Path(__file__).resolve().parent
        offenders = []
        for path in root.rglob("*.py"):
            if path.name == "tests.py":
                continue
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                names = [a.name for a in node.names] if isinstance(node, ast.Import) else (
                    [node.module] if isinstance(node, ast.ImportFrom) and node.module else []
                )
                for name in names:
                    if name.split(".")[0] in self.FORBIDDEN_IMPORTS or name in self.FORBIDDEN_IMPORTS:
                        offenders.append(f"{path.name}: {name}")
        self.assertEqual(offenders, [])

    def test_no_route_controls_a_robot(self):
        from apps.bots.urls import urlpatterns

        names = " ".join(p.name for p in urlpatterns)
        for word in ("start_bot", "stop_bot", "restart", "deploy", "ssh", "command", "trade", "sync"):
            self.assertNotIn(word, names)

    def test_bots_does_not_import_academy(self):
        root = Path(__file__).resolve().parent
        for path in root.rglob("*.py"):
            if path.name != "tests.py":
                self.assertNotIn("apps.academy", path.read_text(encoding="utf-8"), path.name)
