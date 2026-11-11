"""Remise en forme du contenu créé par la première version de ``seed_system_c_method``.

Seules les lignes qui contiennent encore exactement les textes de cette première
version sont modifiées : un contenu déjà retouché à la main n'est pas touché.

- Les titres d'étape perdent le tiret long et les capitales (« Comprendre ») ;
  le numéro d'étape vient de la position.
- La phrase stockée comme contenu de leçon était un résumé : elle passe dans le
  résumé, et le contenu redevient vide (à rédiger).
- Deux leçons prennent la position prévue par la structure du programme.
- Les ressources reçoivent leur catégorie, et la ressource gratuite devient publique.
"""

from django.db import migrations

STEPS = {
    "Étape 1 — COMPRENDRE": ("Comprendre", "Understand"),
    "Étape 2 — PRÉPARER": ("Préparer", "Prepare"),
    "Étape 3 — DÉCIDER": ("Décider", "Decide"),
    "Étape 4 — DOCUMENTER": ("Documenter", "Document"),
    "Étape 5 — ÉVALUER": ("Évaluer", "Evaluate"),
}

# Ancien titre français : (ancien contenu FR, ancien contenu EN, nouvelle position ou None,
#                          nouveau titre FR, nouveau titre EN, résumé FR, résumé EN)
LESSONS = {
    "Les bases de l'apprentissage du trading": (
        "Comprendre comment on apprend et pourquoi aucune méthode ne garantit un résultat.",
        "Understand how we learn and why no method guarantees a result.",
        None,
        "Les bases de l'apprentissage du trading",
        "The basics of learning to trade",
        "Comprendre comment s'apprend une discipline nouvelle, étape par étape.",
        "Understand how a new discipline is learned, step by step.",
    ),
    "La notion de risque": (
        "Risque financier, psychologique et méthodologique.",
        "Financial, psychological and methodological risk.",
        None,
        "La notion de risque",
        "The notion of risk",
        "Risque financier, psychologique et méthodologique.",
        "Financial, psychological and methodological risk.",
    ),
    "Information, hypothèse et décision": (
        "Distinguer ce que vous savez, ce que vous pensez, et ce que vous décidez.",
        "Distinguish what you know, what you think, and what you decide.",
        None,
        "Information, hypothèse et décision",
        "Information, hypothesis and decision",
        "Distinguer ce que l'on sait, ce que l'on pense et ce que l'on décide.",
        "Tell apart what you know, what you think and what you decide.",
    ),
    "Définir ses objectifs d'apprentissage": (
        "Savoir ce qu'on veut apprendre et pourquoi.",
        "Know what you want to learn and why.",
        None,
        "Définir ses objectifs d'apprentissage",
        "Setting your learning goals",
        "Savoir ce que l'on veut apprendre, et pourquoi.",
        "Know what you want to learn, and why.",
    ),
    "Établir un cadre personnel de travail": (
        "Règles, horaires, discipline.",
        "Rules, schedules, discipline.",
        None,
        "Établir un cadre personnel de travail",
        "Setting a personal working framework",
        "Règles, horaires et discipline de travail.",
        "Rules, schedule and working discipline.",
    ),
    "Comprendre les limites du capital exposé": (
        "Ne jamais risquer plus que ce qu'on peut se permettre de perdre.",
        "Never risk more than you can afford to lose.",
        None,
        "Comprendre les limites du capital exposé",
        "Understanding the limits of exposed capital",
        "Ne jamais exposer une somme dont la perte mettrait en difficulté.",
        "Never expose money whose loss would put you in difficulty.",
    ),
    "Utiliser une checklist avant une décision": (
        "Vérifier systématiquement tous les critères.",
        "Systematically verify all criteria.",
        None,
        "Utiliser une checklist avant une décision",
        "Using a checklist before a decision",
        "Vérifier chaque critère avant d'agir, toujours dans le même ordre.",
        "Check each criterion before acting, always in the same order.",
    ),
    "Identifier les informations disponibles": (
        "Différencier les données, les analyses et les opinions.",
        "Differentiate data, analyses and opinions.",
        None,
        "Identifier les informations disponibles",
        "Identifying the information available",
        "Distinguer les données, les analyses et les opinions.",
        "Tell apart data, analyses and opinions.",
    ),
    "Identifier les décisions impulsives": (
        "Reconnaître la peur, la cupidité et les biais.",
        "Recognize fear, greed and biases.",
        4,
        "Identifier les décisions impulsives",
        "Recognising impulsive decisions",
        "Reconnaître la peur, la cupidité et les biais.",
        "Recognise fear, greed and biases.",
    ),
    "Tenir un journal de décisions": (
        "Noter chaque décision et ses raisons.",
        "Record each decision and its reasons.",
        None,
        "Tenir un journal de décisions",
        "Keeping a decision journal",
        "Noter chaque décision et ses raisons.",
        "Record each decision and its reasons.",
    ),
    "Consigner ses émotions": (
        "Comprendre le rôle des émotions dans vos décisions.",
        "Understand the role of emotions in your decisions.",
        None,
        "Consigner ses émotions",
        "Recording your emotions",
        "Observer le rôle des émotions dans ses décisions.",
        "Observe the part emotions play in your decisions.",
    ),
    "Documenter ses erreurs": (
        "Apprendre de ses erreurs sans les répéter.",
        "Learn from your mistakes without repeating them.",
        None,
        "Documenter ses erreurs",
        "Documenting your mistakes",
        "Décrire une erreur pour pouvoir la reconnaître la fois suivante.",
        "Describe a mistake so you can recognise it next time.",
    ),
    "Faire un bilan hebdomadaire": (
        "Analyser ce qui a fonctionné et ce qui ne fonctionne pas.",
        "Analyze what worked and what did not.",
        None,
        "Faire un bilan hebdomadaire",
        "Holding a weekly review",
        "Examiner ce qui a été respecté et ce qui ne l'a pas été.",
        "Review what was followed and what was not.",
    ),
    "Identifier les habitudes à corriger": (
        "Reconnaître les schémas répétitifs.",
        "Recognize repetitive patterns.",
        None,
        "Identifier les habitudes à corriger",
        "Identifying habits to correct",
        "Reconnaître les comportements qui se répètent.",
        "Recognise behaviours that repeat.",
    ),
    "Définir les prochains objectifs": (
        "Construire un plan d'amélioration.",
        "Build an improvement plan.",
        4,
        "Définir les prochains objectifs d'apprentissage",
        "Setting the next learning goals",
        "Choisir ce que l'on travaillera ensuite.",
        "Choose what to work on next.",
    ),
}

