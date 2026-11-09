> **Document remplacé (2026-11-09).** Cette version supposait une vitrine à préserver. L'orientation actuelle est décrite dans `NEW_PROJECT_DIRECTION.md`. Contenu conservé comme historique.

# SYSTEM-C — Plan de migration

Objectif : faire évoluer le projet vers SYSTEM-C Platform **sans casser la vitrine actuelle**, en gardant chaque étape réversible.

Principes :
1. **Aucune étape ne modifie `public/` sans test de non-régression préalable.** Le site vitrine est le produit visible ; il ne sert pas de terrain d'expérimentation.
2. **Ajouter avant de remplacer.** La plateforme vit à côté ; la vitrine ne dépend pas d'elle.
3. **Une étape = un changement vérifiable et une annulation simple** (un commit, ou une bascule de configuration).
4. **Expand, then contract** pour la base de données : ajouter, faire coexister, retirer plus tard.
5. **Pas de nouvelle promesse de confidentialité sans mise à jour du texte public** au même moment.

Chaque étape indique : **pourquoi**, **fichiers concernés**, **changements cassants**, **complexité**, **sécurité**. Les numéros renvoient à `IMPLEMENTATION_ROADMAP.md`.

---

## 1. Filet de sécurité avant toute modification

### M-0 — Figer le comportement actuel
- **Pourquoi** : sans référence, impossible de prouver qu'une modification n'a rien cassé. Le projet n'a aucun test.
- **Actions** :
  - capturer des captures d'écran de référence (FR et EN, thème clair et sombre, 390 px, 768 px, 1440 px) ;
  - inventorier les liens sortants, les ancres et les textes FR/EN (liste dans les tests) ;
  - tag Git `v9-baseline` sur le commit actuel.
- **Fichiers concernés** : aucun (les captures sont hors dépôt ou dans `tests/site/baseline/`).
- **Changements cassants** : aucun.
- **Complexité** : S.
- **Sécurité** : aucune donnée sensible dans les captures (site public).

### M-1 — Tests de fumée du site vitrine
- **Pourquoi** : garantir que chaque étape suivante laisse le site fonctionnel.
- **Détail** : Playwright (`--trace off` par défaut) sur `public/` servi localement. Vérifications :
  - chargement FR et EN, pas d'erreur console ;
  - bascule de langue met à jour `lang`, `title`, et les textes ;
  - menu mobile, Échap, focus ;
  - formulaire : erreurs si incomplet, résultat favorable et défavorable ;
  - **aucune requête réseau vers un domaine autre que la origine**, sauf les liens sortants (clic seulement) ;
  - **sans JavaScript, le formulaire ne transmet aucune réponse dans l'URL** (échouera tant que S1 n'est pas corrigé : ce test est donc le critère d'acceptation de M-2).
- **Fichiers concernés** : `tests/site/smoke.spec.ts` (nouveau), `playwright.config.ts` (nouveau), `package.json` (nouveau, **dev seulement**, dans `tests/site/`). Aucun fichier de `public/`.
- **Changements cassants** : aucun.
- **Complexité** : M.
- **Sécurité** : le test d'absence de requête externe est un garde-fou de confidentialité.

### M-2 — Corriger S1 (réponses dans l'URL sans JavaScript)
- **Pourquoi** : la page affirme que les réponses ne sont pas transmises à un serveur ; sans JavaScript, c'est faux.
- **Option retenue** : masquer le formulaire sans JavaScript et afficher un message `<noscript>` qui oriente vers le guide et le groupe, plutôt que de laisser le navigateur soumettre.
  - `styles.css` : `html:not(.js) .eligibility-form { display: none; }` et une règle pour le message.
  - `index.html` : `<noscript>` dans la section `#eligibility` (FR et EN, via texte statique bilingue).
  - Alternative écartée : `method="post"` vers une route inexistante (produirait une erreur serveur et une requête contenant les réponses, donc pire).
- **Fichiers concernés** : `public/styles.css`, `public/index.html`.
- **Changements cassants** : pour les utilisateurs sans JavaScript, le formulaire disparaît au profit d'un message. C'est un changement visible, mais il corrige une promesse fausse.
- **Complexité** : S.
- **Sécurité** : supprime une fuite de réponses vers les journaux de l'hébergeur.
- **Vérification** : `M-1` passe ; capture sans JS ; vérification que la classe `js` est bien posée au chargement normal (sinon le formulaire serait masqué à tort).

