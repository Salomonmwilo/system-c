# SYSTEM-C Platform : spécification du CRM BOT MANAGEMENT

Statut : **spécification de conception, révision 3, à valider avant implémentation.**

Ce document détaille les décisions validées pour les affiliés, les utilisateurs de robots et leurs configurations. Il complète `NEW_PROJECT_DIRECTION.md` (révision 3). Il ne décrit aucun contrôle technique du VPS.

Principe central : **la plateforme enregistre ce que l'administrateur déclare. Elle ne sait pas ce qui tourne réellement sur le VPS.**

---

## 0. Points non vérifiés (bloquants pour la phase 4)

La liste des paramètres de la section 4 est **provisoire**. Elle n'a pas été confirmée contre les fichiers réels, pour les raisons suivantes :

- aucun fichier `reglages.env` ni aucun code de robot n'est présent dans le dépôt ;
- aucun dossier de l'administrateur n'est accessible depuis cette session ;
- les unités (secondes, points, devise), les bornes et l'usage de chaque paramètre par chaque robot sont inconnus.

Conséquence : tout paramètre reste en statut `pending_verification` et **n'apparaît dans aucun formulaire** tant qu'il n'est pas marqué `verified` par un administrateur, à partir d'une vérification consignée (§4.3).

**Procédure de vérification proposée (sans exposer de valeur ni de secret)** :

1. Pour chaque robot, extraire **uniquement les noms de clés** du fichier de réglages, sans les valeurs :
   `cut -d= -f1 reglages.env | grep -E '^[A-Z_]+$' | sort -u`
   Ne jamais partager le fichier complet : il peut contenir des tokens.
2. Pour chaque nom de clé, retrouver les lignes du code qui le lisent :
   `grep -n "NOM_DE_LA_CLE" <fichiers du robot>`
   et partager **uniquement** les noms de fichiers, numéros de ligne et types de lecture, pas les valeurs.
3. Noter si la clé est lue par les deux robots, par un seul, ou par aucun.
4. Noter l'unité et la plage de valeurs réellement acceptées par le code.
5. Signaler toute clé absente de la liste, et toute clé dont le nom suggère un secret.

Ce qui est livré par l'administrateur pour finaliser la liste : une table `clé | robot(s) | unité | plage | secret ? | source (fichier:ligne)`.

---

## 1. Propriété et relations entre modules

### 1.1 Décisions validées

| Sujet | Décision |
|---|---|
| Fiche principale d'un affilié | **`partners`** est propriétaire. Une seule fiche par personne et par organisation. |
| Apprenant également affilié | `academy` référence `partners.affiliate.id`. Pas de copie des données personnelles. |
| Affilié utilisant un robot | `bots` référence `partners.affiliate.id`. Pas de copie des données personnelles. |
| Utilisateur de robot | Fiche administrative `bots.bot_user`, **sans compte de connexion obligatoire**. |
| Compte de connexion | Facultatif, réservé aux personnes qui accèdent à ACADEMY ou à un autre espace. Lié à la même fiche affilié s'il existe. |

### 1.2 Graphe de dépendances autorisées

```
              core  (identité, organisations, rôles, audit, tâches, consentements,
               ▲      seuils d'alerte, i18n, notifications)
               │
   ┌───────────┼──────────────────────┐
   │           │                      │
partners ◄── academy            bots ──┘
   ▲            (références ids)     (références ids,
   │                                 lit partners
   └─────────── bots                 via son API publique)
```

Règles :
- `core` ne dépend d'aucun module.
- `partners` ne dépend que de `core`. Il ne doit **jamais** importer `academy` ou `bots`.
- `academy` et `bots` dépendent de `partners` (par identifiant et API publique) et de `core`.
- `academy` et `bots` **ne se dépendent pas mutuellement**.
- Aucun module ne communique avec le VPS, ni avec Deriv.

Ces règles sont vérifiées par import-linter en CI (§9).

### 1.3 Événements entre modules

| Événement | Émetteur | Consommateur | Effet |
|---|---|---|---|
| `partners.lead_converted` | partners | core | Création d'une fiche affilié |
| `partners.verification_changed` (valeur `validated`) | partners | core | Tâche « Préparer la fiche robot si souhaité » |
| `partners.verification_changed` (valeur `rejected` ou `to_review`) | partners | core | Tâche de suivi |
| `bots.configuration_declared_applied` | bots | core | Mise à jour des alertes, journal |

