# Consignes pour Claude Code sur ce dépôt

## Produit
- Le produit actif est **SYSTEM-C Platform**, dans `platform/` (Django 5.2 LTS, PostgreSQL, gabarits Django, Bootstrap fourni en local). Instructions : `platform/README.md`.
- L'ancien site vitrine (`public/`, `netlify.toml`, `.github/workflows/pages.yml`) est conservé pour mémoire : ne pas le maintenir ni le supprimer.
- Documents de conception : `docs/platform/NEW_PROJECT_DIRECTION.md` (révision la plus récente), `docs/platform/BOT_CRM_SPEC.md`, `docs/platform/MVP_REPORT.md`.

## Règles non négociables
- BOT MANAGEMENT est un **CRM administratif** : aucune connexion au VPS ou à Deriv, aucun stockage de token, mot de passe ou clé API.
- Seul le rôle `crm_admin` peut déclarer un compte réel.
- Toute page privée déclare sa permission ; toute requête est filtrée par organisation.
- Pas de script ni de style en ligne (CSP stricte) ; pas de CDN ni de service externe.
- Toute chaîne visible passe par la traduction FR/EN (`platform/locale/translate_fr.py`).
- Lancer `python manage.py test` (dans `platform/`) avant chaque commit.

## Design
- Pour tout travail d'interface, utiliser les skills du projet :
  - `frontend-design` pour la direction visuelle ;
  - `frontend-design-audit` pour auditer puis corriger l'ergonomie.
- Identité imposée par le responsable : **noir et or, sobre et institutionnel**. Les jetons de design sont en tête de `platform/static/css/systemc.css`.
- Provenance et revue des skills : `.claude/skills/SOURCES.md`.
