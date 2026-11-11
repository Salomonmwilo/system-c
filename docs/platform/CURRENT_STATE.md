# SYSTEM-C : état actuel du dépôt (Phase 0, audit)

Date de l'audit : 2026-11-09 · Branche : `claude/zealous-fermi-lxtqkl` (identique à `main`, 3 commits) · Auteur unique des commits.

Ce document décrit ce qui existe réellement dans le dépôt, sans proposer de changement. Les observations sont vérifiées par lecture du code et, lorsque indiqué, par un test dans un navigateur réel.

---

## 1. Vue d'ensemble

SYSTEM-C est aujourd'hui un **site vitrine statique, bilingue FR/EN, mono-page**, destiné à être publié sur Netlify. Il n'existe :

- aucun backend, aucune API, aucune route serveur ;
- aucune base de données, aucun modèle de données ;
- aucune authentification, aucun compte utilisateur ;
- aucun `package.json`, aucun outil de build, aucun gestionnaire de dépendances ;
- aucun test automatisé, aucun linter, aucun formatteur, aucune validation HTML dans la CI ;
- aucune variable d'environnement, aucun secret (scan effectué : seules des occurrences de texte éditorial apparaissent).

Le « produit » est donc entièrement client-side : HTML + CSS + un fichier JavaScript.

| Indicateur | Valeur |
|---|---|
| Fichiers suivis | 38 |
| Code applicatif | `public/index.html` (285 lignes, 48,6 Ko), `public/styles.css` (258 lignes, 31 Ko), `public/script.js` (278 lignes, 46 Ko) |
| Images | 24 fichiers dans `public/images/` (hero, 4 jeux de photos du fondateur, 6 illustrations de module) |
| Pages | `index.html` (page unique à ancres) + `404.html` |
| Langues | FR (par défaut) et EN, 219 clés de traduction chacune, parité vérifiée |

---

## 2. Arborescence

```
system-c/
├── README.md                       Documentation (français), journal des versions 3 à 9
├── netlify.toml                    publish = "public", en-têtes de sécurité, CSP
├── .gitignore                      .netlify, .DS_Store
├── .github/workflows/pages.yml     Déploiement GitHub Pages (dossier public) sur push vers main
└── public/                         Seul dossier publié
    ├── index.html                  Structure et contenu (texte FR par défaut, data-i18n)
    ├── 404.html                    Page 404 bilingue
    ├── styles.css                  Design noir et or, tokens CSS, responsive, accessibilité
    ├── script.js                   Traductions (lignes 1-33), formulaire, thème, menu, animations
    ├── robots.txt                  Allow: / (sans lien vers un sitemap)
    ├── images/                     Photos (hero, fondateur), illustrations (module)
    └── favicon-32.png, favicon-192.png, apple-touch-icon.png, logo-mark.png, og-image.png
```

Le README mentionne un `favicon.svg` qui **n'existe pas** dans le dépôt (les favicons sont en PNG).

---

## 3. Stack technique

| Couche | Technologie | Remarques |
|---|---|---|
| Structure | HTML5 unique (`index.html`) | Sections identifiées par des ancres : `#home`, `#about`, `#benefits`, `#founder`, `#program`, `#module`, `#eligibility`, `#guide`, `#faq`, `#risk`, `#join` |
| Style | CSS natif, aucun préprocesseur | Variables CSS sur `:root`, thème sombre par défaut, thème clair via `prefers-color-scheme` et attribut `data-theme` |
| Logique | JavaScript vanilla (ES2017+), aucun framework | Un seul fichier, aucun module ES, aucun bundler |
| Polices | Système uniquement | Georgia pour les titres ; Google Fonts retiré pour la confidentialité (v4) |
| Hébergement | Netlify (publication de `public/`, sans commande de build) | Également GitHub Pages via `pages.yml` |
| Dépendances tierces | Aucune au chargement | Liens sortants uniquement (Deriv, WhatsApp) |

---

## 4. Frontend : architecture