Aucun événement ne crée automatiquement une fiche `bot_user` : l'administrateur décide.

---

## 2. Modèle de données recommandé

Conventions : identifiants UUID ; `organization_id` sur chaque table ; horodatages en UTC ; montants en `NUMERIC(18,2)` ; devise ISO 4217 ; enregistrements « append-only » sauf mention contraire.

### 2.1 `partners` (propriétaire des affiliés)

**`partners.affiliate`** (modifiable)

| Champ | Type | Règle |
|---|---|---|
| `id` | UUID | Clé primaire |
| `organization_id` | UUID | Obligatoire |
| `display_name` | texte ≤ 120 | Obligatoire |
| `email` | texte | Facultatif, unique par organisation (normalisé en minuscules) |
| `phone` | texte | Facultatif |
| `country_code` | ISO 3166-1 alpha-2 | Facultatif |
| `preferred_language` | `fr` \| `en` | Obligatoire, défaut `fr` |
| `referral_link_id` | UUID | Lien de parrainage d'origine |
| `assigned_advisor_id` | UUID | Conseiller responsable |
| `created_at`, `created_by` | | Obligatoires |
| `archived_at` | horodatage | Nul si actif ; l'archivage n'efface rien |

Aucune pièce d'identité, aucune photo de document, aucun mot de passe.

**`partners.affiliate_track_event`** (append-only) : trace le parcours. La valeur courante de chaque piste est la dernière ligne.

| Champ | Règle |
|---|---|
| `affiliate_id`, `track`, `value` | `track` ∈ `registration`, `verification`, `demo` ; `value` limitée à l'énumération de la piste (ci-dessous) |
| `declared_at` | Date fournie par l'administrateur (peut être antérieure à l'enregistrement) |
| `recorded_at`, `recorded_by` | Obligatoires |
| `source` | `affiliate`, `administrator`, `deriv_support` |
| `note` | Facultative, ≤ 500 caractères |

Énumérations :
- `registration` : `not_started`, `declared_by_affiliate`, `account_created_declared`
- `verification` : `not_requested`, `requested`, `in_progress`, `to_review`, `validated`, `rejected`
- `demo` : `not_opened`, `opened_declared`

**`partners.interaction`** (append-only) : contact avec l'affilié.

| Champ | Règle |
|---|---|
| `affiliate_id`, `occurred_at`, `kind`, `note`, `author_id` | `kind` ∈ `call`, `message`, `meeting`, `reminder_sent`, `other` |

Le « dernier contact » est calculé à partir de cette table **et** de `bots.intervention` par le module `bots`, via l'API publique de `partners`.

### 2.2 `bots` (CRM des utilisateurs de robots)

**`bots.bot_user`** (modifiable)

| Champ | Règle |
|---|---|
| `id`, `organization_id` | Obligatoires |
| `affiliate_id` | Référence `partners.affiliate.id`, obligatoire |
| `wants_bot` | Booléen : souhaite utiliser un robot |
| `robot_type` | `DIFFERS` \| `OVER_UNDER`, nul tant que non choisi |
| `vps_label` | Facultatif, ≤ 64 caractères, motif `^[a-z0-9_-]+$`. **Libellé d'utilisateur VPS, non secret.** Aucun chemin, aucun mot de passe |
| `override` | `none` \| `paused` \| `disabled` |
| `override_reason`, `override_by`, `override_at` | Obligatoires si `override` ≠ `none` |
| `created_at`, `created_by` | Obligatoires |

Contrainte : au plus **une fiche non archivée par affilié** (hypothèse à confirmer, §10).

**`bots.configuration_version`** (immuable une fois validée)

| Champ | Règle |
|---|---|
| `id`, `organization_id`, `bot_user_id` | Obligatoires |
| `version_number` | Entier croissant, unique par `bot_user_id` |
| `state` | `draft` \| `validated` |
| `robot_type` | Copie du type au moment de la création (ne change pas) |
| `account_type` | `demo` \| `real` |
| `reference_capital_amount`, `reference_capital_currency` | Capital de référence **déclaré**, jamais synchronisé |
| `admin_note` | Facultative, ≤ 1000 caractères |
| `created_at`, `created_by` | Obligatoires |
| `validated_at`, `validated_by` | Renseignés à la validation |
| `real_confirmed_at`, `real_confirmed_by`, `real_confirmation_wording` | Renseignés seulement si `account_type` = `real` (§5) |

**`bots.configuration_parameter`** (immuable avec sa version)

