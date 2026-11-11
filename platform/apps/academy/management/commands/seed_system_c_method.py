"""Initialize SYSTEM-C Method program with 5 steps, lessons, resources and offers.

Usage:
    python manage.py seed_system_c_method --organization system-c --yes
"""

from decimal import Decimal

from django.core.management.base import BaseCommand, CommandError

from apps.academy.models import Course, Enrollment, Lesson, Program, ProgramOffer, Resource
from apps.core.models import Organization


class Command(BaseCommand):
    help = "Initialize SYSTEM-C Method program with full curriculum and offers"

    def add_arguments(self, parser):
        parser.add_argument("--organization", type=str, required=True, help="Organization slug")
        parser.add_argument("--yes", action="store_true", help="Skip confirmation")

    def handle(self, *args, **options):
        org_slug = options["organization"]
        confirmed = options.get("yes", False)

        try:
            org = Organization.objects.get(slug=org_slug)
        except Organization.DoesNotExist:
            raise CommandError(f"Organization '{org_slug}' not found")

        self.stdout.write(f"Initializing SYSTEM-C Method for {org.name}...")

        if not confirmed:
            self.stdout.write(
                "This will create:\n"
                "  - 1 Program: SYSTEM-C Method\n"
                "  - 5 Courses (steps)\n"
                "  - 15 Lessons\n"
                "  - 7 Resources (draft)\n"
                "  - 3 Offers (Starter, Complete, Guided)\n"
            )
            response = input("Continue? (y/n): ")
            if response.lower() != "y":
                self.stdout.write("Cancelled.")
                return

        # Create program
        program, created = Program.objects.get_or_create(
            organization=org,
            title_fr="SYSTEM-C Method",
            defaults={
                "title_en": "SYSTEM-C Method",
                "description_fr": "Un programme éducatif pour structurer son apprentissage du trading, organiser ses décisions et développer une approche consciente des risques.",
                "description_en": "An educational program to structure your trading education, organize your decisions, and develop a conscious approach to risk.",
                "is_published": False,
            },
        )

        if not created:
            self.stdout.write(self.style.WARNING(f"Program '{program.title}' already exists"))
            return

        self.stdout.write(self.style.SUCCESS(f"✓ Created program: {program.title}"))

        # Create 5 steps (courses)
        steps_data = [
            {
                "slug": "comprendre",
                "title_fr": "Étape 1 — COMPRENDRE",
                "title_en": "Step 1 — UNDERSTAND",
                "lessons": [
                    {
                        "title_fr": "Les bases de l'apprentissage du trading",
                        "title_en": "The Basics of Trading Education",
                        "body_fr": "Comprendre comment on apprend et pourquoi aucune méthode ne garantit un résultat.",
                        "body_en": "Understand how we learn and why no method guarantees a result.",
                    },
                    {
                        "title_fr": "La notion de risque",
                        "title_en": "The Notion of Risk",
                        "body_fr": "Risque financier, psychologique et méthodologique.",
                        "body_en": "Financial, psychological and methodological risk.",
                    },
                    {
                        "title_fr": "Information, hypothèse et décision",
                        "title_en": "Information, Hypothesis and Decision",
                        "body_fr": "Distinguer ce que vous savez, ce que vous pensez, et ce que vous décidez.",
                        "body_en": "Distinguish what you know, what you think, and what you decide.",
                    },
                ]
            },
            {
                "slug": "preparer",
                "title_fr": "Étape 2 — PRÉPARER",
                "title_en": "Step 2 — PREPARE",
                "lessons": [
                    {
                        "title_fr": "Définir ses objectifs d'apprentissage",
                        "title_en": "Define Your Learning Goals",
                        "body_fr": "Savoir ce qu'on veut apprendre et pourquoi.",
                        "body_en": "Know what you want to learn and why.",
                    },
                    {
                        "title_fr": "Établir un cadre personnel de travail",
                        "title_en": "Establish Your Personal Work Framework",
                        "body_fr": "Règles, horaires, discipline.",
                        "body_en": "Rules, schedules, discipline.",
                    },
                    {
                        "title_fr": "Comprendre les limites du capital exposé",
                        "title_en": "Understand Capital Limits",
                        "body_fr": "Ne jamais risquer plus que ce qu'on peut se permettre de perdre.",
                        "body_en": "Never risk more than you can afford to lose.",
                    },
                ]
            },
            {
                "slug": "decider",
                "title_fr": "Étape 3 — DÉCIDER",
                "title_en": "Step 3 — DECIDE",
                "lessons": [
                    {
                        "title_fr": "Utiliser une checklist avant une décision",
                        "title_en": "Use a Checklist Before a Decision",
                        "body_fr": "Vérifier systématiquement tous les critères.",
                        "body_en": "Systematically verify all criteria.",
                    },
                    {
                        "title_fr": "Identifier les informations disponibles",
                        "title_en": "Identify Available Information",
                        "body_fr": "Différencier les données, les analyses et les opinions.",
                        "body_en": "Differentiate data, analyses and opinions.",
                    },
                    {
                        "title_fr": "Identifier les décisions impulsives",
                        "title_en": "Identify Impulse Decisions",
                        "body_fr": "Reconnaître la peur, la cupidité et les biais.",
                        "body_en": "Recognize fear, greed and biases.",
                    },
                ]
            },
            {
                "slug": "documenter",
                "title_fr": "Étape 4 — DOCUMENTER",
                "title_en": "Step 4 — DOCUMENT",
                "lessons": [
                    {
                        "title_fr": "Tenir un journal de décisions",
                        "title_en": "Keep a Decision Journal",
                        "body_fr": "Noter chaque décision et ses raisons.",
                        "body_en": "Record each decision and its reasons.",
                    },
                    {
                        "title_fr": "Consigner ses émotions",
                        "title_en": "Record Your Emotions",
                        "body_fr": "Comprendre le rôle des émotions dans vos décisions.",
                        "body_en": "Understand the role of emotions in your decisions.",
                    },
                    {
                        "title_fr": "Documenter ses erreurs",
                        "title_en": "Document Your Mistakes",
                        "body_fr": "Apprendre de ses erreurs sans les répéter.",
                        "body_en": "Learn from your mistakes without repeating them.",
                    },
                ]
            },
            {
                "slug": "evaluer",
                "title_fr": "Étape 5 — ÉVALUER",
                "title_en": "Step 5 — EVALUATE",
                "lessons": [
                    {
                        "title_fr": "Faire un bilan hebdomadaire",
                        "title_en": "Make a Weekly Review",
                        "body_fr": "Analyser ce qui a fonctionné et ce qui ne fonctionne pas.",
                        "body_en": "Analyze what worked and what did not.",
                    },
                    {
                        "title_fr": "Identifier les habitudes à corriger",
                        "title_en": "Identify Habits to Correct",
                        "body_fr": "Reconnaître les schémas répétitifs.",
                        "body_en": "Recognize repetitive patterns.",
                    },
                    {
                        "title_fr": "Définir les prochains objectifs",
                        "title_en": "Define Next Goals",
                        "body_fr": "Construire un plan d'amélioration.",
                        "body_en": "Build an improvement plan.",
                    },
                ]
            },
        ]

        courses = {}
        for position, step in enumerate(steps_data, 1):
            course, _ = Course.objects.get_or_create(
                program=program,
                position=position,
                defaults={
                    "title_fr": step["title_fr"],
                    "title_en": step["title_en"],
                },
            )
            courses[step["slug"]] = course
            self.stdout.write(f"✓ Created course: {course.title_fr}")

            for lesson_pos, lesson_data in enumerate(step["lessons"], 1):
                Lesson.objects.get_or_create(
                    course=course,
                    position=lesson_pos,
                    defaults={
                        "title_fr": lesson_data["title_fr"],
                        "title_en": lesson_data["title_en"],
                        "body_fr": lesson_data["body_fr"],
                        "body_en": lesson_data["body_en"],
                    },
                )

        self.stdout.write(self.style.SUCCESS("✓ Created 15 lessons"))

        # Create resources (draft, no files)
        resources_data = [
            {
                "title_fr": "Guide SYSTEM-C Method",
                "title_en": "SYSTEM-C Method Guide",
                "resource_type": "guide",
                "description_fr": "Guide complet du programme (35-50 pages)",
                "description_en": "Complete program guide (35-50 pages)",
            },
            {
                "title_fr": "Journal de suivi 30 jours",
                "title_en": "30-Day Tracking Journal",
                "resource_type": "worksheet",
                "description_fr": "Journal personnel pour documenter vos décisions",
                "description_en": "Personal journal to document your decisions",
            },
            {
                "title_fr": "Feuille de gestion du risque",
                "title_en": "Risk Management Sheet",
                "resource_type": "worksheet",
                "description_fr": "Suivi du capital et des limites",
                "description_en": "Track capital and limits",
            },
            {
                "title_fr": "Checklist avant une décision",
                "title_en": "Decision Checklist",
                "resource_type": "checklist",
                "description_fr": "7 points à vérifier avant chaque décision",
                "description_en": "7 points to check before each decision",
            },
            {
                "title_fr": "Plan d'apprentissage 4 semaines",
                "title_en": "4-Week Learning Plan",
                "resource_type": "guide",
                "description_fr": "Progression structurée sur 4 semaines",
                "description_en": "Structured progression over 4 weeks",
            },
            {
                "title_fr": "Introduction vidéo",
                "title_en": "Introduction Video",
                "resource_type": "video",
                "description_fr": "Présentation du programme (à créer)",
                "description_en": "Program overview (to create)",
            },
            {
                "title_fr": "7 questions avant une décision (gratuit)",
                "title_en": "7 Questions Before a Decision (free)",
                "resource_type": "guide",
                "description_fr": "Ressource gratuite de découverte",
                "description_en": "Free discovery resource",
            },
        ]

        for position, resource_data in enumerate(resources_data, 1):
            Resource.objects.get_or_create(
                program=program,
                title_fr=resource_data["title_fr"],
                defaults={
                    "title_en": resource_data["title_en"],
                    "resource_type": resource_data["resource_type"],
                    "description_fr": resource_data["description_fr"],
                    "description_en": resource_data["description_en"],
                    "status": Resource.Status.DRAFT,
                    "position": position,
                },
            )

        self.stdout.write(self.style.SUCCESS("✓ Created 7 resources (draft)"))

        # Create offers
        offers_data = [
            {
                "slug": "starter",
                "name_fr": "Starter Kit",
                "name_en": "Starter Kit",
                "description_fr": "Introduction au programme avec ressources essentielles",
                "description_en": "Introduction to the program with essential resources",
                "price_usd": Decimal("9.00"),
                "position": 1,
            },
            {
                "slug": "complete",
                "name_fr": "Complete",
                "name_en": "Complete",
                "description_fr": "Offre principale : guide complet, journal, checklist, plan d'apprentissage et vidéos",
                "description_en": "Main offer: complete guide, journal, checklist, learning plan and videos",
                "price_usd": Decimal("29.00"),
                "position": 2,
            },
            {
                "slug": "guided",
                "name_fr": "Guided",
                "name_en": "Guided",
                "description_fr": "Accompagnement : tout le contenu Complete + ateliers et groupe privé (en préparation)",
                "description_en": "Guided: all Complete content + workshops and private group (in preparation)",
                "price_usd": Decimal("79.00"),
                "position": 3,
            },
        ]

        for offer_data in offers_data:
            ProgramOffer.objects.get_or_create(
                program=program,
                slug=offer_data["slug"],
                defaults={
                    "name_fr": offer_data["name_fr"],
                    "name_en": offer_data["name_en"],
                    "description_fr": offer_data["description_fr"],
                    "description_en": offer_data["description_en"],
                    "price_usd": offer_data["price_usd"],
                    "status": ProgramOffer.Status.DRAFT,
                    "position": offer_data["position"],
                },
            )

        self.stdout.write(self.style.SUCCESS("✓ Created 3 offers (Starter, Complete, Guided)"))

        self.stdout.write(self.style.SUCCESS("\n✓ SYSTEM-C Method initialized successfully!"))
        self.stdout.write(
            "\nNext steps:\n"
            "  1. Edit program and resources in Django admin\n"
            "  2. Upload actual files to resources (guides, videos, etc.)\n"
            "  3. Publish offers when content is ready\n"
            "  4. Create public enrollment pages\n"
        )
