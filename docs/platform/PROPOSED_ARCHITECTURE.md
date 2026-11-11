> **Document remplacé (2026-11-09).** Cette version supposait une vitrine à préserver. L'orientation actuelle est décrite dans `NEW_PROJECT_DIRECTION.md`. Contenu conservé comme historique.

> **Amendement rév. 2 (2026-11-09).** Le module BOT MANAGEMENT est désormais un **CRM administratif** (sans contrôle technique, sans lien avec le VPS). Retirés : R-BOT-1 (agent), R-BOT-2 (requêtes signées), R-BOT-3 (écriture de configuration), la communication VPS du schéma et l'arborescence `agent/`, R-OPS-1 (placement de l'agent), et R-SEC-3 remplacé par l'interdiction totale de stocker des tokens (`NEW_PROJECT_DIRECTION.md` §7.4). Référence actuelle : `NEW_PROJECT_DIRECTION.md` §4 et §6.4.

# SYSTEM-C : architecture proposée

Objectif : faire évoluer SYSTEM-C vers SYSTEM-C Platform en **réutilisant le maximum de l'existant**, sans réécrire la vitrine ni remplacer l'architecture sans justification.

Chaque recommandation indique : **pourquoi**, **fichiers concernés**, **changements cassants**, **complexité** (S / M / L / XL) et **implications de sécurité**.

Statut : proposition à valider. Aucun code n'a été modifié pendant cette phase.

---

## 1. Vue d'ensemble

```
                     ┌──────────────────────────────┐
  Visiteurs ───────▶ │  Site vitrine (inchangé)     │  Netlify, publish = public/
                     │  public/index.html …         │  CSP stricte, statique
                     └──────────────────────────────┘
                     ┌──────────────────────────────┐        ┌─────────────────────┐
  Équipe / étudiants▶│  SYSTEM-C Platform           │───────▶│ PostgreSQL 16       │
  / partenaires      │  platform/ (FastAPI, Jinja2) │        │ (réseau privé)      │
                     │  sessions, RBAC, i18n FR/EN  │        └─────────────────────┘
                     └──────────────▲───────────────┘
                                    │ HTTPS sortant de l'agent uniquement
                                    │ requêtes signées (HMAC, horodatage, nonce)
                     ┌──────────────┴───────────────┐
                     │  Agent VPS Ubuntu            │  Lit l'état des bots Python,
                     │  systemc-agent (Python)      │  publie heartbeats et rapports
                     └──────────────┬───────────────┘
                                    │ fichiers / API locale
                     ┌──────────────┴───────────────┐
                     │  Bots Python existants       │  Differs, Over/Under
                     └──────────────────────────────┘
```

Principe directeur : **le site vitrine reste un site statique isolé** ; la plateforme est une application séparée qui partage le design et le contenu ; le VPS **n'expose aucun port entrant** pour la plateforme.

---

## 2. Organisation du dépôt

### R-ARCH-1 : Garder le site vitrine à l'emplacement actuel et ajouter la plateforme à côté
- **Pourquoi** : `netlify.toml` pointe sur `public/`. Déplacer la vitrine casserait le déploiement, les URL et le SEO. Ajouter un dossier séparé est le moyen le moins risqué de respecter « ne rien supprimer ».
- **Fichiers concernés** : création de `platform/` (application), `docs/platform/` (documentation, déjà créée), `platform/Dockerfile`, `platform/pyproject.toml`, `platform/tests/`. Aucun fichier de `public/` modifié.
- **Changements cassants** : aucun.
- **Complexité** : S.
- **Sécurité** : séparer les dépendances. Le site vitrine n'embarque aucune dépendance de la plateforme, donc aucune surface d'attaque partagée.

Arborescence cible :
```
system-c/
├── public/              site vitrine (inchangé, publié par Netlify)
├── platform/            SYSTEM-C Platform
│   ├── app/             code FastAPI (routes, services, modèles)
│   ├── templates/       Jinja2 (réutilise styles.css via /static)
│   ├── static/          styles.css et script.js partagés (copie ou lien, voir R-DEBT-1)
│   ├── migrations/      Alembic
│   ├── tests/
│   ├── agent/           systemc-agent (paquet Python pour les VPS)
│   ├── Dockerfile
│   └── pyproject.toml
├── shared/i18n/         fr.json, en.json (source unique des libellés, voir R-I18N-1)
├── docs/platform/       documentation d'audit et de feuille de route
├── netlify.toml         inchangé
└── .github/workflows/   tests et build ajoutés, pages.yml traité (R-SEC-2)
```