| Champ | Règle |
|---|---|
| `version_id`, `key` | Clé primaire composite |
| `value` | Texte normalisé, ≤ 64 caractères |
| `unit` | Copie de la définition au moment de la validation |

Contraintes appliquées par le service **et** testées : `key` existe dans `bots.parameter_definition` pour le `robot_type` de la version, est `verified`, et est applicable au `account_type`. La valeur respecte le type, les bornes et l'unité.

**`bots.parameter_definition`** (liste blanche, gouvernée par `crm_admin`)

| Champ | Règle |
|---|---|
| `robot_type`, `key` | Clé primaire composite |
| `value_type` | `decimal`, `integer`, `duration`, `enum` |
| `unit` | Inconnue pour l'instant : `to_verify` |
| `min_value`, `max_value` | Inconnus pour l'instant : nuls |
| `applies_to_account_types` | `demo`, `real` ou `both` |
| `is_secret` | Toujours `false`. Une clé marquée `true` ne peut pas être créée (contrainte de schéma) |
| `status` | `pending_verification` \| `verified` |
| `verification_reference` | Obligatoire pour `verified` : fichier et ligne vérifiés, date, auteur (sans valeur) |

**`bots.application_declaration`** (append-only) : déclaration administrative qu'une version a été appliquée sur le VPS.

| Champ | Règle |
|---|---|
| `version_id` | Doit référencer une version `validated` |
| `kind` | `applied` \| `correction` |
| `applied_on` | Date d'application déclarée (obligatoire, peut être passée) |
| `target_declaration_id` | Pour `correction` : la déclaration corrigée |
| `reason`, `recorded_at`, `recorded_by` | Obligatoires ; `reason` obligatoire pour `correction` |

Une correction n'efface jamais la ligne initiale : elle la neutralise dans le calcul de statut.

**`bots.status_event`** (append-only) : changements manuels de `override` (pause, désactivation, réactivation).

**`bots.intervention`** (append-only) : `occurred_at`, `kind` (`call`, `message`, `follow_up`, `incident_reported`, `other`), `note`, `author_id`. Un `incident_reported` est une **déclaration** de l'administrateur, pas une détection.

### 2.3 `academy` (références seulement)

`academy.enrollment.affiliate_id` (nullable) référence `partners.affiliate.id`. Un apprenant peut exister sans être affilié, et inversement. Les données pédagogiques restent dans `academy`.

### 2.4 `core` (partagé)

- **`core.task`** : `title`, `subject_kind` (`affiliate`, `bot_user`, `learner`), `subject_id`, `owner_id`, `due_at`, `reminder_at`, `status` (`open`, `done`, `cancelled`), `created_by`, `closed_at`. Le lien vers le sujet est validé par le service (pas de clé étrangère croisée entre modules).
- **`core.alert_threshold`** : seuils configurables par organisation (§6.2).
- **`core.consent`** : `person` ou `affiliate` référencé, finalité, `granted_at`, `withdrawn_at`.
- **`core.audit_log`** (append-only, droits sans `UPDATE` ni `DELETE`) : `actor_id`, `organization_id`, `action`, `target_kind`, `target_id`, `before_summary`, `after_summary`, `occurred_at`, `result`. Aucun contenu de note ni valeur de paramètre complet dans le résumé : identifiants et types d'action seulement.

### 2.5 Vues calculées (lecture seule)

- `v_affiliate_current_tracks` : dernière valeur de chaque piste.
- `v_bot_user_status` : statut de configuration calculé (§3.2).
- `v_bot_user_alerts` : alertes calculées (§6).

---

## 3. Statuts administratifs

### 3.1 Statuts de configuration (`bots.bot_user`)

Les cinq statuts demandés. Ils sont **calculés**, sauf « En pause » et « Désactivé », qui sont des actions explicites.

| Statut | Calcul |
|---|---|
| **Désactivé** | `override = disabled` |
| **En pause** | `override = paused` |
| **À configurer** | Aucune version `validated`, **ou** version validée jamais déclarée appliquée |
| **Configuration appliquée** | La version `validated` la plus récente a une déclaration `applied` effective (non corrigée) |
| **Modification demandée** | Une déclaration `applied` effective existe pour une version antérieure, et une version plus récente est `validated` sans déclaration effective |

Précisions :
- Une version `draft` ne change jamais le statut. Elle s'affiche comme « brouillon en préparation ».
- Une version `draft` ne devient « demandée » qu'après validation : une validation est la demande de modification.
- Réactiver un utilisateur (`override` → `none`) rétablit le statut calculé.
- Aucune transition ne supprime d'historique.