### 4.1 Internationalisation
- Un objet littéral `translations = { fr: {...}, en: {...} }` dans `script.js` (lignes 1-33). Les lignes sont très longues (jusqu'à 7,5 Ko), ce qui rend la relecture et le diff difficiles.
- Dans `index.html`, 123 éléments portent `data-i18n`, `data-i18n-alt`, `data-i18n-aria` ou `data-href-*` / `data-src-*`. Le texte français est **dupliqué** : il est écrit en dur dans le HTML **et** dans `translations.fr`. Deux sources de vérité.
- Langue initiale : `navigator.language` (commence par `en` → anglais). Aucune persistance (`localStorage` retiré en v4, voir section 8).
- Bascule via `#langToggle` (`setLanguage()`), qui met à jour le texte, `lang`, `title`, meta description, `alt`, `aria-label`, liens et `src` des images.
- Parité FR/EN vérifiée : 219 clés dans chaque langue, aucune clé manquante pour les `data-i18n` utilisés.
- Clés définies mais apparemment inutilisées : `closingButton`, `modWord` (à confirmer avant suppression).
- Le contenu traduit est injecté avec `innerHTML` (balises `<em>`, `<span>`). Sûr aujourd'hui car le contenu est statique et versionné.

### 4.2 Thème
- Tokens sur `:root` (`--bg`, `--gold`, `--text`, `--line`, etc.), redéfinis trois fois : thème sombre par défaut, `[data-theme="light"]`, et `prefers-color-scheme: light`. Ces trois blocs dupliquent ~30 variables chacun.
- Bouton `.theme-toggle` (`applyTheme()`), choix non mémorisé.
- `meta name="theme-color"` mis à jour selon le thème.

### 4.3 Navigation et accessibilité
- En-tête fixe, menu mobile avec `aria-expanded`, fermeture par Échap et clic extérieur, focus rendu au bouton.
- Lien d'évitement « Aller au contenu » (focus réel sur `<main tabindex="-1">`).
- Barre de progression de lecture et apparition progressive (`IntersectionObserver`), désactivées si `prefers-reduced-motion`.
- Rubrique active marquée par `aria-current` (IntersectionObserver).
- Liens `target="_blank"` annoncés aux lecteurs d'écran (`decorateExternalLinks()`).
- Tous les `<img>` ont un attribut `alt` (0 exception relevée).
- Aucun identifiant `id` dupliqué.

### 4.4 Module « Eligibility » (pré-évaluation)
- Formulaire `#eligibilityForm` à 6 questions à choix radio (`age`, `country`, `identity`, `device`, `capital`, `risk`).
- Validation maison (`showErrors()`), résumé d'erreurs `role="alert"`, focus géré.
- `buildResult()` produit trois issues : `stop` (ne pas poursuivre), `check` (à vérifier), `ok` (favorable). Le cas favorable affiche un bouton vers le groupe WhatsApp (`WHATSAPP_URL`, constante en dur).
- Tout le calcul se fait dans le navigateur. **Voir la section 8 : le formulaire sans JavaScript transmet les réponses dans l'URL.**

### 4.5 Sections de contenu
- Hero avec photo, pastilles, boutons d'action.
- « Pourquoi System-C » (`#about`), « Ce que tu apprendras » (6 compétences, `#benefits`).
- « Le fondateur » (3 photos fournies, formats WebP avec repli JPEG, `#founder`).
- « Cohorte Alpha » (`#program`), « Match/Differs : huit séquences » (`#module`, illustrations FR/EN, versets, avertissement).
- Pré-évaluation (`#eligibility`), « Guide Deriv » en 5 étapes (`#guide`), FAQ en accordéons (`#faq`).
- « Risques & transparence » (`#risk`) : avertissement officiel de Deriv en anglais, traduction française (`lang="fr"` / `lang="en"`).
- Appel à l'action final (`#join`), pied de page avec mention de confidentialité.

### 4.6 Liens externes en dur
| Ressource | Emplacement | Nature |
|---|---|---|
| `https://t.deriv.link?t=L9CTBT5XUH3M` | `index.html` ligne 224 | Lien d'affiliation Deriv |
| `https://chat.whatsapp.com/…` | `script.js` ligne 85 ; `index.html` lignes 235, 267 | Groupe WhatsApp |
| `https://deriv.com/terms-and-conditions/affiliates` | `index.html` ligne 257 | Conditions d'affiliation |
| `deriv.com/help-centre*` (FR et EN) | `index.html` lignes 226, 240, 278 | Aide Deriv |
| `https://system-c.netlify.app/…` | `index.html` lignes 14, 15, 23 | URL canonique et `og:image` |

---

## 5. Backend, base de données, authentification

**Aucun.** Il n'existe ni serveur, ni langage serveur, ni schéma, ni migration, ni session, ni mot de passe, ni jeton, ni rôle. Le seul « serveur » est l'hébergeur statique (Netlify ou GitHub Pages). Les réponses au questionnaire ne quittent jamais le navigateur (vérifié, sauf cas sans JavaScript).

---

## 6. Routes et points d'entrée

| Route | Source | Rôle |
|---|---|---|
| `/` | `public/index.html` | Page unique |
| `/index.html#<section>` | ancres | Navigation interne |
| `/404.html` | `public/404.html` | Page d'erreur (`noindex`), chemins absolus (`/styles.css`) |
| `/robots.txt` | `public/robots.txt` | Autorise tout, sans sitemap |
| `/images/*`, `/*.png` | fichiers statiques | Cache 24 h (`/*.png` uniquement) |

Aucune API. Aucune route dynamique.

---

## 7. Configuration et déploiement

### 7.1 Netlify (`netlify.toml`)
- `publish = "public"`, pas de commande de build.
- En-têtes sur `/*` : `X-Content-Type-Options`, `X-Frame-Options: DENY`, `Referrer-Policy`, `Permissions-Policy` (caméra, micro, géolocalisation, paiement, cohortes désactivés), `Strict-Transport-Security` (1 an, includeSubDomains), et une **CSP stricte** :
  `default-src 'self'; script-src 'self'; style-src 'self'; font-src 'self'; img-src 'self' data:; connect-src 'none'; base-uri 'self'; form-action 'none'; frame-ancestors 'none'; object-src 'none'`
- En-tête `Cache-Control` sur `/*.png`.

### 7.2 GitHub Pages (`.github/workflows/pages.yml`)
- Se déclenche sur push vers `main` et sur `workflow_dispatch`.
- Publie le dossier `public` via `actions/upload-pages-artifact@v3` et `actions/deploy-pages@v4`. Actions référencées par tag majeur, non épinglées par SHA.
- **GitHub Pages n'applique pas `netlify.toml`** : la CSP, HSTS et `frame-ancestors` ne s'appliquent pas à cette version.

### 7.3 Variables d'environnement et secrets
Aucune. Aucun fichier `.env`. Aucun secret dans l'historique Git (recherche sur tout l'historique : aucun motif de type clé ou jeton).

