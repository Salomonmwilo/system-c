"""Crée des fiches fictives, marquées « [Démo] », pour explorer l'interface en local.

Ces données ne sont jamais créées automatiquement. La commande refuse de
s'exécuter sans --yes et quand DEBUG est désactivé (sauf --allow-production).
Toutes les écritures passent par les services : audit et règles métier compris.
"""

import datetime as dt
from decimal import Decimal

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from apps.bots import services as bot_services
from apps.core.models import Membership, Organization, Role
from apps.core.testing import fake_request
from apps.partners import services as partner_services
from apps.partners.models import Affiliate

PEOPLE = [
    ("[Démo] Amani K.", "CD", "active", ("account_created", 40), ("validated", 30), True, "DIFFERS", "applied"),
    ("[Démo] Béatrice M.", "CD", "active", ("account_created", 20), ("in_progress", 18), True, "OVER_UNDER", "modification"),
    ("[Démo] Christian L.", "FR", "active", ("declared_by_affiliate", 12), None, True, "DIFFERS", "validated"),
    ("[Démo] Divine N.", "BE", "prospect", None, None, False, None, None),
    ("[Démo] Emmanuel T.", "CD", "active", ("account_created", 60), ("validated", 55), True, "OVER_UNDER", "paused"),
    ("[Démo] Fatou S.", "SN", "inactive", ("account_created", 90), ("rejected", 80), False, None, None),
]


class Command(BaseCommand):
    help = "Ajoute des données fictives « [Démo] » dans une organisation (exploration locale uniquement)."

    def add_arguments(self, parser):
        parser.add_argument("--organization", required=True, help="Identifiant (slug) de l'organisation.")
        parser.add_argument("--admin-email", required=True, help="Compte crm_admin auteur des fiches.")
        parser.add_argument("--yes", action="store_true", help="Confirme la création de données fictives.")
        parser.add_argument("--allow-production", action="store_true")

    def handle(self, *args, **options):
        if not options["yes"]:
            raise CommandError("Ajoutez --yes pour confirmer la création de données fictives.")
        if not settings.DEBUG and not options["allow_production"]:
            raise CommandError("Refusé hors mode DEBUG.")
        org = Organization.objects.filter(slug=options["organization"]).first()
        if org is None:
            raise CommandError("Organisation inconnue.")
        membership = Membership.objects.filter(
            organization=org, user__email__iexact=options["admin_email"], role=Role.CRM_ADMIN
        ).select_related("user").first()
        if membership is None:
            raise CommandError("Ce compte n'est pas crm_admin de cette organisation.")
        admin = membership.user
        request = fake_request(admin, org)
        today = timezone.localdate()
        created = 0
        with transaction.atomic():
            for name, country, status, registration, verification, wants, robot, scenario in PEOPLE:
                if Affiliate.objects.filter(organization=org, display_name=name).exists():
                    continue
                affiliate = partner_services.create_affiliate(
                    organization=org, actor=admin,
                    data={"display_name": name, "country": country, "status": status, "assigned_to": admin},
                )
                created += 1
                if registration:
                    partner_services.record_track(affiliate=affiliate, actor=admin, track="registration", value=registration[0],
                                                  declared_on=today - dt.timedelta(days=registration[1]), source="affiliate")
                if verification:
                    partner_services.record_track(affiliate=affiliate, actor=admin, track="verification", value=verification[0],
                                                  declared_on=today - dt.timedelta(days=verification[1]), source="deriv_support")
                partner_services.add_interaction(affiliate=affiliate, actor=admin, kind="call",
                                                 occurred_at=timezone.now() - dt.timedelta(days=len(name) % 45),
                                                 summary="Échange de suivi (donnée de démonstration).")
                partner_services.create_followup(affiliate=affiliate, actor=admin, title="Relance de démonstration",
                                                 due_on=today + dt.timedelta(days=(len(name) % 5) - 2), assigned_to=admin)
                if not robot:
                    continue
                bot = bot_services.create_bot_user(organization=org, affiliate=affiliate, actor=admin,
                                                   data={"wants_bot": wants, "robot_type": robot})
                version = bot_services.start_version(request=request, bot_user=bot)
                bot_services.update_draft(request=request, version=version,
                                          data={"account_type": "demo", "reference_capital": Decimal("100"), "currency": "USD",
                                                "admin_note": "Configuration de démonstration."},
                                          parameters={"STAKE": Decimal("0.35"), "MAX_TRADES": Decimal("10")})
                bot_services.validate_version(request=request, version=version)
                if scenario in ("applied", "modification", "paused"):
                    bot_services.declare_applied(request=request, version=version, applied_on=today - dt.timedelta(days=12))
                if scenario == "modification":
                    second = bot_services.start_version(request=request, bot_user=bot)
                    bot_services.update_draft(request=request, version=second,
                                              data={"account_type": "demo", "reference_capital": Decimal("150"), "currency": "USD"},
                                              parameters={"STAKE": Decimal("0.5"), "MAX_TRADES": Decimal("8")})
                    bot_services.validate_version(request=request, version=second)
                if scenario == "paused":
                    bot_services.set_override(request=request, bot_user=bot, override="paused", reason="Pause demandée (démo).")
        self.stdout.write(self.style.SUCCESS(f"{created} fiche(s) de démonstration créée(s) dans « {org.name} »."))