---

## 3. Choix technologiques

### R-ARCH-2 : Python (FastAPI) + Jinja2 rendu serveur + PostgreSQL
- **Pourquoi** :
  - Les bots existants sont en **Python** : une seule langue pour la plateforme, l'agent et les scripts d'import.
  - Le rendu serveur (Jinja2) permet de **réutiliser `styles.css` et `script.js` tels quels**, garde un HTML lisible, et évite un bundle JavaScript lourd.
  - FastAPI + SQLAlchemy 2 + Alembic sont des standards matures, peu nombreux en dépendances.
  - PostgreSQL est imposé par la vision.
- **Alternative écartée** : Next.js / React. Coûteux en dépendances et en build, impose une réécriture du rendu et de la bascule de langue ; pertinent seulement si l'équipe est déjà orientée TypeScript.
- **Fichiers concernés** : `platform/pyproject.toml`, `platform/app/main.py`, `platform/templates/base.html`.
- **Changements cassants** : aucun (nouveau code).
- **Complexité** : M (mise en place), puis récurrente.
- **Sécurité** : FastAPI n'impose pas de sécurité par défaut ; il faut une configuration explicite (CSRF, en-têtes, cookies, validation Pydantic stricte sur toutes les entrées). Garder les dépendances minimales et les épingler.

Dépendances initiales proposées (à valider) : `fastapi`, `uvicorn`, `sqlalchemy`, `alembic`, `psycopg[binary]`, `jinja2`, `argon2-cffi`, `pydantic-settings`. Tests : `pytest`, `httpx`, `playwright` (en développement seulement). Aucun ORM ou framework supplémentaire.

### R-ARCH-3 : Rendu HTML plutôt que SPA, JavaScript progressif
- **Pourquoi** : la vitrine est indexée ; une SPA dégraderait le SEO et le mode sans JavaScript (cf. S1). Le besoin interactif de la plateforme (tableaux, filtres) se couvre par des formulaires classiques et, si nécessaire, un peu de JavaScript.
- **Fichiers concernés** : `platform/templates/*`, `platform/static/app.js` (optionnel, limité).
- **Changements cassants** : aucun.
- **Complexité** : S.
- **Sécurité** : rendu serveur avec échappement automatique Jinja2 (`autoescape` activé) ; interdire `|safe` sur les données utilisateur (règle de revue).

---

## 4. Données et multi-organisation

### R-DATA-1 : Modèle de données initial (version 1)
- **Pourquoi** : couvrir les trois modules sans sur-concevoir ; chaque table locataire porte `organization_id`.
- **Fichiers concernés** : `platform/app/models/*.py`, `platform/migrations/versions/0001_*.py`.
- **Changements cassants** : aucun.
- **Complexité** : M.
- **Sécurité** : les données personnelles (prospects, étudiants) sont identifiées ; journal d'audit obligatoire pour les actions sensibles (R-SEC-6).

Tables proposées :

| Domaine | Tables |
|---|---|
| Identité | `user`, `session`, `totp_secret` (chiffré), `password_reset` |
| Organisation | `organization`, `membership` (utilisateur, organisation, rôle), `role`, `permission`, `role_permission` |
| Académie | `programme`, `course`, `lesson`, `lesson_content` (locale), `exercise`, `enrollment`, `submission`, `progress_event` |
| Partenaires | `referral_link`, `lead` (consentement, source, pays), `onboarding_status`, `onboarding_event`, `follow_up` |
| Bots | `bot_type` (Differs, Over/Under), `bot_user`, `bot_environment` (demo/real), `bot_config`, `bot_config_version`, `agent`, `heartbeat`, `service_check`, `incident`, `incident_event`, `report_run` |
| Transverse | `audit_log` (append-only), `translation_key` (si besoin de contenu éditable) |

