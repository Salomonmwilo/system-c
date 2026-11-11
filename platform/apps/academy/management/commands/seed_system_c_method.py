"""Installe ou complète la structure de SYSTEM-C Method dans une organisation.

    python manage.py seed_system_c_method --organization system-c --yes

La commande est rejouable : elle crée ce qui manque et ne modifie jamais un
élément existant. Elle ne rédige aucun contenu pédagogique :
- les 25 leçons reçoivent un titre et un résumé de l'objectif, sans contenu,
  et restent non publiées ;
- les ressources sont créées en brouillon, sans fichier ;
- les offres restent en brouillon, avec un prix indicatif modifiable.
Le rattachement des ressources aux offres suit le cahier des charges ; il n'est
posé que sur une ressource qui n'en a encore aucun.
"""

from decimal import Decimal

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import Max

from apps.academy.models import Course, Lesson, Program, ProgramOffer, Resource
from apps.core.models import Organization

PROGRAM = {
    "title_fr": "SYSTEM-C Method",
    "title_en": "SYSTEM-C Method",
    "description_fr": (
        "Un programme éducatif pour structurer son apprentissage du trading, organiser ses décisions "
        "et développer une approche consciente des risques."
    ),
    "description_en": (
        "An educational programme to structure how you learn about trading, organise your decisions "
        "and build a risk-aware approach."
    ),
}

# (titre FR, titre EN, [(titre FR, titre EN, résumé FR, résumé EN), ...])
STEPS = [
    ("Comprendre", "Understand", [
        ("Les bases de l'apprentissage du trading", "The basics of learning to trade",
         "Comprendre comment s'apprend une discipline nouvelle, étape par étape.",
         "Understand how a new discipline is learned, step by step."),
        ("La notion de risque", "The notion of risk",
         "Risque financier, psychologique et méthodologique.",
         "Financial, psychological and methodological risk."),
        ("Information, hypothèse et décision", "Information, hypothesis and decision",
         "Distinguer ce que l'on sait, ce que l'on pense et ce que l'on décide.",
         "Tell apart what you know, what you think and what you decide."),
        ("Identifier les limites de ses connaissances", "Recognising the limits of your knowledge",
         "Repérer ce que l'on ne sait pas encore et en tenir compte avant d'agir.",
         "Notice what you do not know yet and take it into account before acting."),
        ("Comprendre pourquoi aucune méthode ne garantit un résultat", "Why no method guarantees a result",
         "Une méthode organise le travail ; elle ne supprime ni l'incertitude ni le risque de perte.",
         "A method organises the work; it removes neither uncertainty nor the risk of loss."),
    ]),
    ("Préparer", "Prepare", [
        ("Définir ses objectifs d'apprentissage", "Setting your learning goals",
         "Savoir ce que l'on veut apprendre, et pourquoi.",
         "Know what you want to learn, and why."),
        ("Établir un cadre personnel de travail", "Setting a personal working framework",
         "Règles, horaires et discipline de travail.",
         "Rules, schedule and working discipline."),
        ("Comprendre les limites du capital exposé", "Understanding the limits of exposed capital",
         "Ne jamais exposer une somme dont la perte mettrait en difficulté.",
         "Never expose money whose loss would put you in difficulty."),
        ("Définir des règles de prudence", "Setting rules of caution",
         "Fixer à l'avance les limites que l'on s'engage à respecter.",
         "Set in advance the limits you commit to respecting."),
        ("Préparer son environnement d'apprentissage", "Preparing your learning environment",
         "Organiser le temps, les outils et le lieu consacrés à l'apprentissage.",
         "Organise the time, tools and place set aside for learning."),
    ]),
    ("Décider", "Decide", [
        ("Utiliser une checklist avant une décision", "Using a checklist before a decision",
         "Vérifier chaque critère avant d'agir, toujours dans le même ordre.",
         "Check each criterion before acting, always in the same order."),
        ("Identifier les informations disponibles", "Identifying the information available",
         "Distinguer les données, les analyses et les opinions.",
         "Tell apart data, analyses and opinions."),
        ("Examiner les raisons d'une décision", "Examining the reasons for a decision",
         "Vérifier que chaque décision repose sur des raisons explicites.",
         "Check that each decision rests on explicit reasons."),
        ("Identifier les décisions impulsives", "Recognising impulsive decisions",
         "Reconnaître la peur, la cupidité et les biais.",
         "Recognise fear, greed and biases."),
        ("Savoir s'abstenir lorsque les conditions ne sont pas réunies", "Knowing when to abstain",
         "Considérer l'abstention comme une décision à part entière.",
         "Treat not acting as a decision in its own right."),
    ]),
    ("Documenter", "Document", [
        ("Tenir un journal de décisions", "Keeping a decision journal",
         "Noter chaque décision et ses raisons.",
         "Record each decision and its reasons."),
        ("Consigner ses émotions", "Recording your emotions",
         "Observer le rôle des émotions dans ses décisions.",
         "Observe the part emotions play in your decisions."),
        ("Documenter ses erreurs", "Documenting your mistakes",
         "Décrire une erreur pour pouvoir la reconnaître la fois suivante.",
         "Describe a mistake so you can recognise it next time."),
        ("Noter ses observations", "Writing down your observations",
         "Consigner ce que l'on observe, séparément de ce que l'on en conclut.",
         "Record what you observe, separately from what you conclude."),
        ("Distinguer respect du processus et résultat financier", "Process versus financial outcome",
         "Juger une décision sur le respect de sa méthode, pas seulement sur son résultat.",
         "Judge a decision on whether you followed your method, not only on its outcome."),
    ]),
    ("Évaluer", "Evaluate", [
        ("Faire un bilan hebdomadaire", "Holding a weekly review",
         "Examiner ce qui a été respecté et ce qui ne l'a pas été.",
         "Review what was followed and what was not."),
        ("Identifier les habitudes à corriger", "Identifying habits to correct",
         "Reconnaître les comportements qui se répètent.",
         "Recognise behaviours that repeat."),
        ("Examiner les erreurs récurrentes", "Examining recurring mistakes",
         "Repérer les erreurs qui reviennent d'une semaine à l'autre.",
         "Spot the mistakes that come back week after week."),
        ("Définir les prochains objectifs d'apprentissage", "Setting the next learning goals",
         "Choisir ce que l'on travaillera ensuite.",
         "Choose what to work on next."),
        ("Construire un plan personnel d'amélioration", "Building a personal improvement plan",
         "Transformer le bilan en quelques actions concrètes pour la période suivante.",
         "Turn the review into a few concrete actions for the next period."),
    ]),
]