### 3.2 Transitions manuelles

| Action | Qui | Effet | Trace |
|---|---|---|---|
| Passer en pause | `crm_operator`, `crm_admin` | `override = paused`, raison obligatoire | `status_event` + audit |
| Désactiver | `crm_admin` | `override = disabled`, raison obligatoire | `status_event` + audit |
| Réactiver | `crm_admin` | `override = none` | `status_event` + audit |

### 3.3 Statuts de parcours (partners, rappel)

| Piste | Valeurs |
|---|---|
| Inscription | `not_started` → `declared_by_affiliate` → `account_created_declared` |
| Vérification | `not_requested` → `requested` → `in_progress` → `validated` · `rejected` · `to_review` |
| Démo | `not_opened` → `opened_declared` |

Les valeurs sont des **déclarations datées**. Aucun statut n'est obtenu automatiquement auprès de Deriv.

---

## 4. Liste blanche des paramètres (provisoire)

### 4.1 Règles

1. Seuls les paramètres de `bots.parameter_definition` au statut `verified` apparaissent dans le formulaire.
2. Le formulaire est **généré à partir de la liste**, jamais à partir d'un fichier importé.
3. Aucune saisie libre de clé : un champ ne peut pas être ajouté par l'utilisateur.
4. Aucun paramètre ne suppose d'être commun aux deux robots.
5. Un paramètre `DEMO` n'est saisissable que pour un `account_type = demo` ; un paramètre réel, pour `real` (à confirmer, §4.4).

### 4.2 Inventaire initial (non vérifié)

Pour chaque clé : statut `pending_verification` pour les deux robots, unité et bornes inconnues. La colonne « Applicabilité » reflète la **seule** hypothèse de nommage et doit être confirmée.

| Clé | Hypothèse de sens (à confirmer) | DIFFERS | OVER_UNDER | Compte | Unité | Bornes |
|---|---|---|---|---|---|---|
| `STAKE` | Mise par contrat | À vérifier | À vérifier | les deux | À vérifier | À vérifier |
| `DURATION` | Durée d'un contrat | À vérifier | À vérifier | les deux | À vérifier | À vérifier |
| `INTERVAL` | Intervalle entre contrats ou cycles | À vérifier | À vérifier | les deux | À vérifier | À vérifier |
| `MAX_TRADES` | Nombre maximal de contrats (par session ?) | À vérifier | À vérifier | les deux | Sans unité | À vérifier |
| `MAX_TRADES_DAY` | Nombre maximal de contrats par jour | À vérifier | À vérifier | les deux | Sans unité | À vérifier |
| `SESSION_TARGET` | Objectif de gain par session | À vérifier | À vérifier | les deux | À vérifier | À vérifier |
| `SESSION_PAUSE` | Pause après une session | À vérifier | À vérifier | les deux | À vérifier | À vérifier |
| `DAILY_TARGET` | Objectif de gain quotidien | À vérifier | À vérifier | les deux | À vérifier | À vérifier |
| `DAILY_MAX_LOSS` | Perte maximale quotidienne (réel ?) | À vérifier | À vérifier | réel ? | À vérifier | À vérifier |
| `DAILY_MAX_LOSS_DEMO` | Perte maximale quotidienne (démo ?) | À vérifier | À vérifier | démo ? | À vérifier | À vérifier |
| `CAPITAL` | Capital de référence (ou capital de travail ?) | À vérifier | À vérifier | les deux ? | Devise à vérifier | À vérifier |
| `DEMO_CAPITAL` | Capital de référence démo | À vérifier | À vérifier | démo | Devise à vérifier | À vérifier |

Points à trancher dès la vérification :
- `CAPITAL` et `DEMO_CAPITAL` : doublons du capital de référence déclaré dans `configuration_version.reference_capital_*`. Décision : soit le capital est **seulement** dans la version (recommandé), soit la clé du robot est saisie aussi. Il ne doit pas exister deux sources pour une même valeur.
- `DAILY_MAX_LOSS` et `DAILY_MAX_LOSS_DEMO` : hypothèse de séparation par type de compte, à confirmer.
- `MAX_TRADES` et `MAX_TRADES_DAY` : portée (session ou jour) à confirmer.

### 4.3 Passage à `verified`