Règles : clés étrangères **composites** `(organization_id, id)` pour empêcher qu'une ligne d'une organisation référence une ligne d'une autre ; `audit_log` sans mise à jour ni suppression (droits de la base).

### R-DATA-2 : Multi-organisation par colonne partagée, isolation applicative puis RLS
- **Pourquoi** : une base par organisation complique les migrations et les sauvegardes à ce stade. Une base partagée avec `organization_id` est standard ; l'isolation est renforcée par des tests et, à terme, par la RLS PostgreSQL.
- **Fichiers concernés** : `platform/app/services/tenancy.py`, `platform/tests/test_isolation.py`, migrations de RLS (phase 7).
- **Changements cassants** : aucun.
- **Complexité** : L (la règle est simple, la discipline est difficile).
- **Sécurité** : chaque requête passe par un contexte d'organisation résolu côté serveur (jamais depuis un paramètre libre sans vérification d'appartenance). Tests d'isolation obligatoires : un utilisateur de A reçoit 404 (et non 403) sur les ressources de B.

---

## 5. Authentification, rôles, sécurité

### R-SEC-A : Authentification par sessions serveur
- **Pourquoi** : révocation immédiate, pas de jeton longue durée côté navigateur.
- **Détail** : cookie `__Host-session` (`HttpOnly`, `Secure`, `SameSite=Lax`, `Path=/`), identifiant aléatoire de 256 bits stocké haché, expiration glissante, rotation à la connexion.
- **Mots de passe** : Argon2id (`argon2-cffi`), politique de longueur minimale, vérification contre les fuites connues optionnelle.
- **Administrateurs** : TOTP obligatoire (`totp_secret` chiffré au repos).
- **Anti-abus** : limitation de débit sur la connexion et la réinitialisation ; réponses identiques pour un compte existant ou non.
- **Fichiers concernés** : `platform/app/auth/*.py`, `platform/app/models/user.py`, `platform/app/models/session.py`.
- **Changements cassants** : aucun.
- **Complexité** : L.
- **Sécurité** : c'est le cœur du risque. Tests dédiés (fixation de session, réutilisation après déconnexion, expiration).

### R-SEC-B : Contrôle d'accès basé sur les rôles (RBAC) avec refus par défaut
- **Pourquoi** : les rôles de la vision (plateforme, organisation, partenaire, instructeur, étudiant, opérateur bot, lecteur) se combinent par organisation.
- **Détail** : une seule fonction `authorize(user, action, resource)` appelée par chaque service ; aucune route ne contourne le service ; une route sans permission déclarée échoue au démarrage (test).
- **Fichiers concernés** : `platform/app/auth/policy.py`, `platform/tests/test_policy.py`.
- **Changements cassants** : aucun.
- **Complexité** : M.
- **Sécurité** : principe du moindre privilège ; séparation des rôles « partenaire » (prospects) et « opérateur bot » (exploitation).

### R-SEC-C : En-têtes et protection CSRF pour la plateforme
- **Pourquoi** : la plateforme gère des données personnelles et des actions d'écriture.
- **Détail** : CSP propre à la plateforme (nonces pour les rares scripts ; `frame-ancestors 'none'`), HSTS, `Referrer-Policy`, `X-Content-Type-Options`, jeton CSRF sur tous les formulaires POST, vérification `Origin` pour les requêtes d'écriture.
- **Fichiers concernés** : `platform/app/middleware/security.py`, `platform/app/middleware/csrf.py`.
- **Changements cassants** : aucun (le site vitrine garde sa CSP dans `netlify.toml`).
- **Complexité** : S.
- **Sécurité** : prévient le détournement de session et le clickjacking.