# Ancien titre : (ancienne description FR, nouveau titre FR, nouveau titre EN, catégorie, visibilité,
#                 nouvelle description FR, nouvelle description EN)
RESOURCES = {
    "Guide SYSTEM-C Method": (
        "Guide complet du programme (35-50 pages)",
        "Guide principal SYSTEM-C Method",
        "SYSTEM-C Method main guide",
        "guide",
        "offers",
        "Guide de référence du programme, organisé selon les cinq étapes.",
        "The programme's reference guide, organised around the five steps.",
    ),
    "Journal de suivi 30 jours": (
        "Journal personnel pour documenter vos décisions",
        "Journal de suivi sur 30 jours",
        "30-day tracking journal",
        "journal",
        "offers",
        "Journal personnel pour consigner décisions, raisons et émotions pendant 30 jours.",
        "A personal journal to record decisions, reasons and emotions over 30 days.",
    ),
    "Feuille de gestion du risque": (
        "Suivi du capital et des limites",
        "Feuille de gestion du capital et du risque",
        "Capital and risk management sheet",
        "risk_sheet",
        "offers",
        "Feuille pour fixer et suivre ses limites de capital exposé et de perte.",
        "A sheet to set and follow your limits on exposed capital and losses.",
    ),
    "Checklist avant une décision": (
        "7 points à vérifier avant chaque décision",
        "Checklist avant une décision",
        "Pre-decision checklist",
        "checklist",
        "offers",
        "Questions à vérifier avant chaque décision.",
        "Questions to check before each decision.",
    ),
    "Plan d'apprentissage 4 semaines": (
        "Progression structurée sur 4 semaines",
        "Plan d'apprentissage de quatre semaines",
        "Four-week learning plan",
        "learning_plan",
        "offers",
        "Progression semaine par semaine à travers les cinq étapes.",
        "A week-by-week path through the five steps.",
    ),
    "Introduction vidéo": (
        "Présentation du programme (à créer)",
        "Vidéo d'introduction",
        "Introduction video",
        "video",
        "offers",
        "Présentation du programme en vidéo.",
        "A video introduction to the programme.",
    ),
    "7 questions avant une décision (gratuit)": (
        "Ressource gratuite de découverte",
        "7 questions à se poser avant une décision de trading",
        "7 questions to ask before a trading decision",
        "discovery",
        "public",
        "Ressource gratuite pour découvrir la démarche SYSTEM-C Method.",
        "A free resource to discover the SYSTEM-C Method approach.",
    ),
}


def forwards(apps, schema_editor):
    Course = apps.get_model("academy", "Course")
    Lesson = apps.get_model("academy", "Lesson")
    Resource = apps.get_model("academy", "Resource")

    for old, (fr, en) in STEPS.items():
        Course.objects.filter(title_fr=old).update(title_fr=fr, title_en=en)

    for lesson in Lesson.objects.filter(title_fr__in=LESSONS.keys()):
        old_body_fr, old_body_en, position, title_fr, title_en, summary_fr, summary_en = LESSONS[lesson.title_fr]
        if lesson.body_fr != old_body_fr or lesson.body_en not in ("", old_body_en):
            continue  # contenu retouché à la main : on n'y touche pas
        lesson.title_fr, lesson.title_en = title_fr, title_en
        lesson.summary_fr, lesson.summary_en = summary_fr, summary_en
        lesson.body_fr = lesson.body_en = ""
        if position is not None:
            lesson.position = position
        lesson.save()

    for resource in Resource.objects.filter(title_fr__in=RESOURCES.keys()):
        old_description, title_fr, title_en, category, visibility, description_fr, description_en = RESOURCES[
            resource.title_fr
        ]
        resource.title_fr, resource.title_en = title_fr, title_en
        resource.category, resource.visibility = category, visibility
        if resource.description_fr == old_description:
            resource.description_fr, resource.description_en = description_fr, description_en
        resource.save()

    # Anciennes catégories sans équivalent.
    Resource.objects.filter(category="worksheet").update(category="exercise")
    Resource.objects.filter(category="other").update(category="guide")


class Migration(migrations.Migration):
    dependencies = [("academy", "0004_integrity_and_resource_fields")]

    operations = [migrations.RunPython(forwards, migrations.RunPython.noop)]