Une clé ne passe à `verified` que lorsque :
- la table de vérification (§0) est complète pour ce robot ;
- `unit`, `min_value`, `max_value`, `value_type`, `applies_to_account_types` sont renseignés ;
- `verification_reference` consigne le fichier, la ligne, la date et l'auteur ;
- un test de contrat vérifie que la clé est encore lue par le code du robot (test manuel documenté, pas d'accès automatisé au VPS).

### 4.4 Questions ouvertes

- Un paramètre réel peut-il être saisi dans une version `demo` ? (Recommandation : non.)
- Les paramètres de sécurité (pertes maximales) sont-ils obligatoires pour une version `real` ? (Recommandation : oui, à confirmer.)

---

## 5. Déclaration du mode réel

### 5.1 Règles

- **Seul `crm_admin` peut déclarer un compte réel.**
- L'opération exige, dans cet ordre :
  1. une case de confirmation explicite, dont le libellé (version du texte) est enregistré ;
  2. une date de déclaration ;
  3. une note administrative ;
  4. une entrée d'audit.
- La déclaration **ne déclenche aucune action** sur le VPS ni sur Deriv.
- Une version `real` ne peut pas passer à `validated` sans ces quatre éléments.
- Revenir à `demo` se fait par une **nouvelle version**. La déclaration réelle précédente reste dans l'historique.

### 5.2 Question ouverte : double validation

Recommandation (non encore validée) : une version `real` doit être validée par un **second** `crm_admin` différent de son auteur. Sans cela, un seul administrateur peut à la fois rédiger et valider un réglage sur compte réel.

---

## 6. Alertes

### 6.1 Quatre catégories distinctes

| Catégorie | Définition | Calcul |
|---|---|---|
| **Dernier contact** | Aucun contact avec l'affilié depuis trop longtemps | Dernière `partners.interaction` ou `bots.intervention`, ou création de la fiche si aucune |
| **Configuration appliquée** | La dernière déclaration effective est ancienne : à revalider | Date de la déclaration `applied` effective la plus récente |
| **Modification en attente** | Une version validée attend sa déclaration d'application | `validated_at` de la version non déclarée appliquée |
| **Inscription ou vérification inachevée** | Une piste n'a pas évolué depuis trop longtemps | Date de la dernière `affiliate_track_event` de la piste, si la valeur n'est pas terminale |

Les valeurs terminales sont : `account_created_declared` (inscription), `validated` et `rejected` (vérification), `opened_declared` (démo).

### 6.2 Seuils configurables

Chaque organisation règle ses seuils dans `core.alert_threshold`, avec des bornes imposées par le système.

| Clé | Catégorie | Défaut proposé | Bornes |
|---|---|---|---|
| `contact_stale_days` | Dernier contact | 30 | 7 à 180 |
| `modification_pending_days` | Modification en attente | 7 | 1 à 60 |
| `configuration_review_days` | Configuration appliquée | 30 | 7 à 365 |
| `registration_stuck_days` | Inscription inachevée | 7 | 1 à 60 |
| `verification_stuck_days` | Vérification inachevée | 14 | 1 à 90 |

Règles :
- Modifier un seuil est une action de `crm_admin`, journalisée (ancienne et nouvelle valeur).
- Un seuil hors bornes est refusé.
- Les seuils ne modifient aucune donnée : ils ne produisent que des alertes et des tâches proposées.

### 6.3 Actions produites

Une alerte affiche : la catégorie, la date de référence, l'affilié ou l'utilisateur concerné. Elle peut être transformée en tâche (`core.task`) par l'administrateur. Aucune alerte ne crée de tâche automatiquement, sauf les deux événements du §1.3.

---

## 7. Règles de permissions

### 7.1 Rôles

| Rôle | Portée |
|---|---|
| `platform_admin` | Globale, TOTP obligatoire, toutes les actions journalisées |
| `org_admin` | Organisation : membres, paramètres généraux |
| `crm_admin` | Organisation : CRM complet, déclaration réelle, seuils, liste blanche |
| `crm_operator` | Organisation : saisie des fiches, interventions, brouillons, pauses |
| `crm_viewer` | Organisation : lecture, données personnelles masquées par défaut |
| `partner_manager` | Organisation : affiliés, prospects, liens |
| `partner_advisor` | Affiliés assignés uniquement |
| `academy_instructor`, `academy_student` | Hors CRM |

### 7.2 Matrice

Légende : **✔** autorisé · **✖** interdit · **C** autorisé avec confirmation et trace · **A** autorisé si affilié assigné

| Action | crm_admin | crm_operator | crm_viewer | partner_manager | partner_advisor |
|---|---|---|---|---|---|
| Créer / modifier un affilié | ✔ | ✖ | ✖ | ✔ | A |
| Voir les données personnelles d'un affilié | ✔ | ✔ | masquées | ✔ | A |
| Modifier le parcours (pistes) | ✔ | ✔ | ✖ | ✔ | A |
| Créer une fiche utilisateur de robot | ✔ | ✔ | ✖ | ✖ | ✖ |
| Choisir le type de robot | ✔ | ✔ | ✖ | ✖ | ✖ |
| Créer un brouillon de version (démo) | ✔ | ✔ | ✖ | ✖ | ✖ |
| Créer un brouillon de version (réel) | ✔ | ✖ | ✖ | ✖ | ✖ |
| Valider une version démo | ✔ | ✖ | ✖ | ✖ | ✖ |
| Valider une version réelle | C | ✖ | ✖ | ✖ | ✖ |
| Déclarer qu'un compte est réel | C | ✖ | ✖ | ✖ | ✖ |
| Déclarer une application (démo) | ✔ | ✔ | ✖ | ✖ | ✖ |
| Déclarer une application (réel) | ✔ | ✖ | ✖ | ✖ | ✖ |
| Corriger une déclaration | ✔ | ✔ (démo) | ✖ | ✖ | ✖ |
| Mettre en pause | ✔ | ✔ | ✖ | ✖ | ✖ |
| Désactiver / réactiver | ✔ | ✖ | ✖ | ✖ | ✖ |
| Modifier les seuils d'alerte | ✔ | ✖ | ✖ | ✖ | ✖ |
| Modifier la liste blanche | ✔ | ✖ | ✖ | ✖ | ✖ |
| Créer une tâche | ✔ | ✔ | ✖ | ✔ | A |
| Exporter (CSV, PDF) | ✔ | ✖ | ✖ | ✖ | ✖ |
| Archiver un affilié | ✔ | ✖ | ✖ | ✔ | ✖ |
| Supprimer définitivement des données | `platform_admin` seul, sur demande documentée | ✖ | ✖ | ✖ | ✖ |

### 7.3 Règles transverses

- **Refus par défaut** : une action absente de la matrice est interdite, et un test échoue si une route n'a pas de permission déclarée.
- **Aucune modification d'une version validée**, par aucun rôle, y compris `platform_admin`. Seule une nouvelle version est possible.
- **Aucune suppression** d'une déclaration, d'un événement de statut, d'une intervention ou d'une entrée d'audit.
- **Export** : journalisé, limité en volume, neutralisation des formules CSV (`=`, `+`, `-`, `@`).
- **Isolation** : une organisation ne voit jamais les fiches d'une autre (test par type de ressource).
- Les rôles `academy_*` n'ont accès à aucune route du CRM.

---

## 8. Scénarios d'utilisation

Chaque scénario indique les données créées et les permissions utilisées.

### S1 : nouvel affilié
1. `partner_manager` crée la fiche affilié (`partners.affiliate`).
2. Il enregistre la piste inscription : `declared_by_affiliate`, source `affiliate`.
3. Aucune fiche robot n'est créée.
- **Données** : 1 affilié, 1 événement de piste.

### S2 : vérification validée
1. `partner_manager` enregistre `verification = validated`, source `deriv_support`, date fournie.
2. Un événement crée une tâche « Décider si la fiche robot est ouverte » (`core.task`).
- **Données** : événement de piste, tâche.

### S3 : l'affilié souhaite un robot
1. `crm_operator` crée `bot_user` avec `wants_bot = true` et `robot_type = DIFFERS`.
2. Statut calculé : **À configurer**.
- **Données** : 1 fiche robot. Pas de version.

### S4 : première configuration (démo)
1. `crm_operator` crée un brouillon de version `demo` avec les paramètres autorisés et le capital de référence déclaré.
2. `crm_admin` valide la version : elle devient immuable.
3. Hors plateforme, l'administrateur applique la configuration sur le VPS.
4. `crm_operator` enregistre `applied_on` (date du jour ou antérieure) et une note : déclaration `applied`.
5. Statut calculé : **Configuration appliquée**.
- **Données** : version validée, paramètres, déclaration.

### S5 : modification de la mise
1. `crm_operator` crée une nouvelle version (copie de la précédente, à modifier). L'ancienne version reste intacte.
2. `crm_operator` ne peut pas valider une version démo ; `crm_admin` valide.
3. Statut calculé : **Modification demandée**, alerte après `modification_pending_days`.
4. Hors plateforme, l'administrateur applique le changement sur le VPS.
5. Déclaration `applied` pour la nouvelle version. Statut : **Configuration appliquée**.
- **Données** : deux versions, deux déclarations.

### S6 : erreur de déclaration
1. Une déclaration `applied` est saisie pour la mauvaise date ou la mauvaise version.
2. `crm_operator` (démo) ou `crm_admin` (réel) enregistre une `correction` avec motif.
3. Le statut est recalculé. La ligne d'origine reste dans l'historique.

### S7 : passage en compte réel
1. `crm_admin` crée un brouillon de version `real`. Un `crm_operator` ne peut pas le faire.
2. `crm_admin` coche la confirmation, indique la date et une note. Une entrée d'audit est créée.
3. Validation : demandée à un second `crm_admin` si la double validation est retenue (§5.2).
4. Aucune commande n'est envoyée au VPS. L'administrateur applique la configuration à la main, puis déclare l'application.

### S8 : pause
1. `crm_operator` met la fiche en pause avec un motif.
2. Statut : **En pause**. L'historique est conservé.
3. Réactivation par `crm_admin` : retour au statut calculé.

### S9 : désactivation
1. `crm_admin` désactive la fiche avec un motif. Statut : **Désactivé**.
2. Aucune nouvelle version ne peut être validée tant que la fiche est désactivée.

### S10 : alerte de contact
1. Aucun contact depuis `contact_stale_days` jours.
2. L'alerte « Dernier contact » apparaît au tableau de bord.
3. L'administrateur crée une tâche de relance, ou enregistre un contact qui clôt l'alerte.

### S11 : affilié devenu apprenant
1. Un affilié s'inscrit à ACADEMY. `academy.enrollment.affiliate_id` référence sa fiche.
2. Aucune donnée personnelle n'est copiée. Le parcours pédagogique reste dans `academy`.

### S12 : tentative de saisie d'un secret
1. Un utilisateur saisit une clé API dans la note.
2. La note est enregistrée **uniquement si l'administrateur confirme**, avec un avertissement qui explique que la plateforme ne doit contenir aucun secret.
3. Un signalement est journalisé. Ce mécanisme est un **rappel**, pas une protection : la protection réelle est l'absence de champ destiné aux secrets (§9).

### S13 : export
1. `crm_admin` exporte la liste des fiches robots au format CSV.
2. L'export est journalisé, sans contenu des notes.

### S14 : inscription inachevée
1. La piste de vérification reste `requested` plus de `verification_stuck_days` jours.
2. Une alerte apparaît. L'administrateur crée une tâche de relance.

---

## 9. Sécurité : protections réelles et limites

### 9.1 Protections structurelles (à privilégier)

- **Aucun champ de secret** : aucune colonne, aucun champ de formulaire, aucune table nommée pour un token, un mot de passe, une clé API ou un identifiant de connexion.
- **Liste blanche fermée** : les clés de configuration viennent uniquement de `bots.parameter_definition`. Une clé inconnue est refusée par le service et par une contrainte de base.
- **Types et bornes** : chaque valeur est validée selon son type, ses bornes et son unité.
- **Aucun client réseau** vers le VPS ni vers Deriv dans le code du module (test d'import et de dépendances).
- **Aucune lecture de fichier** de réglages.
- **Versions immuables** : contrainte en base (déclencheur refusant toute mise à jour d'une version validée et de ses paramètres).
- **Séparation des libellés** : `vps_label` est limité à un motif restreint.

### 9.2 Limites assumées

- Les **notes libres** (`admin_note`, `note`, `reason`) peuvent contenir n'importe quel texte. Aucune expression régulière ne peut garantir l'absence de secret. Les mesures sont : longueur limitée, avertissement visible, formation de l'administrateur, revue périodique et purge sur demande.
- Un administrateur qui copie un secret dans une note reste responsable de cette saisie. La plateforme ne doit pas prétendre l'en empêcher.
- Le VPS et ses secrets restent hors de portée : l'administrateur les gère avec ses procédures existantes.

### 9.3 Journal d'audit

Chaque action d'écriture crée une entrée : acteur, organisation, action, cible, résultat, horodatage. Les résumés avant/après ne contiennent que des identifiants, des énumérations et des montants de capital, jamais de note complète.

---

## 10. Décisions à valider

| # | Décision | Recommandation |
|---|---|---|
| D1 | Propriété des affiliés | `partners` (validé) |
| D2 | Utilisateurs de robots sans compte | Fiches administratives (validé) |
| D3 | Une seule fiche robot active par affilié | Oui |
| D4 | Paramètres réels dans une version démo | Interdit |
| D5 | Paramètres de perte maximale obligatoires en réel | Oui, à confirmer |
| D6 | Double validation des versions réelles | Oui |
| D7 | Doublons `CAPITAL` / `DEMO_CAPITAL` vs capital déclaré | Capital uniquement dans la version |
| D8 | Liste blanche : validation des 12 clés après vérification réelle | **Bloquant, §0** |
| D9 | Seuils d'alerte (valeurs par défaut) | Tableau du §6.2 |
| D10 | Durée de conservation des notes et interventions | À définir avec le juriste |

---

## 11. Tests nécessaires

### 11.1 Schéma et sécurité
- Aucune colonne ni champ de formulaire dont le nom contient `token`, `secret`, `password`, `passwd`, `api_key`, `apikey`, `key_id`, `private`, `credential` (test de schéma).
- Aucune clé de paramètre hors de `parameter_definition` ne peut être enregistrée (test de service et de contrainte).
- `is_secret = true` refusé à la création d'une définition.
- Aucun module `bots` n'importe de client HTTP, de module d'accès au VPS ou de lecteur de fichier de réglages (test d'import).
- Aucune route de commande ou de contrôle de robot (test de routes).

### 11.2 Versions et immuabilité
- Une version `validated` ne peut pas être modifiée, ni par service, ni par requête SQL directe (test de déclencheur).
- Une modification crée une nouvelle version avec un numéro strictement croissant.
- Deux validations simultanées : une seule réussit (test de concurrence).
- Une version `real` sans confirmation, date ou note est refusée à la validation.

### 11.3 Statuts
- Tableau de vérité complet : chaque combinaison (override, versions, déclarations, corrections) produit le statut attendu.
- Une version `draft` ne change jamais le statut.
- Une correction neutralise la déclaration corrigée.
- La réactivation rétablit le statut calculé, et l'historique est conservé.

### 11.4 Permissions
- Test par cellule de la matrice §7.2 : chaque action × chaque rôle, résultat attendu.
- Un `crm_operator` ne peut pas créer de brouillon réel, ni valider, ni déclarer un réel.
- Un `crm_viewer` ne voit pas les données personnelles en clair.
- Un rôle `academy_*` reçoit 403 ou 404 sur toute route CRM.
- Un `partner_advisor` ne voit que ses affiliés assignés.

### 11.5 Déclaration réelle
- Refus si l'auteur n'est pas `crm_admin`.
- Refus sans confirmation explicite.
- Entrée d'audit créée avec le libellé de confirmation.
- Aucun appel réseau pendant la déclaration (test d'isolation réseau).

### 11.6 Alertes
- Chaque seuil est configurable dans ses bornes ; hors bornes refusé.
- Chaque catégorie produit l'alerte attendue, et seulement celle-ci, sur des jeux de dates fixes.
- Une alerte ne crée aucune tâche automatiquement, sauf les deux événements du §1.3.

### 11.7 Relations entre modules
- `partners` n'importe ni `academy` ni `bots` (règle import-linter).
- `academy` et `bots` ne s'importent pas mutuellement.
- Un affilié supprimé logiquement (archivé) reste référencé sans fuite de données.
- Le « dernier contact » combine correctement les interactions des deux modules.

### 11.8 Isolation et données personnelles
- Un utilisateur d'une autre organisation reçoit 404 sur chaque type de ressource.
- Export : journalisé, sans notes, formules CSV neutralisées.
- Les données d'un affilié archivé n'apparaissent plus dans les listes actives.

### 11.9 Bilinguisme
- Parité FR/EN de tous les libellés de statut, de piste, de catégorie d'alerte et de rôle.
- Les noms de paramètres (`STAKE`, etc.) restent identiques dans les deux langues.

### 11.10 Scénarios de bout en bout
- S1 à S14 du §8, en FR et EN, sur jeu de données réaliste.

---

## 12. Prochaines étapes

1. **Vérification des fichiers réels** (§0) : fournir la table `clé | robot | unité | plage | secret ? | source`.
2. Validation des décisions D1 à D10.
3. Seulement ensuite : création des entités `bots` et de la liste blanche, puis formulaires.
