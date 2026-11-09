# SYSTEM-C Platform — Nouvelle orientation et architecture cible

Statut : **révision 2 — proposition à approuver**. Aucun code n'est écrit à ce stade. Aucun fichier existant n'est supprimé ni modifié.

Historique :
- Révision 1 (2026-11-09) : plateforme SaaS à trois modules.
- **Révision 2 (2026-11-09) : BOT MANAGEMENT redéfini comme CRM administratif.** Le module ne contrôle plus les robots. Il n'y a ni agent sur le VPS, ni API de contrôle, ni commande distante, ni synchronisation de trades, ni stockage de tokens. Les sections touchées sont signalées par **[rév. 2]**.
- **Révision 3 (2026-11-09) : décisions de conception validées** (propriété des affiliés, comptes de robots, liste blanche, mode réel, alertes, sécurité). Détail dans `BOT_CRM_SPEC.md`, qui fait foi pour le CRM. Les sections modifiées sont marquées **[rév. 3]**.

Documents remplacés : `PROPOSED_ARCHITECTURE.md`, `MIGRATION_PLAN.md`, `IMPLEMENTATION_ROADMAP.md` (voir §10). `CURRENT_STATE.md` et `GAP_ANALYSIS.md` restent valables comme inventaire.

---

## 1. Nouvelle vision du produit

**SYSTEM-C Platform** est une plateforme SaaS multi-utilisateurs et multi-organisations, en français et en anglais, composée de trois modules fonctionnellement indépendants qui partagent l'identité, les profils, les permissions et les services communs.

| Module | Mission | Nature |
|---|---|---|
| **ACADEMY** | Formation autonome : programmes, cours, leçons, exercices, évaluations, progression | Pédagogique |
| **PARTNERS** | Personnes orientées par les liens de parrainage, prospects, liens d'affiliation, suivi d'inscription et de vérification, relances | Commerciale et administrative |
| **BOT MANAGEMENT** **[rév. 2]** | **CRM administratif** des affiliés et des utilisateurs de robots : type de robot attribué, capital de référence, réglages déclarés, historique des configurations, interventions, tâches et rappels | Administrative, **sans contrôle technique** |

### 1.1 Rôle de BOT MANAGEMENT **[rév. 2]**

BOT MANAGEMENT ne commande, ne surveille et ne lit aucun robot. Il sert à l'administrateur pour :

1. Enregistrer et gérer les affiliés Deriv et leur parcours d'inscription et de vérification.
2. Enregistrer si un affilié souhaite utiliser un robot.
3. Lui attribuer un type de robot : **DIFFERS** ou **OVER/UNDER**.
4. Enregistrer le capital de référence et les réglages qui lui sont attribués.
5. Conserver l'historique des configurations **déclarées comme appliquées**.
6. Enregistrer les dates des interventions et les notes de suivi.
7. Gérer les tâches, rappels et actions en attente.
8. Visualiser rapidement l'état de chaque affilié et de chaque utilisateur de robot.

### 1.2 Responsabilités du VPS **[rév. 2]**

Le VPS Ubuntu existant reste **entièrement indépendant** de la plateforme. L'administrateur continue, avec ses scripts et commandes existants :

- créer les utilisateurs des robots ;
- configurer les fichiers `reglages.env` ;
- gérer les tokens Deriv ;
- démarrer et arrêter les services systemd ;
- modifier les paramètres techniques ;
- consulter les journaux et rapports ;
- gérer les opérations de trading.

**La plateforme ne lit, n'écrit et ne vérifie rien sur le VPS.**

### 1.3 Règle de fonctionnement **[rév. 2]**

Quand une configuration est appliquée sur le VPS, l'administrateur **met à jour la fiche correspondante** dans la plateforme. La plateforme conserve donc un **registre administratif** de ce qui a été déclaré comme appliqué. Elle ne prétend jamais connaître l'état réel du VPS : chaque statut affiché porte la mention « déclaré par l'administrateur, non vérifié », et la date de la dernière déclaration.

Principes directeurs :
1. **Sécurité par défaut** : refus par défaut, moindre privilège, aucune donnée sensible inutile.
2. **Transparence** : aucune promesse de gain, avertissements de risque visibles, distinction claire entre ce qui est déclaré et ce qui est vérifié.
3. **Bilingue dès le départ** : toute interface et tout contenu éditable existent en FR et EN.
4. **Multi-organisation dès le départ** : chaque donnée appartient à une organisation.
5. **Modularité sans microservices** : des modules séparés dans un même déploiement.
6. **Ne pas en faire plus que nécessaire** : pas de fonctionnalité technique tant qu'un besoin administratif ne l'exige pas.

---

## 2. Éléments de l'ancien dépôt à réutiliser

Réutiliser signifie : récupérer la **donnée ou la décision** (texte validé, identité visuelle, règle métier), pas le code qui la présente.

### 2.1 Identité et branding