### M-3 — Choisir la cible de publication (R-SEC-2)
- **Pourquoi** : S2 et S3.
- **Actions** : confirmer si `pages.yml` est actif et si une URL GitHub Pages est utilisée publiquement. Si non : désactiver le workflow (déclenchement manuel conservé, ou suppression) après validation du responsable.
- **Fichiers concernés** : `.github/workflows/pages.yml`.
- **Changements cassants** : si une URL GitHub Pages est référencée publiquement, elle ne répondra plus. Vérifier avant.
- **Complexité** : S.
- **Sécurité** : une seule politique d'en-têtes.

---

## 2. Consolidation de la vitrine (sans changement visible)

### M-4 — Extraire les traductions vers des fichiers de données
- **Pourquoi** : D1 et D2 ; prérequis au partage FR/EN avec la plateforme (R-I18N-1).
- **Détail** :
  - créer `shared/i18n/fr.json` et `shared/i18n/en.json` à partir de `translations` (clés inchangées) ;
  - un script `scripts/build_i18n.py` génère `public/i18n.js` (fichier statique, sans dépendance) ; `script.js` le charge **avant** lui, ou `script.js` lit le fichier généré ;
  - le HTML conserve son texte FR par défaut (sans JavaScript, la page reste lisible).
- **Fichiers concernés** : `public/script.js` (lignes 1-33 retirées), `public/index.html` (ajout de `<script src="i18n.js">` avant `script.js`), `public/i18n.js` (généré), `shared/i18n/*.json`, `scripts/build_i18n.py`.
- **Changements cassants** :
  - ordre de chargement : `i18n.js` doit être chargé avant `script.js` ; test M-1 le vérifie ;
  - **la CSP** : `script-src 'self'` autorise `i18n.js` (même origine) ; aucun changement de politique nécessaire ;
  - **le fichier généré doit être commité** (Netlify ne lance pas de build) ; un test vérifie qu'il est à jour.
- **Complexité** : M.
- **Sécurité** : le HTML des traductions (`<em>`) reste statique et versionné.

### M-5 — Supprimer la duplication FR (HTML et traductions)
- **Pourquoi** : D1 ; la divergence est l'erreur la plus probable.
- **Détail** : test de cohérence qui compare le texte du HTML (`data-i18n`) et `fr.json`. Si identique, retirer le texte en double ou le garder comme repli, selon l'avis du responsable. **Ne pas supprimer le repli sans test de rendu sans JavaScript.**
- **Fichiers concernés** : `public/index.html` (`data-i18n` et texte), `scripts/check_i18n.py` (nouveau), `tests/site/`.
- **Changements cassants** : rendu sans JavaScript modifié si le texte est retiré. **Choisir de garder le repli par défaut.**
- **Complexité** : M.
- **Sécurité** : aucune.

### M-6 — Consolider les tokens de thème (R-DEBT-2)
- **Pourquoi** : D3.
- **Détail** : un seul bloc `:root` de base, les surcharges n'énumèrent que les variables qui changent ; comparaison visuelle avec les captures M-0 (tolérance nulle).
- **Fichiers concernés** : `public/styles.css` (lignes 2-4).
- **Changements cassants** : aucun si la comparaison est identique. En cas d'écart, corriger avant de valider.
- **Complexité** : S.
- **Sécurité** : aucune.

### M-7 — Nettoyage documentaire et de contenu (R-DEBT-5)
- **Actions** : corriger la mention `favicon.svg` dans le README ; séparer dans le README « déployé » et « aperçu » ; vérifier et retirer `closingButton` et `modWord` si inutilisés ; ajouter `sitemap.xml` et sa référence dans `robots.txt`.
- **Fichiers concernés** : `README.md`, `public/robots.txt`, `public/sitemap.xml` (nouveau), `shared/i18n/*.json`.
- **Changements cassants** : aucun.
- **Complexité** : S.
- **Sécurité** : aucune.

### M-8 — Mettre à jour le texte de confidentialité **avant** toute capture de données
- **Pourquoi** : la promesse « rien n'est stocké » sera fausse dès la phase Partners.
- **Détail** : ne pas modifier le texte tant qu'aucune capture n'existe ; le modifier au moment de la mise en service du formulaire de contact, dans la même version.
- **Fichiers concernés** : `shared/i18n/*.json`, `public/index.html` (`privacyNote`, `footerPrivacy`).
- **Changements cassants** : texte public modifié (intentionnel).
- **Complexité** : S.
- **Sécurité** : cohérence entre promesse et réalité ; exigence juridique (`GAP_ANALYSIS.md` §6).

---

## 3. Socle de la plateforme (aucun impact sur la vitrine)

