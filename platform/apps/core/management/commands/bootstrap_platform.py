"""Crée l'organisation initiale et son administrateur (idempotent).

Le mot de passe est lu dans la variable SYSTEMC_ADMIN_PASSWORD ou demandé de
façon interactive. Il n'est jamais passé en argument de ligne de commande (il
apparaîtrait dans l'historique du shell et la liste des processus).
"""

import getpass
import os

from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils.text import slugify

from apps.core import audit
from apps.core.models import Membership, Organization, OrganizationSettings, Role, User, UserManager
from apps.core.services import run_organization_setup


class Command(BaseCommand):
    help = "Crée l'organisation initiale et un compte administrateur (org_admin + crm_admin)."

    def add_arguments(self, parser):
        parser.add_argument("--organization", required=True, help="Nom de l'organisation, ex. « SYSTEM-C ».")
        parser.add_argument("--email", required=True, help="Adresse de connexion de l'administrateur.")
        parser.add_argument("--full-name", required=True, help="Nom affiché de l'administrateur.")
        parser.add_argument("--language", choices=["fr", "en"], default="fr")
        parser.add_argument("--no-input", action="store_true", help="Exige SYSTEMC_ADMIN_PASSWORD.")

    def _password(self, options, candidate) -> str:
        password = os.environ.get("SYSTEMC_ADMIN_PASSWORD", "")
        if not password:
            if options["no_input"]:
                raise CommandError("SYSTEMC_ADMIN_PASSWORD est vide alors que --no-input est demandé.")
            password = getpass.getpass("Mot de passe : ")
            if password != getpass.getpass("Confirmation : "):
                raise CommandError("Les deux mots de passe diffèrent.")
        try:
            validate_password(password, candidate)
        except ValidationError as exc:
            raise CommandError(" ".join(exc.messages)) from exc
        return password

    def handle(self, *args, **options):
        email = UserManager.normalize_login(options["email"])
        name = options["organization"].strip()
        slug = slugify(name)[:60] or "organisation"
        with transaction.atomic():
            organization, org_created = Organization.objects.get_or_create(slug=slug, defaults={"name": name})
            OrganizationSettings.for_organization(organization)
            run_organization_setup(organization)
            user = User.objects.filter(email__iexact=email).first()
            user_created = False
            if user is None:
                candidate = User(email=email, full_name=options["full_name"])
                password = self._password(options, candidate)
                user = User.objects.create_user(
                    email=email,
                    password=password,
                    full_name=options["full_name"],
                    preferred_language=options["language"],
                )
                user_created = True
            for role in (Role.ORG_ADMIN, Role.CRM_ADMIN):
                Membership.objects.get_or_create(user=user, organization=organization, role=role)
            audit.record(
                "platform_bootstrapped",
                organization=organization,
                target=organization,
                organization_created=org_created,
                user_created=user_created,
            )
        self.stdout.write(self.style.SUCCESS(
            f"Organisation « {organization.name} » {'créée' if org_created else 'existante'} ; "
            f"administrateur {email} {'créé' if user_created else 'existant'} (rôles org_admin et crm_admin)."
        ))