### R-SEC-2 : Clarifier la cible de publication du site vitrine (Netlify ou GitHub Pages)
- **Pourquoi** : constat S2 et S3. GitHub Pages ne lit pas `netlify.toml` (pas de CSP ni HSTS) et crée une seconde URL.
- **Options** :
  - (a) **Recommandée** : Netlify seul. Désactiver ou supprimer `pages.yml` après confirmation que Pages n'est pas utilisé comme lien public.
  - (b) Garder les deux, avec une balise `<meta http-equiv="Content-Security-Policy">` de repli sur la vitrine (sans `frame-ancestors`, qui n'est pas pris en charge en méta) et une `canonical` unique.
- **Fichiers concernés** : `.github/workflows/pages.yml` (suppression ou désactivation), éventuellement `public/index.html` (méta CSP, canonique).
- **Changements cassants** : si un lien public pointe vers l'URL GitHub Pages, il cessera de fonctionner (option a). Vérifier d'abord les liens existants.
- **Complexité** : S.
- **Sécurité** : une seule politique de sécurité à maintenir.

### R-SEC-3 : Ne jamais stocker les jetons de compte Deriv en clair
- **Pourquoi** : un jeton d'API Deriv donne accès à un compte financier. Une fuite de la base serait critique.
- **Détail** :
  - Préférer que les jetons restent **sur le VPS**, dans l'environnement de l'agent (fichier `0600`, utilisateur dédié), jamais envoyés à la plateforme.
  - La plateforme ne stocke que des empreintes (hachage) et des libellés.
  - Préférer des jetons à portée minimale (lecture seule quand c'est possible), avec procédure de rotation.
  - Si un stockage chiffré devient indispensable : chiffrement d'enveloppe (clé hors base, par exemple via un gestionnaire de secrets), jamais dans le dépôt.
- **Fichiers concernés** : `platform/app/models/bot_user.py` (champs d'empreinte uniquement), `agent/systemc_agent/config.py`, documentation d'exploitation.
- **Changements cassants** : aucun (fonctionnalité nouvelle).
- **Complexité** : M.
- **Sécurité** : c'est la protection principale des fonds des utilisateurs. À valider avant toute intégration réelle.

### R-SEC-4 : Gestion des secrets hors dépôt
- **Pourquoi** : aucun secret n'existe aujourd'hui, mais la plateforme en aura (clé de session, clé de signature de l'agent, base).
- **Détail** : variables d'environnement injectées par l'hébergeur ou fichier hors dépôt ; `.env.example` sans valeurs ; détection de secrets en CI (`gitleaks` ou équivalent) ; `.gitignore` étendu (`.env`, `*.pem`, `*.key`).
- **Fichiers concernés** : `.gitignore`, `platform/.env.example`, `.github/workflows/ci.yml`.
- **Changements cassants** : aucun.
- **Complexité** : S.
- **Sécurité** : réduit le risque de fuite par commit.

### R-SEC-5 : Journal d'audit en ajout seul
- **Pourquoi** : la vision exige des rapports et une supervision d'incidents ; toute action d'administration ou de configuration de bot doit être traçable.
- **Détail** : `audit_log` (acteur, organisation, action, cible, horodatage, résultat) ; droits PostgreSQL sans `UPDATE` ni `DELETE` pour l'application.
- **Fichiers concernés** : `platform/app/services/audit.py`, migration `0002_audit`.
- **Changements cassants** : aucun.
- **Complexité** : S.
- **Sécurité** : traçabilité et détection ; pas de données secrètes dans le journal.

---

## 6. Communication avec le VPS et les bots

### R-BOT-1 : Agent poussé depuis le VPS (sortant uniquement)
- **Pourquoi** : le VPS n'ouvre aucun port entrant pour la plateforme ; réduit la surface d'attaque. Les bots restent sous le contrôle du VPS.
- **Détail** : `systemc-agent` (paquet Python) envoie des heartbeats et des rapports en HTTPS vers `POST /api/agent/v1/...`. Mode **lecture seule** par défaut ; aucune commande de trading.
- **Fichiers concernés** : `platform/agent/systemc_agent/*.py`, `platform/app/api/agent.py`.
- **Changements cassants** : aucun (nouveau).
- **Complexité** : M.
- **Sécurité** : voir R-BOT-2.

### R-BOT-2 : Requêtes signées avec anti-rejeu
- **Pourquoi** : empêcher l'usurpation d'un agent et le rejeu de messages.
- **Détail** : HMAC-SHA256 sur `méthode + chemin + horodatage + nonce + empreinte du corps` ; secret propre à chaque agent, stocké haché côté plateforme ; fenêtre d'horodatage de 5 minutes ; nonce mémorisé ; révocation d'agent immédiate ; TLS obligatoire. mTLS possible en phase ultérieure.
- **Fichiers concernés** : `platform/app/auth/agent_signature.py`, `platform/agent/systemc_agent/client.py`.
- **Changements cassants** : aucun.
- **Complexité** : M.
- **Sécurité** : comparaison à temps constant ; journalisation des rejets.

### R-BOT-3 : Commandes d'écriture désactivées par défaut
- **Pourquoi** : la gestion de configuration (vision) peut modifier des bots sur comptes réels. Tant que la gouvernance n'est pas en place, rien ne doit être exécuté côté VPS depuis la plateforme.
- **Détail** : configuration versionnée et approuvée (deux personnes pour `real`) ; l'agent applique une configuration seulement si sa signature est valide et si la version est supérieure à la précédente.
- **Fichiers concernés** : `platform/app/services/bot_config.py`, `platform/agent/systemc_agent/apply.py`.
- **Changements cassants** : aucun.
- **Complexité** : L.
- **Sécurité** : principe des quatre yeux ; interrupteur d'arrêt d'urgence ; aucune exécution de code distant.

---

## 7. Internationalisation

### R-I18N-1 : Une seule source FR/EN pour la vitrine et la plateforme
- **Pourquoi** : aujourd'hui les textes FR sont dupliqués entre HTML et `script.js` (D1), et les 219 clés sont mélangées au code.
- **Détail** : extraire `translations.fr` et `translations.en` vers `shared/i18n/fr.json` et `shared/i18n/en.json` ; `script.js` les charge via un petit fichier généré, ou un script de build les injecte ; la plateforme les lit côté serveur. Les contenus éditables (cours, liens) ont des champs `*_fr` / `*_en`.
- **Fichiers concernés** : `public/script.js` (lignes 1-33), `shared/i18n/*.json`, `platform/app/i18n.py`, `scripts/build_i18n.py`.
- **Changements cassants** : **oui, potentiellement** : si l'extraction change l'ordre de chargement, le premier rendu peut afficher du texte brut. Mitigation : le HTML garde son texte FR par défaut (déjà le cas).
- **Complexité** : M.
- **Sécurité** : les contenus éditables sont texte brut par défaut ; le HTML (`<em>`) n'est autorisé que dans les clés de traduction statiques, ou via un sous-ensemble validé.

---

## 8. Hébergement et exploitation

### R-OPS-1 : Vitrine sur Netlify, plateforme dans un conteneur, base PostgreSQL privée
- **Pourquoi** : la vitrine reste gratuite et statique ; la plateforme a besoin d'un processus et d'une base.
- **Options** :

| Option | Avantages | Inconvénients | Recommandation |
|---|---|---|---|
| A. Conteneur sur le VPS Ubuntu existant (Docker, Caddy en TLS, PostgreSQL dans un réseau Docker privé) | Coût nul, déjà maîtrisé | Partage de machine avec les bots : risque de propagation ; sauvegardes à organiser | **Acceptable pour phases 2 à 4**, sous réserve d'un utilisateur système dédié, pare-feu, mises à jour automatiques |
| B. Plateforme managée (PaaS conteneur) + PostgreSQL géré | Sauvegardes, haute disponibilité, séparation | Coût, dépendance | **Recommandée dès la phase 5** (bots en production) |

- **Fichiers concernés** : `platform/Dockerfile`, `platform/compose.yml` (développement), `docs/platform/OPERATIONS.md` (à créer).
- **Changements cassants** : aucun.
- **Complexité** : M (A), M (B).
- **Sécurité** : base non exposée publiquement ; secrets par variables d'environnement ; sauvegardes chiffrées ; restauration testée.

### R-OPS-2 : Sous-domaines séparés
- **Pourquoi** : isoler la vitrine (publique, statique) et la plateforme (privée, avec sessions) pour des politiques de cookies et d'en-têtes distinctes.
- **Détail** : `www` / racine → vitrine (Netlify) ; `app` → plateforme ; le cookie de session n'est jamais posé sur le domaine de la vitrine.
- **Fichiers concernés** : configuration DNS (hors dépôt), `netlify.toml` (inchangé), `platform/app/config.py`.
- **Changements cassants** : aucun tant que le domaine n'est pas choisi. Les URL `netlify.app` actuelles restent valides.
- **Complexité** : S.
- **Sécurité** : limite la portée des cookies et des en-têtes.

---

## 9. Qualité et tests

### R-DEBT-3 : Outillage minimal et tests dès la phase 1
- **Pourquoi** : le projet n'a aucun test (D4). Il faut un filet de sécurité avant de toucher à la vitrine.
- **Détail** :
  - Vitrine : test de fumée Playwright (chargement FR/EN, bascule de langue, formulaire complet, menu mobile, absence de requêtes réseau externes, comportement sans JavaScript) ; validation HTML en CI.
  - Plateforme : pytest, ruff, mypy progressif, tests d'isolation et d'autorisation.
- **Fichiers concernés** : `.github/workflows/ci.yml`, `tests/site/*.spec.ts` ou `.py`, `platform/tests/*`.
- **Changements cassants** : aucun.
- **Complexité** : M.
- **Sécurité** : le test « aucune requête externe » protège la promesse de confidentialité.

### R-DEBT-2 : Consolider les tokens de thème
- **Pourquoi** : trois blocs de variables dupliqués (D3).
- **Détail** : un bloc de base et des surcharges ; vérifier le rendu identique par comparaison de captures d'écran (les deux thèmes, deux largeurs).
- **Fichiers concernés** : `public/styles.css` (lignes 2-4).
- **Changements cassants** : aucun si la comparaison visuelle est identique ; sinon, couleurs modifiées involontairement.
- **Complexité** : S.
- **Sécurité** : aucune.

### R-DEBT-4 : Épingler les actions GitHub
- **Pourquoi** : S6.
- **Fichiers concernés** : `.github/workflows/pages.yml`, futurs workflows.
- **Changements cassants** : aucun.
- **Complexité** : S.
- **Sécurité** : réduit le risque de chaîne d'approvisionnement.

### R-DEBT-5 : Nettoyage documentaire et technique
- **Pourquoi** : D5, D6, D7.
- **Détail** : corriger la mention de `favicon.svg` ; retirer ou confirmer `closingButton` et `modWord` ; ajouter `sitemap.xml` et sa référence dans `robots.txt` ; réécrire le README pour séparer ce qui est déployé de ce qui est en aperçu.
- **Fichiers concernés** : `README.md`, `public/robots.txt`, `public/sitemap.xml` (nouveau), `public/script.js` (clés).
- **Changements cassants** : suppression de clés inutilisées : aucun si vérifié par recherche ; ajout de `sitemap.xml` : aucun.
- **Complexité** : S.
- **Sécurité** : aucune.

---

## 10. Résumé des recommandations

| ID | Sujet | Complexité | Priorité |
|---|---|---|---|
| S1 (voir `CURRENT_STATE.md`) | Formulaire sans JavaScript transmet les réponses dans l'URL | S | **Immédiate** |
| R-SEC-2 | Cible de publication unique | S | Immédiate |
| R-DEBT-3 | Tests de fumée du site | M | Immédiate |
| R-ARCH-1 | Dossier plateforme séparé | S | Phase 2 |
| R-ARCH-2 | Stack Python / FastAPI / PostgreSQL | M | Phase 2 |
| R-SEC-A/B/C | Sessions, RBAC, en-têtes CSRF | L | Phase 2 |
| R-DATA-1/2 | Modèle et isolation multi-organisation | L | Phase 2 |
| R-SEC-4/5 | Secrets et journal d'audit | S | Phase 2 |
| R-I18N-1 | Source unique FR/EN | M | Phase 1 à 2 |
| R-DEBT-2/4/5 | Nettoyage | S | Phase 1 |
| R-BOT-1/2 | Agent sortant signé | M | Phase 5 |
| R-SEC-3 | Jetons Deriv hors base | M | Avant toute intégration réelle |
| R-BOT-3 | Écriture de configuration | L | Phase 6 |
| R-OPS-1/2 | Hébergement et sous-domaines | M | Phase 2 à 5 |

Décisions attendues du responsable : choix Netlify seul ou Pages (R-SEC-2) ; hébergement de la plateforme (R-OPS-1) ; nom de domaine (R-OPS-2) ; liste des pays cibles (conformité).
