"""Crée un programme et une offre d'essai « [Démo] » pour tester le parcours de commande en local.

    python manage.py seed_academy_demo --organization system-c --yes

Refusé quand DEBUG est désactivé. Ne touche pas à SYSTEM-C Method. Aucune
commande n'est créée et aucun paiement n'est simulé : pour essayer, commandez
l'offre d'essai depuis l'interface, puis confirmez-la depuis « Commandes ».
Les ressources d'essai pointent vers example.org, un domaine réservé aux exemples.
"""

from decimal import Decimal

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.academy.models import Program, ProgramOffer, Resource
from apps.core.models import Organization

TITLE = "[Démo] Programme d'essai"


class Command(BaseCommand):
    help = "Ajoute un programme et une offre d'essai « [Démo] » (exploration locale uniquement)."

    def add_arguments(self, parser):
        parser.add_argument("--organization", required=True, help="Identifiant (slug) de l'organisation.")
        parser.add_argument("--yes", action="store_true", help="Confirme la création de données fictives.")

    def handle(self, *args, **options):
        if not settings.DEBUG:
            raise CommandError("Refusé hors mode DEBUG.")
        if not options["yes"]:
            raise CommandError("Ajoutez --yes pour confirmer la création de données fictives.")
        try:
            org = Organization.objects.get(slug=options["organization"])
        except Organization.DoesNotExist as exc:
            raise CommandError(f"Organisation « {options['organization']} » introuvable.") from exc

        with transaction.atomic():
            program, created = Program.objects.get_or_create(
                organization=org,
                title_fr=TITLE,
                defaults={
                    "title_en": "[Demo] Trial programme",
                    "description_fr": "Données fictives pour essayer le parcours de commande en local.",
                    "description_en": "Fictitious data to try the ordering flow locally.",
                    "is_published": True,
                },
            )
            if not created:
                self.stdout.write("Le programme d'essai existe déjà : rien n'est ajouté.")
                return
            offer = ProgramOffer.objects.create(
                program=program,
                slug="demo",
                name_fr="[Démo] Offre d'essai",
                name_en="[Demo] Trial offer",
                description_fr="Offre fictive. Aucun paiement réel ne doit être effectué.",
                description_en="Fictitious offer. No real payment must be made.",
                price=Decimal("5.00"),
                currency="USD",
                status=ProgramOffer.Status.PUBLISHED,
            )
            paid = Resource.objects.create(
                program=program,
                title_fr="[Démo] Fiche d'essai",
                title_en="[Demo] Trial sheet",
                category=Resource.Category.CHECKLIST,
                visibility=Resource.Visibility.OFFERS,
                external_url="https://example.org/systemc-demo",
                status=Resource.Status.PUBLISHED,
                position=1,
            )
            paid.offers.set([offer])
            Resource.objects.create(
                program=program,
                title_fr="[Démo] Ressource gratuite d'essai",
                title_en="[Demo] Free trial resource",
                category=Resource.Category.DISCOVERY,
                visibility=Resource.Visibility.PUBLIC,
                external_url="https://example.org/systemc-demo-free",
                status=Resource.Status.PUBLISHED,
                position=2,
            )
        self.stdout.write(self.style.SUCCESS(
            f"Programme et offre d'essai « [Démo] » créés pour « {org.name} » (5,00 USD, fictif)."
        ))