| Élément | Source | Usage | Décision |
|---|---|---|---|
| Nom et slogan | `index.html` (en-tête, pied), `script.js` (`heroTitle`, `metaTitle`) | Nom du produit, « Penser juste. Agir avec discipline. » | Réutiliser (à confirmer pour la plateforme) |
| Devise latine validée | `script.js` (`footerSlogan`) : « Solus cum plenitudine, inopi est alia » | Pied de page des pages publiques | Réutiliser (validée par le responsable) |
| Logo | `public/logo-mark.png` (source 480×279) | En-tête, favicon, icône | Réutiliser ; demander une version vectorielle avant les documents imprimés |
| Favicons | `favicon-32.png`, `favicon-192.png`, `apple-touch-icon.png` | Plateforme | Réutiliser |
| Palette noir et or | `styles.css` : `--bg #09090a`, `--gold #d7b46a`, `--gold2 #f0d79b`, `--text #f5f1e8` et variantes claires | Tokens de design | Réutiliser les **valeurs** |
| Typographie | Georgia (titres), police système (texte) | Idem | Réutiliser, à valider pour les tableaux de bord |
| Image de partage | `public/og-image.png` | Pages publiques | Réutiliser |

### 2.2 Textes institutionnels et mission

| Élément | Source | Décision |
|---|---|---|
| Principes « pas de promesses » | `script.js` (`trans1Title` à `trans4Title`) | **Réutiliser tels quels** |
| Mention d'indépendance | `footerDisclaimer` | Adapter : « Plateforme éducative et administrative indépendante. Deriv est une marque distincte. » |
| Avertissement de risque officiel | `index.html` (texte anglais, Deriv Affiliates Terms, section 1.10) | **Réutiliser verbatim** en anglais ; traduction française séparée, marquée « non officielle ; la version anglaise fait foi » |
| Politique de confidentialité | — | **À réécrire** : la plateforme collecte des données de prospects, d'affiliés et d'utilisateurs de robots |

### 2.3 Traductions FR et EN

- Environ 219 clés par langue existent dans `script.js`, en parité vérifiée. **Réutilisation sélective** : seuls les textes institutionnels, pédagogiques et d'avertissement sont repris. Les clés du site vitrine (menu, thème, animations) ne le sont pas.
- Les traductions sortent du JavaScript et entrent dans les catalogues du framework, avec contrôle de parité en CI.

### 2.4 Contenus pédagogiques

| Élément | Source | Réutilisation |
|---|---|---|
| Huit séquences Match/Differs (titres, objectifs, exercices, FR et EN) | `script.js` (`seq1Title`… `seq8Ex`) | **Premier contenu d'ACADEMY**, après relecture pédagogique |
| Six compétences | `b1Title`… `b6Desc` | Objectifs de programme |
| Définitions « trading » et « Deriv » | `defTradingDesc`, `defDerivDesc` | À valider |
| Versets (Louis Segond, King James) | `verse1`… `verse8` | Vérifier les droits de la traduction Louis Segond avant publication ; la King James est dans le domaine public |
| Illustrations (parcours, digits, proba) | `public/images/module-*` | Réutilisables |
| FAQ et guide Deriv en cinq étapes | `script.js` (`step*`, `faq*`) | **À réviser** : contenu daté, dépend de l'interface Deriv |

### 2.5 Logique métier réutilisable comme données

Les règles de pré-évaluation (âge minimum, pays autorisé, document accepté, fonds non essentiels, compréhension du risque) sont reprises **comme référentiel versionné**, pas comme code. Elles servent à ACADEMY (admissibilité) et à PARTNERS (onboarding). Le code JavaScript qui les évaluait n'est pas réutilisé.

### 2.6 Documentation

- Les documents de `docs/platform/` sont conservés comme historique de l'audit.
- `CURRENT_STATE.md` reste la référence de l'inventaire.

### 2.7 Idées de conception réutilisables

- Tokens CSS (variables, deux thèmes).
- Accessibilité : focus géré après une erreur, `aria-describedby` par champ, cibles de 44 px, mention « s'ouvre dans un nouvel onglet », respect de `prefers-reduced-motion`.
- Politique d'en-têtes de sécurité de l'ancien `netlify.toml` (CSP stricte, `frame-ancestors 'none'`, `Referrer-Policy`, `Permissions-Policy`), à réappliquer à l'application.

---

## 3. Éléments à abandonner ou ignorer

