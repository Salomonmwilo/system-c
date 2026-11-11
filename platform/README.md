# SYSTEM-C Platform

Plateforme SaaS bilingue (français / anglais) de SYSTEM-C : gestion des affiliés (**Partners**), registre administratif des utilisateurs de robots (**Bot Management**) et structure initiale de formation (**Academy**).

> **Bot Management est un CRM administratif.** La plateforme ne se connecte jamais au VPS, ne pilote aucun robot et ne stocke aucun token Deriv, mot de passe ni clé API. Les statuts affichés sont ceux qu'un administrateur a déclarés.

Documents de conception : `../docs/platform/NEW_PROJECT_DIRECTION.md` (révision de référence) et `../docs/platform/BOT_CRM_SPEC.md`. État de cette version : `../docs/platform/MVP_REPORT.md`.

---

## Prérequis

| Outil | Version | Remarque |
|---|---|---|
| Python | 3.12 ou plus récent (testé avec 3.13) | |
| PostgreSQL | 16 | installé localement, ou via `compose.yaml` (Docker) |
| gettext | facultatif | seulement pour régénérer les traductions |

Dépendances Python (figées dans `requirements.txt`) : Django 5.2 LTS, psycopg 3, argon2-cffi. Bootstrap 5.3.8 et Bootstrap Icons 1.13.2 sont fournis dans `static/vendor/` : aucun CDN, aucun service externe.

## Installation locale

Toutes les commandes s'exécutent depuis le dossier `platform/`.

```bash
cd platform
python3 -m venv .venv
source .venv/bin/activate            # Windows : .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env                 # puis éditez .env (mot de passe PostgreSQL, etc.)
```

### Base de données

**Option A, Docker :**

```bash
docker compose --env-file .env up -d db
```

**Option B, PostgreSQL déjà installé :** créez un rôle et une base correspondant à `.env`. Le rôle doit pouvoir créer des bases pour que les tests fonctionnent :

```sql
CREATE ROLE systemc LOGIN PASSWORD 'votre-mot-de-passe' CREATEDB;
CREATE DATABASE systemc OWNER systemc ENCODING 'UTF8' TEMPLATE template0;
```

### Initialisation

```bash
python manage.py migrate
python manage.py createcachetable
python manage.py bootstrap_platform --organization "SYSTEM-C" \
    --email admin@example.org --full-name "Administrateur SYSTEM-C"
```

`bootstrap_platform` demande le mot de passe de façon interactive. Pour un script, utilisez la variable `SYSTEMC_ADMIN_PASSWORD` avec `--no-input`, jamais un argument de ligne de commande. La commande crée l'organisation, le compte administrateur (rôles `org_admin` et `crm_admin`), les seuils d'alerte par défaut et la liste blanche des paramètres. Elle peut être relancée sans risque.

### Lancement

```bash
python manage.py runserver
```

Ouvrez http://127.0.0.1:8000 et connectez-vous avec le compte créé.

### Données de démonstration (facultatif)

```bash
python manage.py seed_demo_data --organization system-c --admin-email admin@example.org --yes
```

Crée six fiches fictives préfixées « [Démo] ». La commande est refusée hors mode `DEBUG`.

### Structure de SYSTEM-C Method

```bash
python manage.py seed_system_c_method --organization system-c --yes
```

Crée ou complète le programme : 5 étapes, 25 leçons (titre et résumé, sans contenu rédigé), 10 ressources en brouillon sans fichier et 3 offres en brouillon (prix indicatifs 9, 29 et 79 USD). La commande peut être relancée : elle ajoute ce qui manque et ne modifie jamais un élément existant. Rien n'est publié.

Les fichiers des ressources sont enregistrés dans `private_media/` (ou `SYSTEMC_PRIVATE_MEDIA_ROOT`), hors des fichiers statiques, sans adresse publique et ignorés par Git.

### Essayer le parcours de commande (facultatif)

```bash
python manage.py seed_academy_demo --organization system-c --yes
```