### M-9 — Créer le squelette `platform/`
- **Pourquoi** : poser l'architecture sans toucher au site.
- **Détail** : FastAPI (`/healthz` seulement), configuration par variables d'environnement, Dockerfile, `compose.yml` avec PostgreSQL privé, Alembic initialisé, pytest et ruff en CI.
- **Fichiers concernés** : `platform/**` (nouveau), `.github/workflows/ci.yml` (nouveau), `.gitignore` (`.env`, `*.pem`, `*.key`, `platform/.venv`).
- **Changements cassants** : aucun.
- **Complexité** : M.
- **Sécurité** : `.env` ignoré ; `.env.example` sans valeurs ; image non-root ; `/healthz` ne révèle aucune version.

### M-10 — Base de données et migration initiale
- **Pourquoi** : démarrer le modèle de données (R-DATA-1) sans données réelles.
- **Détail** : migration `0001` (identité, organisations, rôles) et `0002` (audit, append-only).
- **Fichiers concernés** : `platform/migrations/versions/0001_*.py`, `0002_*.py`, `platform/app/models/*.py`.
- **Changements cassants** : aucun (base vide). Les migrations suivantes suivront le principe expand/contract.
- **Complexité** : M.
- **Sécurité** : utilisateur de base applicatif sans droits `UPDATE`/`DELETE` sur `audit_log`.

### M-11 — Authentification, sessions, RBAC
- **Détail** : voir R-SEC-A, R-SEC-B, R-SEC-C ; tests d'autorisation et d'isolation dès l'introduction.
- **Fichiers concernés** : `platform/app/auth/*`, `platform/app/middleware/*`, `platform/tests/test_auth.py`, `platform/tests/test_isolation.py`.
- **Changements cassants** : aucun.
- **Complexité** : L.
- **Sécurité** : critère de sortie de la phase 2 : aucun test d'isolation en échec, aucune route sans permission déclarée.

### M-12 — Lien entre la plateforme et la vitrine
- **Pourquoi** : la vitrine doit pouvoir renvoyer vers l'espace connecté sans partager de cookies.
- **Détail** : bouton « Espace membre » dans l'en-tête **uniquement** après mise en service de `app.` ; lien en dur vers le sous-domaine ; aucune requête de la vitrine vers la plateforme.
- **Fichiers concernés** : `public/index.html`, `shared/i18n/*.json`, `public/styles.css` (si besoin).
- **Changements cassants** : nouvel élément de navigation (intentionnel). Mettre à jour le test M-1 (liste des liens).
- **Complexité** : S.
- **Sécurité** : le test « aucune requête externe » doit autoriser ce seul domaine **en clic**, pas au chargement.

---

## 4. Modules (dans l'ordre de la feuille de route)

Chaque module suit le même cycle : modèle → migration → services avec autorisation → routes → templates FR/EN → tests (autorisation, isolation, parcours) → activation derrière un indicateur de configuration.

### M-13 — ACADEMY : contenu et inscription
- **Pourquoi** : premier module à valeur pour les étudiants ; le contenu Match/Differs existe déjà.
- **Détail** : import des 8 séquences depuis `index.html` (section `#module`) vers `course` / `lesson` par script ; le HTML public reste inchangé dans un premier temps.
- **Fichiers concernés** : `platform/app/models/academy.py`, `platform/app/services/academy.py`, `platform/app/routes/academy.py`, `platform/scripts/import_module_content.py`.
- **Changements cassants** : aucun pour la vitrine (contenu dupliqué volontairement pendant la transition).
- **Complexité** : L.
- **Sécurité** : contrôle d'accès sur chaque leçon ; pas de contenu réservé dans la vitrine publique.

### M-14 — ACADEMY : exercices, progression, évaluation
- **Détail** : correction déterministe ; notation indépendante du solde du compte démo (cohérent avec le texte public « Assessment »).
- **Changements cassants** : aucun.
- **Complexité** : L.
- **Sécurité** : réponses stockées avec horodatage ; pas de correction côté client.

### M-15 — PARTNERS : liens et prospects (après M-8)
- **Pourquoi** : remplace la constante en dur par un registre piloté.
- **Détail** : `referral_link` ; formulaire de contact séparé avec consentement daté ; statuts d'onboarding ; relances.
- **Fichiers concernés** : `platform/app/models/partners.py`, `platform/app/services/partners.py`, `platform/app/routes/partners.py`, `public/index.html` (lien de contact seulement).
- **Changements cassants** : **la vitrine ne doit pas changer de comportement** tant que la vitrine ne lit pas le registre. Le lien affilié reste en dur dans `index.html` jusqu'à M-16.
- **Complexité** : L.
- **Sécurité** : données personnelles : minimisation, consentement, durée de conservation, droit d'effacement (`GAP_ANALYSIS.md` §6).