| Élément | Raison | Action |
|---|---|---|
| Site vitrine comme produit à maintenir | Hors objectif | Ignorer ; ne pas modifier |
| `netlify.toml`, `.github/workflows/pages.yml` | Hors objectif | Ignorer ; conserver les fichiers |
| `public/script.js` et `public/styles.css` comme base applicative | Non modulaires ; conçus pour une page | Ne pas réutiliser le code ; extraire seulement les données et tokens |
| Formulaire d'éligibilité en HTML | Logique client, réponses non enregistrées | Remplacer par un parcours serveur auditable |
| Lien d'affiliation codé en dur | Doit devenir une donnée gérée | Migrer vers le registre de liens |
| Canal WhatsApp comme canal d'inscription | Canal non contrôlé pour des données personnelles | **À décider** (§11) |
| Affirmation « carte d'électeur RDC acceptée » | Témoignages non vérifiés | **Ne pas réutiliser comme fait** |
| Promesse « rien n'est stocké » | Fausse pour la plateforme | Réécrire |
| **Agent Python sur le VPS** **[rév. 2]** | Hors périmètre | **Retiré** |
| **API de contrôle des robots, commandes distantes** **[rév. 2]** | Hors périmètre | **Retiré** |
| **Synchronisation automatique des trades et des soldes** **[rév. 2]** | Hors périmètre ; données financières inutiles | **Retiré** |
| **Stockage des tokens Deriv, même haché** **[rév. 2]** | Hors périmètre ; risque inutile | **Retiré** (§7.4) |
| Documents `PROPOSED_ARCHITECTURE.md`, `MIGRATION_PLAN.md`, `IMPLEMENTATION_ROADMAP.md` | Orientés vitrine ou agent | Marqués « remplacés » (§10) |

---

## 4. Architecture cible recommandée

### 4.1 Choix structurant : un monolithe modulaire

Une seule application backend découpée en modules à frontières strictes, avec une base PostgreSQL partagée. **Aucun composant ne tourne sur le VPS.** Le VPS est un système séparé que l'administrateur utilise seul.

Pourquoi pas des microservices : trois modules, équipe réduite, besoins transactionnels communs. Pourquoi pas une SPA : le rendu serveur simplifie la sécurité des sessions et réduit le code client.

### 4.2 Schéma **[rév. 2]**

```
   Administrateur, opérateurs, partenaires, apprenants (FR/EN)
        │  HTTPS, cookies de session HttpOnly
        ▼
┌───────────────────────────────────────────────────────────────┐
│  SYSTEM-C Platform (une application)                          │
│                                                               │
│  ┌──────────────── core (partagé) ─────────────────────────┐  │
│  │ identité · profils · organisations · rôles · permissions │  │
│  │ audit · consentements · tâches · notifications · i18n   │  │
│  └───────▲──────────────────▲──────────────────▲───────────┘  │
│  ┌───────┴───────┐  ┌───────┴────────┐  ┌──────┴────────────┐  │
│  │   academy     │  │   partners     │  │   bots (CRM)      │  │
│  │ programmes    │  │ liens          │  │ utilisateurs bots │  │
│  │ leçons        │  │ prospects      │  │ type, capital     │  │
│  │ exercices     │  │ affiliés*      │  │ réglages déclarés │  │
│  │ progression   │  │ onboarding     │  │ historique        │  │
│  │               │  │ relances       │  │ interventions     │  │
│  └───────────────┘  └────────────────┘  └───────────────────┘  │
└───────────────────────────────────────────────────────────────┘
                              │
                              ▼
                     ┌─────────────────┐       ┌────────────────────────────┐
                     │ PostgreSQL      │       │ Stockage objet (exports,   │
                     │ (réseau privé)  │       │ pièces non sensibles)      │
                     └─────────────────┘       └────────────────────────────┘

   ┊ Aucune connexion automatique ┊
   ┊                             ┊
   VPS Ubuntu (indépendant)  ◄── l'administrateur applique les configurations
   bots Python, reglages.env,      et MET À JOUR LA FICHE à la main dans la
   tokens, systemd, journaux       plateforme (registre déclaratif)

   * « affiliés » : entité possédée par partners ou bots — voir §4.3
```

### 4.3 Propriété de la fiche affilié **[rév. 2]** — décision à prendre

La demande initiale donne aux deux modules PARTNERS et BOT MANAGEMENT la gestion des affiliés et de leur parcours d'inscription et de vérification. Il faut éviter deux fiches pour une même personne.

**Décidé [rév. 3]** : `partners` est propriétaire de la fiche principale. Une seule fiche par personne. `academy` et `bots` la **référencent** par identifiant et ne copient aucune donnée personnelle. Voir `BOT_CRM_SPEC.md` §1.

Option écartée [rév. 3] : `bots` propriétaire de l'affilié.

Dans les deux cas, un **prospect** (PARTNERS, avant inscription) devient un **affilié** à la conversion. Un seul événement de domaine porte cette transition.

### 4.4 Règle de séparation des modules

