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
- Pour tout travail d'interface, utiliser les skills du projet, dans cet ordre :
  1. `ui-ux-pro-max` : consulter sa base (profil produit « CRM », « Banking », règles d'ergonomie) avant de décider ;
  2. `frontend-design` : direction visuelle et plan de jetons ;
  3. `unslop` : passes de polissage (espacement, couleur, icônes, texte, typographie, mise en page, détails, mouvement) ;
  4. `frontend-design-audit` : audit d'ergonomie final et corrections.
  5. `web-interface-guidelines` (Vercel) et `accessibility` (WCAG 2.2) : revue des gabarits et audit des pages rendues, puis corrections.
- Direction retenue (passe `unslop`) : exact, posé, solennel ; univers du registre et du sceau. La signature est le filet d'or de `.sc-declared` : il ne sert qu'aux informations déclarées, non vérifiées.
- Identité imposée par le responsable : **noir et or, sobre et institutionnel**. Les jetons de design sont en tête de `platform/static/css/systemc.css`.
- Provenance et revue des skills : `.claude/skills/SOURCES.md`.