### 7.4 Identifiant d'affiliation
Le code d'affiliation Deriv est public par nature (il figure dans le HTML servi). Il n'est pas un secret, mais il est codé en dur et doit devenir une donnée de configuration dans la future plateforme.

---

## 8. Tests, qualité, sécurité

### 8.1 Tests et qualité
- **Aucun test automatisé**, aucun linter, aucune vérification HTML/CSS/JS en CI.
- Vérifications manuelles effectuées pour cet audit (scripts jetables hors dépôt, non commités) :
  - parité des clés FR/EN et couverture des `data-i18n` : OK ;
  - identifiants dupliqués : aucun ;
  - images sans `alt` : aucune ;
  - formulaire en navigateur **sans JavaScript** : voir ci-dessous.

### 8.2 Constats de sécurité et de confidentialité

| # | Constat | Gravité | Preuve |
|---|---|---|---|
| S1 | **Le formulaire d'éligibilité, sans JavaScript, envoie les réponses dans l'URL.** Le `<form>` n'a ni `method` ni `action`. Sans JS, la soumission est une requête `GET` qui ajoute `?age=yes&country=yes&…` à l'URL. Cela contredit le texte affiché (« ne transmet ni ne stocke tes réponses sur un serveur ») : les réponses sont transmises à l'hébergeur et peuvent figurer dans ses journaux d'accès. | Moyenne (confidentialité, promesse non tenue) | Test Chromium avec JavaScript désactivé : URL finale `index.html?age=yes&country=yes&identity=yes&device=yes&capital=demo&risk=yes` |
| S2 | **GitHub Pages sans en-têtes de sécurité.** Si le workflow `pages.yml` publie réellement le site, celui-ci est servi sans CSP ni HSTS. La politique de sécurité dépend donc de l'hébergeur. | Moyenne (à confirmer par l'état réel de Pages) | Lecture de `netlify.toml` et `pages.yml` |
| S3 | **Deux cibles de publication** (Netlify depuis Git, GitHub Pages depuis `main`) avec une URL canonique fixe sur `netlify.app`. Risque de contenu dupliqué et de source de vérité ambiguë. | Faible | `index.html` lignes 14, 15, 23 ; `pages.yml` |
| S4 | `innerHTML` appliqué aux traductions. Aujourd'hui sûr (contenu statique), mais le pattern deviendrait dangereux si le contenu venait d'une base de données ou d'un éditeur. | Faible (actuel) / élevée si réutilisé tel quel | `script.js` ligne 147 |
| S5 | Pas de `<noscript>` : aucun message pour les utilisateurs sans JavaScript (le menu, le thème et le formulaire ne fonctionnent pas). | Faible | `index.html` : 0 occurrence |
| S6 | Actions GitHub non épinglées par SHA ; permission `id-token: write` accordée au workflow. | Faible | `pages.yml` |
| S7 | Aucune politique de cache pour les pages HTML/CSS/JS (valeurs par défaut de Netlify). | Très faible | `netlify.toml` |
| S8 | Contenu sensible : avertissement de risque, promesses, affiliation, contenu financier destiné à de jeunes publics (« Cohorte Alpha », « Match/Differs »). Points de conformité à faire valider (voir `GAP_ANALYSIS.md` section 6). | Élevée (réglementaire, hors code) | README « Avant publication » ; `index.html` |