- Chaque module a ses propres modèles, services, routes, gabarits et tests.
- Un module n'importe jamais les modèles d'un autre : il passe par ses fonctions publiques ou par un événement.
- Vérification automatique en CI (règles d'import).
- Liens entre modules par identifiants.
- Chaque module peut être désactivé par organisation.

### 4.5 Organisation et multi-tenancy

- **Organisation** = frontière de données. Le premier tenant est SYSTEM-C.
- Toute table métier porte `organization_id`. Aucune requête métier sans contexte d'organisation résolu côté serveur.
- Une personne peut appartenir à plusieurs organisations avec des rôles différents.
- Les **administrateurs de plateforme** ont un rôle global, journalisé, avec double authentification.
- Isolation renforcée en phase 6 par les politiques de ligne PostgreSQL.

### 4.6 Identité, profils et permissions

- `person` : identité (nom affiché, langue, fuseau horaire, pays de résidence déclaré).
- `user` : compte de connexion, lié à une `person`. **Les utilisateurs de robots n'ont pas de compte de connexion par défaut** (§11).
- `membership` : appartenance à une organisation avec des rôles.
- Politique d'autorisation centralisée, refus par défaut, test qui échoue si une route n'a pas de permission déclarée.

Rôles proposés :

| Rôle | Portée | Accès |
|---|---|---|
| `platform_admin` | Globale | Tout ; journalisé ; TOTP obligatoire |
| `org_admin` | Organisation | Membres, paramètres, exports |
| `crm_admin` **[rév. 2]** | Organisation | CRM complet : affiliés, utilisateurs de robots, configurations, historique |
| `crm_operator` **[rév. 2]** | Organisation | Saisie des interventions, notes, tâches ; mise à jour des statuts |
| `crm_viewer` **[rév. 2]** | Organisation | Lecture ; données personnelles masquées par défaut |
| `partner_manager` / `partner_advisor` | Organisation / prospects assignés | Liens, prospects, relances |
| `academy_instructor` / `academy_student` | Organisation / soi-même | Contenus, parcours |

---

## 5. Technologies recommandées

### 5.1 Critères

1. Sécurité intégrée (sessions, CSRF, hachage, permissions).
2. Simplicité : un CRM n'a pas besoin de temps réel ni de file de messages.
3. Internationalisation et migrations natives.
4. Peu de dépendances.

### 5.2 Comparaison résumée

| Option | Points forts | Points faibles | Verdict |
|---|---|---|---|
| **Django (LTS) + PostgreSQL, rendu serveur** | Auth, sessions, CSRF, permissions, administration, migrations, gettext ; adapté à un CRM | Conventions à respecter | **Recommandé** |
| FastAPI + SQLAlchemy + gabarits | Léger | Auth, permissions, admin, i18n à construire | Acceptable, plus de code de sécurité |
| Next.js / TypeScript | Bonne expérience front | Deux langages et déploiements pour un CRM | Écarté |

### 5.3 Stack **[rév. 2]**

| Couche | Choix | Remarque |
|---|---|---|
| Langage | Python (version stable actuelle, à figer au démarrage) | Cohérence avec les scripts existants de l'administrateur |
| Framework | Django (LTS à la date de lancement) | Administration et permissions intégrées |
| Base | PostgreSQL 16 ou plus récent | Réseau privé |
| Interface | Gabarits Django, JavaScript minimal | Tableaux, filtres, formulaires classiques |
| Design | Tokens issus du branding | Composants internes |
| i18n | gettext pour l'interface ; `*_fr` / `*_en` pour les contenus | Notes libres non traduites |
| Authentification | Sessions Django ; TOTP pour `platform_admin` et `crm_admin` | Pas de compte pour les utilisateurs de robots |
| Tâches et rappels **[rév. 2]** | Tâches planifiées (commande de gestion) qui créent des rappels dans l'application et, si activé, par courriel | Pas de file de messages au départ |
| Exports **[rév. 2]** | CSV et PDF générés à la demande, journalisés | Données personnelles : export réservé à `crm_admin` |
| Courriel | Fournisseur transactionnel (à choisir) | Rappels, réinitialisation |
| Tests | pytest, pytest-django, Playwright (FR/EN), import-linter, tests d'autorisation et d'isolation | — |
| Qualité | ruff, mypy progressif, scan de dépendances, scan de secrets | — |
| Hébergement | Conteneur, reverse proxy TLS, PostgreSQL privé | Hébergement séparé du VPS recommandé (§11) |

**Retiré [rév. 2]** : signatures HMAC, nonces, protocole d'agent, file de tâches distribuée, Redis.

---

## 6. Modules et responsabilités

### 6.1 `core` (partagé)

Identité, profils, organisations, appartenances, rôles, permissions, **tâches et rappels** **[rév. 2]**, audit, consentements, notifications, fichiers, traductions, outbox d'événements.

### 6.2 `partners`

| Responsabilité | Détail |
|---|---|
| Liens d'affiliation | Libellé, code, pays ciblés, statut, dernière revue, responsable |
| Attribution | Jeton signé de courte durée ; pas de traceur sans consentement |
| Prospects | Coordonnées, source, pays, consentement daté, statut |
| **Affiliés** **[rév. 2]** | Entité unique (§4.3) : identité, lien de parrainage, date d'inscription déclarée |
| **Parcours d'inscription et de vérification** **[rév. 2]** | Étapes datées (voir tableau ci-dessous) |
| Interactions et relances | Journal en ajout seul |
| Conformité | Export, suppression, durée de conservation |

**Étapes du parcours** **[rév. 2]** — statuts déclarés par l'administrateur, **jamais de pièce d'identité** :

| Étape | Valeurs possibles |
|---|---|
| Inscription | Non commencée · Déclarée par l'affilié · Compte créé (déclaré) |
| Vérification | Non demandée · Demandée · En cours · Validée · Refusée · À revoir |
| Démo | Non ouvert · Ouvert (déclaré) |

Chaque changement est daté et annoté. La source (« affilié », « administrateur », « support Deriv ») est enregistrée.

### 6.3 `academy`

Programmes, cours et leçons (bilingues), inscriptions, pré-évaluation d'admissibilité (référentiel versionné), exercices, évaluations, progression, attestation interne. La notation ne dépend jamais du solde d'un compte.

### 6.4 `bots` — CRM administratif **[rév. 2]**

Ce module est un **registre administratif**. Il ne communique avec aucun robot. Chaque donnée est une **déclaration** de l'administrateur.

#### 6.4.1 Entités

| Entité | Contenu |
|---|---|
| `bot_user` | Affilié concerné (référence) ; **souhaite un robot** (oui/non) ; **type de robot** : DIFFERS ou OVER/UNDER ; statut de configuration courant ; libellé libre facultatif de l'utilisateur sur le VPS (non secret) |
| `reference_capital` | Montant déclaré, devise, date de la déclaration, auteur. **Aucun solde synchronisé.** |
| `configuration_version` | Version **immuable** : type de robot, environnement déclaré (démo ou réel), capital de référence, réglages déclarés (§6.4.3), date d'application déclarée, auteur, note |
| `intervention` | Date, type, note, auteur, lien vers l'affilié ou l'utilisateur de robot |
| `task` | Titre, échéance, responsable, statut (à faire, faite, annulée), rappel, lien vers la fiche |

#### 6.4.2 Statuts de configuration **[rév. 2]**

Ces cinq statuts décrivent **l'état administratif déclaré**, jamais l'état réel du VPS.

| Statut | Signification | Entrée dans ce statut |
|---|---|---|
| **À configurer** | Utilisateur enregistré, aucune configuration déclarée comme appliquée | Création de la fiche |
| **Configuration appliquée** | L'administrateur a déclaré avoir appliqué la configuration courante sur le VPS | Action « Marquer comme appliquée » : date d'application obligatoire |
| **Modification demandée** | Une nouvelle version a été rédigée mais n'est pas encore déclarée comme appliquée | Création d'une nouvelle version non appliquée |
| **En pause** | L'administrateur a déclaré l'utilisateur en pause (raison obligatoire) | Action explicite |
| **Désactivé** | L'administrateur a déclaré l'utilisateur désactivé (raison obligatoire) | Action explicite |

Règles :
- Une seule version est « courante » par utilisateur de robot.
- Passer à « Configuration appliquée » exige une date et une note ; la version devient la version appliquée déclarée.
- **[rév. 3]** Les statuts sont **calculés** (sauf « En pause » et « Désactivé »). « Modification demandée » apparaît seulement si une déclaration d'application existe pour une version antérieure et qu'une version plus récente est validée sans déclaration. Une version jamais déclarée appliquée reste « À configurer ». Règles complètes : `BOT_CRM_SPEC.md` §3.
- « En pause » et « Désactivé » n'effacent jamais l'historique.
- Chaque transition est journalisée (auteur, date, ancien et nouvel état).
- Une fiche sans déclaration depuis un délai configurable (par défaut 30 jours) est signalée comme « à revalider » dans le tableau de bord.

#### 6.4.3 Réglages déclarés **[rév. 3]**

- La plateforme **ne lit jamais** `reglages.env` et n'importe rien depuis le VPS.
- Les paramètres viennent d'une **liste blanche fermée** (`bots.parameter_definition`), gouvernée par `crm_admin`. Seuls les paramètres au statut `verified` apparaissent dans le formulaire.
- **Aucun champ destiné à un secret** n'existe : ni colonne, ni champ de formulaire, ni table. Ce point est la protection principale.
- Les valeurs sont validées par type, bornes et unité. Une clé inconnue est refusée.
- Les **notes libres** restent possibles. Une détection par expressions régulières **n'est pas considérée comme une protection** : elle sert de rappel, et les mesures réelles sont décrites dans `BOT_CRM_SPEC.md` §9.
- **Liste provisoire** : les 12 clés ne sont pas validées. Elles dépendent de la vérification des fichiers réels, qui n'a pas pu être faite (`BOT_CRM_SPEC.md` §0).

- La plateforme **ne lit jamais** `reglages.env` et **n'importe rien** depuis le VPS.
- Les réglages sont saisis manuellement, à partir d'un **modèle de formulaire par type de robot**.
- Le modèle ne contient que des paramètres **non secrets**, validés par l'administrateur (liste à fournir, §11).
- Aucun champ ne peut accueillir un token, un mot de passe ou une clé. Les champs de texte libre (notes) passent par un **contrôle de motifs** qui détecte les chaînes ressemblant à des secrets et refuse l'enregistrement.

#### 6.4.4 Tableau de bord **[rév. 2]**

Vue d'ensemble pour répondre à « où en est chaque affilié ? » :

| Colonne | Source |
|---|---|
| Affilié, pays, langue | `partners` |
| Étape d'inscription et de vérification | `partners` |
| Souhaite un robot, type | `bots` |
| Statut de configuration déclaré | `bots` |
| Dernière déclaration (date) | `bots` |
| Dernière intervention (date) | `bots` |
| Prochaine tâche (date) | `core` |
| Alertes | Calculées : tâche en retard, « modification demandée » depuis plus de N jours, vérification en attente depuis plus de N jours, fiche à revalider |

Filtres : statut, type de robot, environnement déclaré, étape de vérification, alertes, responsable.

#### 6.4.5 Environnement démo et réel **[rév. 2]**

**[rév. 3]** Seul `crm_admin` peut déclarer un compte réel. La déclaration exige une confirmation explicite, une date, une note et une trace d'audit. Elle ne déclenche **aucune** action sur le VPS ni sur Deriv. Une double validation des versions réelles est recommandée, en attente de décision (`BOT_CRM_SPEC.md` §5).

#### 6.4.6 Tâches, rappels et actions en attente **[rév. 2]**

- Création manuelle, ou automatique lors d'événements (vérification en attente depuis N jours, fiche à revalider, modification demandée sans application).
- Rappels dans l'application, et par courriel si l'administrateur l'active.
- Vue « Mes tâches » par responsable, et vue globale pour `crm_admin`.

### 6.5 `academy` / `partners` / `bots` : interactions

| Événement | Émetteur | Consommateur | Usage |
|---|---|---|---|
| `partners.lead_converted` | partners | bots, academy | Créer une fiche d'affilié |
| `partners.verification_changed` | partners | bots, core | Créer une tâche si la vérification est validée ou refusée |
| `bots.configuration_applied_declared` | bots | core | Journaliser et mettre à jour les alertes |

Les événements passent par l'outbox PostgreSQL. Aucun événement ne part vers le VPS.

---

## 7. Fondations techniques nécessaires

### 7.1 Développement
- Dossier applicatif séparé, docker compose (application et PostgreSQL), environnements local, préproduction, production.
- Configuration par variables d'environnement ; `.env.example` sans valeurs.

### 7.2 Sécurité de base
- Sessions serveur, cookies `__Host-`, Argon2id, limitation de débit, messages d'erreur uniformes.
- TOTP obligatoire pour `platform_admin` et `crm_admin`.
- En-têtes HTTP stricts, CSRF, vérification `Origin`, autoéchappement des gabarits.
- Journal d'audit en ajout seul, pour tout changement de statut, de version de configuration et de donnée personnelle.

### 7.3 Données et multi-tenancy
- Clés composites `(organization_id, id)`.
- Tests d'isolation pour chaque type de ressource.
- Versions de configuration **immuables** : une correction crée une nouvelle version, jamais une modification.

### 7.4 Interdictions techniques **[rév. 2]**

Ces règles sont testées en CI :
- aucune colonne, aucun champ de formulaire, aucune table nommée pour un token, un mot de passe ou une clé Deriv ;
- aucun client HTTP vers le VPS ni vers Deriv depuis la plateforme ;
- aucun module de lecture de fichier `reglages.env` ;
- aucune route de commande ou de contrôle de robot ;
- **[rév. 3]** aucun champ destiné à un secret ; liste blanche fermée ; versions immuables en base ; tests de schéma et d'import (`BOT_CRM_SPEC.md` §11.1). Le contrôle de motifs n'est pas compté comme protection.

### 7.5 Confidentialité
- Registre des traitements, base légale et durée de conservation par catégorie.
- Consentement distinct pour la prospection et pour les relances.
- Export et suppression d'une fiche (affilié, prospect, utilisateur de robot).
- Minimisation : pas de pièce d'identité, pas de capture d'écran de compte, pas de solde.
- Journaux sans données personnelles en clair.

### 7.6 Qualité et livraison
- CI : tests unitaires, autorisation, isolation, parité FR/EN, règles d'import, lint, scans.
- Revue obligatoire pour `core` et `bots`.
- Procédure d'exploitation : sauvegarde, restauration, rotation de secrets, réponse à incident.

---

## 8. Risques de sécurité et de conformité

### 8.1 Sécurité **[rév. 2]**

| # | Risque | Gravité | Mesures |
|---|---|---|---|
| SEC-1 | Saisie d'un token ou d'un mot de passe dans une note | Élevée | **[rév. 3]** Aucun champ secret ; liste blanche ; avertissement et journal ; formation ; purge sur demande. La détection par expressions régulières n'est pas une protection |
| SEC-2 | Compromission d'un compte administrateur (accès aux données personnelles d'affiliés) | Élevée | TOTP obligatoire ; sessions courtes ; journal ; moindre privilège |
| SEC-3 | Fuite de données entre organisations | Élevée | Isolation applicative ; tests ; RLS en phase 6 |
| SEC-4 | Export massif de données personnelles | Élevée | Export réservé à `crm_admin` ; journalisé ; limité en volume ; PDF filigrané |
| SEC-5 | Injection (SQL, gabarits, export CSV) | Moyenne | ORM ; autoéchappement ; neutralisation des formules dans les CSV (`=`, `+`, `-`, `@`) |
| SEC-6 | Fuite via journaux ou sauvegardes | Moyenne | Journaux sans données personnelles ; sauvegardes chiffrées |
| SEC-7 | Dépendances vulnérables | Moyenne | Versions figées ; scans |
| SEC-8 | Accès à la base depuis l'extérieur | Élevée | Réseau privé ; comptes à droits limités |
| SEC-9 | Téléversement malveillant | Faible | Pas de téléversement de pièce d'identité ; types et tailles contrôlés ; analyse |