# (slug, nom FR, nom EN, prix indicatif, description FR, description EN)
OFFERS = [
    ("starter", "Starter Kit", "Starter Kit", Decimal("9.00"),
     "Guide introductif, checklist, journal simplifié, feuille de suivi du risque et vidéo d'introduction.",
     "Introductory guide, checklist, simplified journal, risk tracking sheet and introduction video."),
    ("complete", "Complete", "Complete", Decimal("29.00"),
     "Guide principal, journal de suivi sur 30 jours, feuille de gestion du capital et du risque, checklist "
     "complète, plan d'apprentissage de quatre semaines, mini-vidéos et exercices.",
     "Main guide, 30-day tracking journal, capital and risk management sheet, full checklist, four-week "
     "learning plan, short videos and exercises."),
    ("guided", "Guided", "Guided", Decimal("79.00"),
     "Tout le contenu Complete, deux ateliers collectifs, un parcours guidé de quatre semaines et un groupe "
     "privé temporaire et modéré.",
     "Everything in Complete, two group workshops, a four-week guided path and a temporary, moderated "
     "private group."),
]

C = Resource.Category
PUBLIC, OFFERS_ONLY = Resource.Visibility.PUBLIC, Resource.Visibility.OFFERS
ALL = ("starter", "complete", "guided")
FULL = ("complete", "guided")