### M-16 — Lien d'affiliation piloté par configuration (optionnel)
- **Détail** : la vitrine lit un fichier `public/config.json` généré depuis le registre ; ou le lien reste statique et est modifié par une revue. **Recommandation : rester statique tant que le volume de liens est faible.**
- **Fichiers concernés** : `public/index.html` (lignes 224, 226 si d'autres liens), `public/script.js`.
- **Changements cassants** : changement de lien = changement de contenu promotionnel ; revue obligatoire.
- **Complexité** : S (statique) / M (dynamique).
- **Sécurité** : le lien reste public par nature ; ne jamais y mettre de secret.

### M-17 — BOT MANAGEMENT : registre et supervision en lecture seule
- **Détail** : `bot_user`, `bot_environment`, `bot_type` ; agent sortant signé (R-BOT-1, R-BOT-2) ; heartbeats ; incidents.
- **Fichiers concernés** : `platform/app/models/bots.py`, `platform/app/api/agent.py`, `platform/agent/systemc_agent/*`, `platform/app/services/bots.py`.
- **Changements cassants** : aucun.
- **Complexité** : L.
- **Sécurité** : R-SEC-3 appliqué (aucun jeton stocké) ; signatures et anti-rejeu testés ; aucune commande d'écriture.

### M-18 — BOT MANAGEMENT : configuration versionnée (après gouvernance)
- **Détail** : `bot_config_version` immuable ; approbation à deux personnes pour `real` ; application par l'agent sur signature valide uniquement (R-BOT-3).
- **Changements cassants** : aucun.
- **Complexité** : L.
- **Sécurité** : interrupteur d'arrêt ; journal d'audit ; aucune exécution de code distant.

---

## 5. Stratégie de bascule et annulation

| Élément | Mécanisme | Annulation |
|---|---|---|
| Vitrine | Netlify, `publish = public` inchangé | Revenir au commit précédent (déploiement Netlify) |
| Plateforme | Sous-domaine `app.`, variable `FEATURE_*` par module | Désactiver le module ; la vitrine ne dépend pas de la plateforme |
| Base de données | Migrations Alembic réversibles pour les ajouts ; pas de suppression avant la phase 7 | `alembic downgrade -1` (ajouts) ; restauration de sauvegarde (cas graves) |
| Agent VPS | Version figée, arrêt par `systemctl stop` | Désactivation côté plateforme (révocation de l'agent) |
| Traductions | Fichier généré versionné | Revert du commit de génération |

---

## 6. Registre des changements cassants potentiels

| # | Changement | Étape | Qui est affecté | Atténuation |
|---|---|---|---|---|
| B1 | Formulaire masqué sans JavaScript | M-2 | Visiteurs sans JS | Message `<noscript>` explicite ; décision documentée |
| B2 | Ordre de chargement des scripts | M-4 | Tous les visiteurs | Test de fumée ; `i18n.js` avant `script.js` |
| B3 | URL GitHub Pages inactive | M-3 | Quiconque suit cette URL | Vérifier les liens avant désactivation |
| B4 | Texte de confidentialité modifié | M-8 | Lecteurs | Intentionnel, versionné |
| B5 | Nouveau lien de navigation | M-12 | Visiteurs | Test M-1 mis à jour |
| B6 | Fichier généré à maintenir | M-4 | Contributeurs | Test « fichier à jour » en CI |
| B7 | Contenu Match/Differs dupliqué (HTML et base) | M-13 | Équipe éditoriale | Source de vérité désignée par module |

---

## 7. Critères de sortie par étape

- Tous les tests de fumée passent (FR, EN, mobile, sans JS).
- Comparaison visuelle avec `v9-baseline` : identique, sauf changements approuvés.
- Aucune nouvelle requête réseau au chargement de la vitrine.
- CSP inchangée, sauf décision documentée.
- Revue de code par une personne autre que l'auteur pour toute modification de `public/` ou de l'authentification.
- Documentation (`README.md`, `docs/platform/`) à jour.

---

## 8. Décisions à obtenir avant de commencer

1. Feu vert pour M-2 (correction de S1) : c'est la correction la plus urgente, et elle est indépendante du reste.
2. Netlify seul ou Netlify plus GitHub Pages (M-3).
3. Emplacement de la plateforme : VPS existant ou hébergement séparé (R-OPS-1).
4. Ordre des modules : ACADEMY d'abord (recommandé) ou PARTNERS.
5. Calendrier de M-15 (prospects) au regard des points de conformité.