Les risques liés au VPS (tokens, reglages.env, systemd, trading) **sont hors du périmètre de la plateforme**. Ils restent sous la responsabilité de l'administrateur, avec ses pratiques existantes.

### 8.2 Risques propres au CRM **[rév. 2]**

| # | Risque | Mesures |
|---|---|---|
| CRM-1 | **Écart entre ce qui est déclaré et ce qui est appliqué** : la plateforme affiche une configuration qui n'est pas celle du VPS | Mention « déclaré, non vérifié » sur chaque statut ; date de dernière déclaration visible ; alerte de revalidation ; procédure de revue périodique par l'administrateur |
| CRM-2 | Erreur de saisie des réglages (valeur de capital ou de mise erronée) | Modèle de formulaire avec bornes et unités ; double saisie pour les changements de capital ; historique consultable |
| CRM-3 | Fiche « configuration appliquée » alors que la modification n'a pas été faite | Date et auteur obligatoires ; le statut ne change qu'à la déclaration explicite |
| CRM-4 | Données personnelles d'affiliés en excès | Minimisation ; pas de pièce d'identité ; durée de conservation ; export contrôlé |
| CRM-5 | Notes contenant des informations sensibles | Contrôle de motifs ; formation ; purge sur demande | **[rév. 3]** Limites de longueur ; avertissement visible ; formation ; revue périodique ; purge sur demande |
| CRM-6 | Confusion entre démo et réel | Libellé explicite à chaque affichage ; filtre dédié ; aucune action ne se déclenche automatiquement |