# (titre FR, titre EN, catégorie, visibilité, description FR, description EN, offres)
RESOURCES = [
    ("Guide principal SYSTEM-C Method", "SYSTEM-C Method main guide", C.GUIDE, OFFERS_ONLY,
     "Guide de référence du programme, organisé selon les cinq étapes.",
     "The programme's reference guide, organised around the five steps.", FULL),
    ("Guide introductif", "Introductory guide", C.GUIDE, OFFERS_ONLY,
     "Présentation courte du programme et de ses cinq étapes.",
     "A short introduction to the programme and its five steps.", ("starter",)),
    ("Journal de suivi sur 30 jours", "30-day tracking journal", C.JOURNAL, OFFERS_ONLY,
     "Journal personnel pour consigner décisions, raisons et émotions pendant 30 jours.",
     "A personal journal to record decisions, reasons and emotions over 30 days.", FULL),
    ("Journal simplifié", "Simplified journal", C.JOURNAL, OFFERS_ONLY,
     "Version courte du journal de décisions.",
     "A short version of the decision journal.", ("starter",)),
    ("Feuille de gestion du capital et du risque", "Capital and risk management sheet", C.RISK_SHEET, OFFERS_ONLY,
     "Feuille pour fixer et suivre ses limites de capital exposé et de perte.",
     "A sheet to set and follow your limits on exposed capital and losses.", ALL),
    ("Checklist avant une décision", "Pre-decision checklist", C.CHECKLIST, OFFERS_ONLY,
     "Questions à vérifier avant chaque décision.",
     "Questions to check before each decision.", ALL),
    ("Plan d'apprentissage de quatre semaines", "Four-week learning plan", C.LEARNING_PLAN, OFFERS_ONLY,
     "Progression semaine par semaine à travers les cinq étapes.",
     "A week-by-week path through the five steps.", FULL),
    ("Vidéo d'introduction", "Introduction video", C.VIDEO, OFFERS_ONLY,
     "Présentation du programme en vidéo.",
     "A video introduction to the programme.", ("starter",)),
    ("Exercices et feuilles de réflexion", "Exercises and reflection sheets", C.EXERCISE, OFFERS_ONLY,
     "Exercices associés aux leçons.",
     "Exercises that go with the lessons.", FULL),
    ("7 questions à se poser avant une décision de trading", "7 questions to ask before a trading decision",
     C.DISCOVERY, PUBLIC,
     "Ressource gratuite pour découvrir la démarche SYSTEM-C Method.",
     "A free resource to discover the SYSTEM-C Method approach.", ()),
]


class Command(BaseCommand):
    help = "Installe ou complète la structure de SYSTEM-C Method (étapes, leçons, ressources, offres)."

    def add_arguments(self, parser):
        parser.add_argument("--organization", required=True, help="Identifiant de l'organisation")
        parser.add_argument("--yes", action="store_true", help="Ne pas demander de confirmation")

    def handle(self, *args, **options):
        try:
            org = Organization.objects.get(slug=options["organization"])
        except Organization.DoesNotExist as exc:
            raise CommandError(f"Organisation « {options['organization']} » introuvable.") from exc

        if not options["yes"]:
            answer = input(f"Compléter la structure de SYSTEM-C Method pour « {org.name} » ? (o/n) ")
            if answer.strip().lower() not in ("o", "oui", "y", "yes"):
                self.stdout.write("Annulé.")
                return

        counts = {"étapes": 0, "leçons": 0, "ressources": 0, "offres": 0, "rattachements": 0}
        with transaction.atomic():
            program, _ = Program.objects.get_or_create(
                organization=org, title_fr=PROGRAM["title_fr"], defaults={k: v for k, v in PROGRAM.items() if k != "title_fr"}
            )
            for position, (title_fr, title_en, lessons) in enumerate(STEPS, 1):
                course, created = Course.objects.get_or_create(
                    program=program, position=position, defaults={"title_fr": title_fr, "title_en": title_en}
                )
                counts["étapes"] += created
                for lesson_position, (l_fr, l_en, s_fr, s_en) in enumerate(lessons, 1):
                    _, created = Lesson.objects.get_or_create(
                        course=course,
                        title_fr=l_fr,
                        defaults={"title_en": l_en, "summary_fr": s_fr, "summary_en": s_en, "position": lesson_position},
                    )
                    counts["leçons"] += created

            offers = {}
            for position, (slug, name_fr, name_en, price, desc_fr, desc_en) in enumerate(OFFERS, 1):
                offers[slug], created = ProgramOffer.objects.get_or_create(
                    program=program,
                    slug=slug,
                    defaults={
                        "name_fr": name_fr, "name_en": name_en, "price": price, "currency": "USD",
                        "description_fr": desc_fr, "description_en": desc_en, "position": position,
                    },
                )
                counts["offres"] += created

            for title_fr, title_en, category, visibility, desc_fr, desc_en, offer_slugs in RESOURCES:
                resource = Resource.objects.filter(program=program, title_fr=title_fr).first()
                if resource is None:
                    last = program.resources.aggregate(m=Max("position"))["m"] or 0
                    resource = Resource.objects.create(
                        program=program, title_fr=title_fr, title_en=title_en, category=category,
                        visibility=visibility, description_fr=desc_fr, description_en=desc_en, position=last + 1,
                    )
                    counts["ressources"] += 1
                if resource.visibility == OFFERS_ONLY and offer_slugs and not resource.offers.exists():
                    resource.offers.set([offers[s] for s in offer_slugs])
                    counts["rattachements"] += 1

        created = ", ".join(f"{n} {label}" for label, n in counts.items())
        self.stdout.write(self.style.SUCCESS(f"SYSTEM-C Method pour « {org.name} » : créé {created}."))
        self.stdout.write(
            "Rien n'est publié : leçons sans contenu rédigé, ressources sans fichier, offres en brouillon."
        )