Points **positifs** à préserver :
- CSP stricte sans `unsafe-inline` ; aucun script ni style inline dans le HTML ; aucun appel réseau au chargement (`connect-src 'none'`).
- Aucun cookie, aucun stockage local, aucun outil d'analyse.
- Les 8 liens `target="_blank"` portent `noopener noreferrer` ; le lien d'affiliation ajoute `sponsored`, ce qui est correct.
- Accessibilité très soignée (focus, ARIA, cibles tactiles, mouvement réduit, contraste du mode clair corrigé).

### 8.3 Dette technique

| # | Dette | Impact |
|---|---|---|
| D1 | Traductions FR dupliquées entre HTML et `script.js` | Risque de divergence ; coût de chaque modification de texte ×2 |
| D2 | `script.js` de 46 Ko mélangeant données, logique et UI, lignes de 7 Ko | Relecture et diff impraticables ; pas de réutilisation possible |
| D3 | Trois blocs de tokens de thème dupliqués dans `styles.css` | Oubli probable d'une variable lors d'un changement de couleur |
| D4 | Pas de gestionnaire de paquets ni de build | Impossible d'ajouter proprement des outils de test ou de lint sans les introduire |
| D5 | README en retard sur le code : mentionne `favicon.svg` (absent), un « rapport d'audit » non présent dans le dépôt, et des versions « non déployées » mêlées à l'historique | Confusion pour toute personne qui reprend le projet |
| D6 | `closingButton` et `modWord` probablement inutilisés | Bruit mineur |
| D7 | Pas de `sitemap.xml` ; `robots.txt` sans référence | SEO légèrement réduit |
| D8 | Historique Git court (3 commits), pas de convention de messages de commit documentée | Pas de repère pour les contributions futures |

---

## 9. Ce qui fonctionne bien et doit être préservé

- Identité visuelle (noir et or, logo, favicons, image de partage) et ton éditorial prudent (« aucun gain garanti », « pas de promesses »).
- Engagement de confidentialité par conception : aucun service tiers au chargement, aucune donnée stockée côté client.
- Système de tokens CSS (`--gold`, `--bg`, etc.) : base directe pour un futur design system de la plateforme.
- Responsive : points de rupture à 950, 700, 420 et 380 px ; cibles tactiles de 44 px pour le questionnaire.
- Contenu pédagogique déjà rédigé : huit séquences Match/Differs (FR/EN), six compétences, guide en cinq étapes, FAQ.
- Parité bilingue FR/EN déjà réalisée.

---

## 10. Résumé

SYSTEM-C est un **site vitrine statique, soigné et bilingue**, sans backend. Sa qualité d'implémentation (accessibilité, CSP, confidentialité) est nettement supérieure à sa couverture technique (aucun test, aucun build, aucune donnée structurée). La principale faiblesse technique à traiter avant toute évolution est la **dualité des traductions** (HTML et JavaScript) ; le principal constat de confidentialité est **S1**, à corriger quel que soit le calendrier de la plateforme.