### 8.3 Conformité et contenu (à valider avec un juriste et le responsable)

| # | Sujet | Mesure proposée |
|---|---|---|
| CONF-1 | Activité d'affiliation et d'utilisation de robots automatisés | Le CRM ne passe ni n'exécute d'ordre. Il **documente** une activité qui peut être réglementée selon les pays : revue juridique avant d'enregistrer des affiliés hors de pays validés |
| CONF-2 | Conditions Deriv (affiliation, API, données partagées) | Revue à chaque changement ; pas de transmission de données à Deriv par la plateforme |
| CONF-3 | Données personnelles (RGPD et équivalents) | §7.5 ; registre ; analyse d'impact si profilage |
| CONF-4 | Public jeune | Vérification de l'âge déclaré ; pas de contenu destiné aux mineurs |
| CONF-5 | Promesses non vérifiées | Aucun témoignage ni statistique sans source |
| CONF-6 | Avertissements de risque | Texte officiel en anglais, traduction distincte |
| CONF-7 | Droit de la marque | Mention de distinction ; pas de logo Deriv sans autorisation |
| CONF-8 | Droits des traductions religieuses | Vérifier la source |

---

## 9. Feuille de route de construction progressive **[rév. 2]**

Chaque phase a un critère de sortie vérifiable. Aucune phase ne commence sans approbation de la précédente. Estimations pour une personne à temps plein, indicatives.