Crée un programme et une offre d'essai publiés, marqués « [Démo] » (5,00 USD fictifs), avec des ressources qui pointent vers example.org. Refusé hors mode `DEBUG`. Aucune commande ni aucun paiement n'est simulé : commandez l'offre depuis « Offres », puis confirmez-la depuis « Commandes » avec une note. Les offres réelles de SYSTEM-C Method restent en brouillon et ne peuvent pas être commandées.

L'administration Django (`/admin`) reste désactivée : elle contournerait l'isolation par organisation. Voir `docs/platform/SYSTEM_C_METHOD_AUDIT.md`.

## Tests

```bash
python manage.py test
```

Les tests utilisent PostgreSQL : les protections en base (déclencheurs d'immuabilité, contraintes) sont réellement exercées. Couverture : authentification, limitation des tentatives, permissions de chaque route, isolation entre organisations, immuabilité, règles du compte réel, liste blanche, alertes, traductions, en-têtes de sécurité, frontières entre modules.

## Traductions

Les textes du code sont en anglais, l'interface est en français par défaut. Après modification de textes :

```bash
python manage.py makemessages -l fr --no-location --ignore=.venv --ignore=staticfiles
python locale/translate_fr.py        # signale toute chaîne non traduite
python manage.py compilemessages -l fr --ignore=.venv
```

Ajoutez les nouvelles traductions dans le dictionnaire de `locale/translate_fr.py`. Le fichier compilé `django.mo` est versionné : gettext n'est pas nécessaire pour lancer l'application.

## Structure

```
platform/
├── config/            réglages Django, URLs, lecture de .env
├── apps/
│   ├── core/          utilisateurs, organisations, rôles, permissions, audit, seuils, tableau de bord
│   ├── partners/      affiliés (fiche principale), parcours Deriv, interactions, relances, liens
│   ├── bots/          CRM : fiches robot, versions immuables, déclarations, liste blanche
│   └── academy/       programmes (SYSTEM-C Method) : étapes, leçons, ressources, offres, commandes, inscriptions
├── templates/         gabarit de base, navigation, composants
├── static/            thème noir et or, logo, Bootstrap local
└── locale/fr/         catalogue français
```

Règles de dépendance : `core` ne dépend d'aucun module. `partners` ne dépend que de `core`. `bots` et `academy` référencent les affiliés de `partners` par identifiant. Les tests vérifient ces règles.

## Rôles

| Rôle | Usage principal |
|---|---|
| `org_admin` | membres et rôles, journal d'audit ; commandes d'Academy : consultation, **confirmation manuelle des paiements**, annulation, remboursement (permissions `payments.*`) |
| `crm_admin` | CRM complet, validation des versions, **seul rôle autorisé à déclarer un compte réel**, seuils, liste blanche |
| `crm_operator` | fiches robot, brouillons démo, déclarations d'application démo, pauses, interactions |
| `crm_viewer` | lecture seule, données personnelles masquées |
| `partner_manager` | affiliés, parcours, relances, liens de parrainage |
| `partner_advisor` | uniquement les affiliés qui lui sont attribués |
| `academy_instructor`, `academy_student` | module Academy uniquement : consulter les programmes et les offres, commander |

Un même compte peut cumuler plusieurs rôles. Le statut de super-utilisateur Django ne donne accès à aucune donnée d'organisation, ni aucune permission de paiement. Un futur rôle `finance_admin` pourra recevoir les permissions `payments.*` (voir `apps/core/permissions.py`).

## Production (à compléter avant toute mise en ligne)

- `DJANGO_DEBUG=False`, `DJANGO_SECRET_KEY` longue et aléatoire, `DJANGO_ALLOWED_HOSTS`, `DJANGO_CSRF_TRUSTED_ORIGINS`.
- Service HTTPS devant l'application (reverse proxy). Avec un proxy TLS, définir `DJANGO_BEHIND_TLS_PROXY=True`.
- Fichiers statiques : `python manage.py collectstatic`, servis par le reverse proxy.
- Serveur d'application (par exemple gunicorn) : non inclus dans cette version.
- `python manage.py check --deploy` ne doit laisser que les avertissements HSTS sous-domaines et préchargement, à activer après décision sur le domaine.
- Sauvegardes chiffrées de PostgreSQL et test de restauration.