### Phase 1 — Fondations (3 à 4 semaines)
- Squelette, Docker, PostgreSQL, CI, règles d'import, tests.
- Identité, sessions, TOTP, organisations, rôles, permissions, refus par défaut.
- Journal d'audit. Internationalisation FR/EN avec parité en CI.
- Design minimal, pages de connexion et de profil.
- Politique de confidentialité (brouillon).

**Sortie** : tests d'authentification et d'isolation verts ; FR et EN complets ; déploiement de test ; revue de sécurité interne.

### Phase 2 — ACADEMY (4 à 6 semaines)
- Programmes, cours, leçons bilingues ; import des huit séquences après relecture.
- Inscriptions, pré-évaluation, exercices, progression, attestation interne.

**Sortie** : parcours complet en FR et EN ; isolation testée ; contenus validés.

### Phase 3 — PARTNERS : prospects, affiliés et parcours (3 à 5 semaines)
- Liens d'affiliation, attribution par jeton signé.
- Prospects avec consentement ; conversion en affilié (§4.3).
- **Parcours d'inscription et de vérification** (§6.2), sans pièce d'identité.
- Interactions, relances, export, suppression.

**Sortie** : validation juridique écrite ; tests de consentement ; export et suppression vérifiés.

### Phase 4 — BOT MANAGEMENT : CRM des utilisateurs de robots (4 à 5 semaines) **[rév. 2]**
- Fiche utilisateur de robot liée à l'affilié : souhaite un robot, type DIFFERS ou OVER/UNDER.
- Capital de référence déclaré, avec historique.
- Versions de configuration immuables, réglages déclarés selon modèle par type.
- Statuts de configuration (§6.4.2) et leurs règles de transition.
- Environnement démo ou réel déclaré.
- Interventions, notes, dates.

**Sortie** : tests de `BOT_CRM_SPEC.md` §11 verts (statuts, immuabilité, permissions, déclaration réelle, schéma sans secret, import) ; liste blanche validée contre les fichiers réels ; aucune dépendance vers le VPS.

### Phase 5 — Tableau de bord, tâches et rappels (3 à 4 semaines) **[rév. 2]**
- Vue d'ensemble par affilié et par utilisateur de robot, filtres, alertes.
- Tâches, rappels dans l'application et par courriel, vue « Mes tâches ».
- Exports CSV et PDF journalisés, avec neutralisation des formules.
- Procédure de revue périodique des déclarations.

**Sortie** : alertes correctes sur jeux de test ; exports contrôlés ; charge acceptable sur un jeu de données réaliste.

### Phase 6 — Durcissement et exploitation (3 à 4 semaines)
- Politiques de ligne PostgreSQL.
- Test d'intrusion de l'application.
- Sauvegardes chiffrées, restauration testée.
- Procédures d'exploitation et de réponse à incident ; revue juridique finale.

**Sortie** : aucun constat critique ouvert ; restauration validée.

### Phases retirées **[rév. 2]**
- ~~Agent VPS et communication signée~~
- ~~Configuration appliquée par l'agent, arrêt d'urgence, actions sur le réel~~

Si un besoin de contrôle technique apparaît plus tard, il fera l'objet d'un document de décision séparé, avec une analyse de sécurité et juridique préalable.

### Calendrier indicatif **[rév. 2]**

| Phase | Durée | Cumul |
|---|---|---|
| 1 | 3 à 4 semaines | 3 à 4 |
| 2 | 4 à 6 semaines | 7 à 10 |
| 3 | 3 à 5 semaines (parallélisable avec la fin de 2) | 9 à 14 |
| 4 | 4 à 5 semaines | 13 à 19 |
| 5 | 3 à 4 semaines | 16 à 23 |
| 6 | 3 à 4 semaines | 19 à 27 |

Le contenu pédagogique et la saisie initiale des fiches sont souvent le goulot d'étranglement. À estimer séparément.

---

## 10. Mise à jour des documents existants

- `PROPOSED_ARCHITECTURE.md`, `MIGRATION_PLAN.md`, `IMPLEMENTATION_ROADMAP.md` : déjà marqués « remplacés ». Un amendement **[rév. 2]** en tête précise les sections retirées.
- `GAP_ANALYSIS.md` : §2.3 décrit un agent et des commandes ; le même amendement s'applique.
- `CURRENT_STATE.md` : inchangé.

---

## 11. Décisions — état après révision 3

**Validées [rév. 3]** : 4 (propriété `partners`), 5 (fiches robots sans compte), 7 (capital déclaré manuellement), 9 (mode réel par `crm_admin`). **Non tranchée** : 1 (framework : Django recommandé, décision toujours ouverte). **Bloquante** : 6 (liste des réglages, non vérifiée, `BOT_CRM_SPEC.md` §0). Les autres restent ouvertes. Détail des décisions propres au CRM : `BOT_CRM_SPEC.md` §10.

1. **Framework** : Django (recommandé) ou FastAPI.
2. **Hébergement de la plateforme** : hors du VPS Ubuntu (recommandé), ou sur le VPS dans un conteneur isolé, utilisateur dédié, réseau privé.
3. **Nom de domaine** et sous-domaine.
4. **Propriété de la fiche affilié** (§4.3) : `partners` (recommandé) ou `bots`.
5. **Utilisateurs de robots** : fiches gérées par l'administrateur (recommandé) ou comptes de connexion.
6. **Liste des réglages à déclarer** : fournir **les noms des paramètres** de `reglages.env` pour chaque type de robot, **sans leurs valeurs**, en indiquant lesquels sont secrets. Seuls les paramètres non secrets seront saisissables. Les tokens restent hors de la plateforme.
7. **Capital de référence** : montant déclaré manuellement, avec devise et date. Confirmer qu'aucune synchronisation de solde n'est souhaitée.
8. **Seuils d'alerte** : délai de revalidation (proposition : 30 jours), délai de « modification demandée » (proposition : 7 jours), délai de vérification en attente (proposition : 14 jours).
9. **Qui peut déclarer un environnement réel** : `crm_admin` uniquement (proposition), avec double saisie.
10. **Durée de conservation** des interventions, des notes et des fiches d'affiliés non actifs.
11. **Canal WhatsApp** : retiré de la plateforme, ou cadré par une politique écrite.
12. **Validation juridique** : activité d'affiliation et de robots, données de prospects, public, pays cibles (CONF-1 et CONF-3).
13. **Responsable pédagogique** pour les contenus ACADEMY.
14. **Fournisseurs** : courriel transactionnel, stockage objet.
15. **Langue par défaut** : français, avec repli sur la langue du navigateur.

---

## 12. Prochaine action proposée

Après validation de cette révision et des décisions 1 à 5 : créer le squelette de la phase 1 dans un dossier séparé, sans modifier les fichiers existants. Aucune implémentation du module BOT MANAGEMENT avant validation de la phase 3, qui fixe la propriété de la fiche affilié.
