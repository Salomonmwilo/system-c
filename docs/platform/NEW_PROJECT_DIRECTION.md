# SYSTEM-C Platform — Nouvelle orientation et architecture cible

Statut : **proposition à approuver**. Aucun code n'est écrit à ce stade. Aucun fichier existant n'est supprimé ni modifié.

Ce document remplace l'orientation « site vitrine » des documents `PROPOSED_ARCHITECTURE.md`, `MIGRATION_PLAN.md` et `IMPLEMENTATION_ROADMAP.md` (voir §10). `CURRENT_STATE.md` et `GAP_ANALYSIS.md` restent valables comme inventaire et diagnostic.

---

## 1. Nouvelle vision du produit

**SYSTEM-C Platform** est une plateforme SaaS multi-utilisateurs et multi-organisations, en français et en anglais, composée de trois modules fonctionnellement indépendants qui partagent l'identité, les profils, les permissions et les services communs.

| Module | Mission | Utilisateurs principaux |
|---|---|---|
| **ACADEMY** | Formation autonome : programmes, cours, leçons, exercices, évaluations, progression | Apprenants, instructeurs, responsables pédagogiques |
| **PARTNERS** | Gestion des personnes orientées par les liens de parrainage, suivi des prospects, des affiliations, de la vérification et des relances | Gestionnaires de partenaires, conseillers, responsables d'affiliation |
| **BOT MANAGEMENT** | Gestion des utilisateurs de robots Deriv et de leurs instances, séparation démo/réel, supervision, rapports, communication sécurisée avec le VPS | Opérateurs, superviseurs, responsables des risques, utilisateurs de robots (accès limité) |

Principes directeurs :
1. **Sécurité par défaut** : refus par défaut, moindre privilège, aucune donnée sensible inutile.
2. **Pédagogie et transparence** : aucune promesse de gain, avertissements de risque visibles, distinction claire entre démo et réel.
3. **Bilingue dès le départ** : toute interface, tout message, tout contenu éditable existe en FR et EN.
4. **Multi-organisation dès le départ** : chaque donnée appartient à une organisation ; aucune requête ne peut lire hors de son périmètre.
5. **Modularité sans microservices** : des modules séparés dans un même déploiement, jusqu'à ce qu'une contrainte réelle justifie de les séparer.

Un point de cadrage à trancher : SYSTEM-C Platform est un outil de **formation et d'exploitation**, pas un service de conseil financier ni un intermédiaire. Le produit ne doit jamais passer d'ordres sur des comptes réels pour le compte de tiers sans cadre réglementaire validé (voir §8).

---

## 2. Éléments de l'ancien dépôt à réutiliser

Réutiliser signifie : récupérer la **donnée ou la décision** (texte validé, identité visuelle, règle métier), pas le code qui la présente.

### 2.1 Identité et branding

| Élément | Source | Usage dans la plateforme | Décision |
|---|---|---|---|
| Nom et slogan | `index.html` (en-tête, pied), `script.js` (`heroTitle`, `metaTitle`) | Nom du produit, « Penser juste. Agir avec discipline. » | Réutiliser (à confirmer pour la plateforme) |
| Devise latine validée | `script.js` (`footerSlogan`) : « Solus cum plenitudine, inopi est alia » | Pied de page des pages publiques | Réutiliser (validée par le responsable) |
| Logo | `public/logo-mark.png` (32 Ko, source 480×279) | En-tête, favicon, icône d'application | Réutiliser, **mais** demander une version vectorielle et haute résolution avant les écrans imprimés ou les rapports |
| Icônes et favicons | `favicon-32.png`, `favicon-192.png`, `apple-touch-icon.png` | Favicons de la plateforme | Réutiliser |
| Palette noir et or | `styles.css` : `--bg #09090a`, `--gold #d7b46a`, `--gold2 #f0d79b`, `--text #f5f1e8`, et les variantes du mode clair | Tokens de design system | Réutiliser les **valeurs**, les reformuler en tokens du nouveau framework |
| Typographie | Georgia (titres), police système (texte) | Idem | Réutiliser, à valider pour les données tabulaires |
| Image de partage | `public/og-image.png` | Aperçus de liens publics uniquement | Réutiliser pour les pages publiques |

### 2.2 Textes institutionnels et mission

| Élément | Source | Décision |
|---|---|---|
| Mission et « Penser juste » | `script.js` (`aboutTitle`, `founderP1`, `founderP2`) | Réutiliser comme base, réécrire en vue de la plateforme |
| Principes « pas de promesses » | `script.js` (`trans1Title` à `trans4Title`) | **Réutiliser tels quels** : ce sont des engagements de transparence |
| Mention d'indépendance | `footerDisclaimer` : « Site de présentation indépendant. Deriv est une marque distincte. » | Réutiliser, adapté en « Plateforme éducative indépendante. Deriv est une marque distincte. » |
| Avertissement de risque officiel | `index.html` ligne 248 (texte anglais, Deriv Affiliates Terms, section 1.10) | **Réutiliser verbatim** en anglais, et traduction française séparée clairement marquée « non officielle ; la version anglaise fait foi » |
| Pages de confidentialité | Textes existants | **À réécrire**, ils décrivent une absence de collecte qui ne sera plus vraie (voir §7.4) |

### 2.3 Traductions FR et EN

- Environ **219 clés** par langue existent dans `script.js` (lignes 1-33). Elles sont en parité (vérifiée). **Réutilisation sélective** : seules les clés qui décrivent les textes institutionnels, les modules pédagogiques et les avertissements sont reprises. Les clés propres au site vitrine (menu, thème, animations, libellés de navigation de la landing) ne sont pas réutilisées.
- Les traductions doivent être sorties du JavaScript et placées dans les catalogues du framework (voir §5.4), avec un contrôle de parité FR/EN en CI.

### 2.4 Contenus pédagogiques

| Élément | Source | Réutilisation |
|---|---|---|
| Huit séquences Match/Differs (titres, objectifs, exercices, FR et EN) | `script.js` (`seq1Title`… `seq8Ex`) | **Premier contenu d'ACADEMY**, à importer comme données et à relire par un responsable pédagogique |
| Six compétences (budget, risque, journal, etc.) | `b1Title`… `b6Desc` | Réutilisable comme objectifs de programme |
| Définitions « trading » et « Deriv » | `defTradingDesc`, `defDerivDesc` | Réutilisable, à valider |
| Versets (Louis Segond, King James) | `verse1`… `verse8` | Réutilisable **si** la source est conforme : vérifier les droits de la traduction Louis Segond avant publication. La King James est dans le domaine public. |
| Parcours en quatre modules (diagramme) | `public/images/module-parcours-*.png` | Réutilisable comme illustration |
| Illustrations digits et proba (FR/EN) | `public/images/module-digits-*`, `module-proba-*` | Réutilisable |
| FAQ et guide Deriv en cinq étapes | `script.js` (`step1Title`…, `faqQ*`) | **À réviser** : contenu daté, dépend de l'interface Deriv, et plusieurs réponses doivent être réécrites |

### 2.5 Logique métier réutilisable comme données

La pré-évaluation (`buildResult`, `script.js` lignes 87-114) contient des règles métier utiles : âge minimum, pays autorisé, document accepté, fonds non essentiels, compréhension du risque. Ces règles sont **réutilisées comme données** : un référentiel de critères d'onboarding (§6.3), versionné, avec ses textes FR/EN. Le code JavaScript qui les évalue n'est pas réutilisé ; la logique est réimplémentée côté serveur, où elle peut être auditée et tracée.

### 2.6 Documentation

- Les cinq documents de `docs/platform/` sont conservés comme historique de l'audit.
- `CURRENT_STATE.md` reste la référence de l'inventaire.
- `GAP_ANALYSIS.md` reste valable, notamment §6 (conformité) et §8 (informations manquantes).

### 2.7 Composants et fonctions réellement réutilisables

Peu de code est réutilisable tel quel, et ce n'est pas un problème. Les seuls éléments à reprendre sont des **idées de conception** :
- le système de tokens CSS (variables, deux thèmes) ;
- la logique d'accessibilité documentée : focus géré après une erreur, `aria-describedby` par question, cibles de 44 px, mention « s'ouvre dans un nouvel onglet », respect de `prefers-reduced-motion` ;
- la politique d'en-têtes de sécurité dans `netlify.toml` (CSP stricte, `frame-ancestors 'none'`, `Referrer-Policy`, `Permissions-Policy`), à réappliquer dans la configuration de l'application.

---

## 3. Éléments à abandonner ou ignorer

| Élément | Raison | Action |
|---|---|---|
| Site vitrine comme produit à maintenir | Hors objectif | Ignorer ; ne pas modifier |
| `netlify.toml`, configuration de publication Netlify | Hors objectif | Ignorer ; conserver le fichier |
| `.github/workflows/pages.yml` (GitHub Pages) | Hors objectif | Ignorer ; conserver le fichier |
| `public/script.js` comme code applicatif | Mélange données, logique et UI ; non modulaire ; non testable | Ne pas réutiliser le code. Extraire seulement les données (§2.3, §2.4) |
| `public/styles.css` comme base de l'interface | Conçu pour une page unique | Ne pas réutiliser les règles ; réutiliser les tokens (§2.1) |
| Formulaire d'éligibilité en HTML | Logique client, réponses non enregistrées | Remplacer par un parcours serveur auditable (§6.3) |
| Lien d'affiliation codé en dur | Doit devenir une donnée gérée | Migrer vers le registre de liens (§6.2) |
| Groupe WhatsApp comme canal d'inscription | Canal non contrôlé pour des données personnelles | **À décider** : retirer de la plateforme, ou le cadrer (§8) |
| Affirmation « carte d'électeur RDC acceptée » | Témoignages non vérifiés, pouvant induire en erreur sur une vérification de compte | **Ne pas réutiliser comme fait.** Remplacer par une source officielle Deriv ou une mention « à confirmer auprès de Deriv » |
| Promesse « rien n'est stocké sur un serveur » | Fausse pour la plateforme | Abandonner ; réécrire la politique de confidentialité |
| Mentions « Approbation Deriv en cours » et « Cohorte Alpha » | Statut éphémère | Ne pas réutiliser |
| `docs/platform/PROPOSED_ARCHITECTURE.md`, `MIGRATION_PLAN.md`, `IMPLEMENTATION_ROADMAP.md` | Orientés vitrine | Marqués « remplacés » (§10) |
| Historique des versions du README (v3 à v9) | Décrit le site vitrine | Conserver, sans en faire la documentation du produit |

---

## 4. Architecture cible recommandée

### 4.1 Choix structurant : un monolithe modulaire

Recommandation : **une seule application backend, découpée en modules Django (ou framework équivalent) à frontières strictes**, avec une base PostgreSQL partagée et, pour le VPS, un agent séparé.

Pourquoi pas des microservices : trois modules, une équipe réduite, des besoins transactionnels communs (permissions, audit, profils). Les microservices ajouteraient des coûts de réseau, d'authentification inter-services, et de cohérence des données, sans bénéfice immédiat.

Pourquoi pas une SPA séparée : le référencement public de certaines pages reste utile, la sécurité des sessions est plus simple côté serveur, et le rendu serveur réduit la surface de code JavaScript.

### 4.2 Schéma

```
   Navigateur (FR/EN)
        │  HTTPS, cookies de session HttpOnly
        ▼
┌─────────────────────────────────────────────────────────────────┐
│  SYSTEM-C Platform (application web, un seul déploiement)       │
│                                                                 │
│  ┌──────────────── core (partagé) ───────────────────────────┐  │
│  │ identité · profils · organisations · rôles · permissions  │  │
│  │ audit · consentements · notifications · i18n · fichiers   │  │
│  └────────────▲────────────────▲────────────────▲────────────┘  │
│   API interne │   API interne  │   API interne  │               │
│  ┌────────────┴───┐ ┌──────────┴─────┐ ┌────────┴───────────┐   │
│  │   academy      │ │   partners     │ │   bots             │   │
│  │ programmes     │ │ liens          │ │ utilisateurs bots  │   │
│  │ cours, leçons  │ │ prospects      │ │ instances          │   │
│  │ exercices      │ │ onboarding     │ │ environnements     │   │
│  │ progression    │ │ relances       │ │ supervision        │   │
│  └────────────────┘ └────────────────┘ │ incidents, rapports│   │
│                                        └────────┬───────────┘   │
└─────────────────────────────────────────────────┼───────────────┘
                 │                                 │ HTTPS sortant,
                 ▼                                 │ requêtes signées
        ┌─────────────────┐                        │ (HMAC + nonce)
        │ PostgreSQL      │                        ▼
        │ (réseau privé)  │          ┌────────────────────────────┐
        └─────────────────┘          │ Agent sur VPS Ubuntu       │
                                     │ lit les bots, publie état  │
        ┌─────────────────┐          │ et rapports ; ne reçoit    │
        │ Stockage objet  │          │ aucun ordre de trading     │
        │ (rapports, pièces│         └──────────────┬─────────────┘
        │ jointes chiffrées)│                       │ fichiers / API locale
        └─────────────────┘                          ▼
                                     ┌────────────────────────────┐
                                     │ Bots Python (Differs,      │
                                     │ Over/Under), API Deriv     │
                                     └────────────────────────────┘
```

### 4.3 Règle de séparation des modules

- Chaque module a son **propre espace de noms** (`academy.*`, `partners.*`, `bots.*`), ses modèles, ses services, ses routes, ses gabarits et ses tests.
- Un module **n'importe jamais les modèles d'un autre module**. Il passe par son interface de service (fonctions publiques) ou par un événement de domaine.
- Vérification automatique en CI (règle d'import, par exemple `import-linter`).
- Le lien entre modules se fait par **identifiants**, pas par clés étrangères croisées. Exemple : une personne « prospect » devient « étudiant » via un événement `partners.lead_enrolled` consommé par `academy`.
- Chaque module peut être désactivé par configuration d'organisation, sans casser les autres.

### 4.4 Organisation et multi-tenancy

- **Organisation** = frontière de données (tenant). Le premier tenant est SYSTEM-C lui-même.
- Toute table métier porte `organization_id`. Aucune requête métier ne s'exécute sans contexte d'organisation résolu côté serveur.
- Une personne peut appartenir à plusieurs organisations avec des rôles différents (`membership`).
- Les **administrateurs de plateforme** sont distincts : ils ont un rôle global, auditable, avec double authentification obligatoire.
- Isolation renforcée en phase de durcissement par les **politiques de ligne PostgreSQL** (RLS), en plus des contrôles applicatifs.

### 4.5 Identité, profils et permissions

Un seul modèle d'identité pour tous les modules :

- `person` : identité de la personne (nom affiché, langue préférée, fuseau horaire, pays de résidence déclaré, statut de vérification de l'âge).
- `user` : compte de connexion, lié à une `person` (un compte peut exister sans être connectable, par exemple pour un utilisateur de bot géré par un opérateur).
- `membership` : appartenance à une organisation avec un ou plusieurs `role`.
- `role` et `permission` : définis par module (`academy.enroll`, `partners.lead.read`, `bots.instance.read_real`, etc.).
- Politique centralisée : une seule fonction d'autorisation appelée par chaque service, **refus par défaut**, avec test automatique qui échoue si une route n'a pas de permission déclarée.

Rôles de départ proposés (à valider) :

| Rôle | Portée | Modules |
|---|---|---|
| `platform_admin` | Globale | Tous (journalisé, MFA obligatoire) |
| `org_admin` | Organisation | Gestion des membres et des paramètres |
| `academy_instructor` | Organisation | Contenu, correction, suivi des apprenants |
| `academy_student` | Soi-même | Parcours, exercices, progression |
| `partner_manager` | Organisation | Liens, prospects, relances, statuts |
| `partner_advisor` | Ses prospects assignés | Suivi et relances |
| `bot_operator` | Instances assignées | Lecture et actions autorisées en démo |
| `bot_risk_approver` | Organisation | Approbation des changements sur réel (phase 6) |
| `bot_viewer` | Rapports autorisés | Lecture seule |
| `bot_user` | Ses propres instances | Lecture de son état et de ses rapports, si accès accordé |

### 4.6 Partage de services communs (`core`)

`core` fournit : identité et authentification, profils, organisations et appartenances, rôles et permissions, journal d'audit, consentements, notifications (courriel et in-app), gestion des fichiers, catalogues de traduction, configuration par organisation, et un **outbox** pour les événements de domaine.

---

## 5. Technologies recommandées

Le dépôt n'impose aucune technologie. Il ne contient ni code serveur, ni dépendance, ni base de données : le choix est donc libre, et guidé par les contraintes du produit.

### 5.1 Critères

1. Sécurité intégrée (sessions, CSRF, hachage de mots de passe, permissions) plutôt qu'à reconstruire.
2. Cohérence avec le langage des bots existants (Python).
3. Support natif de l'internationalisation et des migrations de schéma.
4. Écosystème mature et maintenu ; peu de dépendances tierces.
5. Capacité à fonctionner sur un VPS ou une plateforme managée.

### 5.2 Comparaison résumée

| Option | Points forts | Points faibles | Verdict |
|---|---|---|---|
| **Django (version LTS) + PostgreSQL, rendu serveur** | Authentification, sessions, CSRF, permissions, administration, migrations, i18n (gettext) inclus ; Python comme les bots ; mature | Plus de conventions à respecter ; admin à sécuriser | **Recommandé** |
| FastAPI + SQLAlchemy + Alembic + gabarits | Léger, typage fort, API natives | Authentification, permissions, admin, i18n à construire soi-même : plus de code de sécurité à auditer | Acceptable, mais coût de sécurité plus élevé |
| Next.js / TypeScript + API séparée | Excellente expérience front ; écosystème large | Deux langages, deux déploiements, sécurité de session à consolider ; le savoir-faire Python des bots ne sert pas | Écarté sauf équipe orientée TypeScript |
| Microservices par module | Isolation forte | Complexité opérationnelle disproportionnée | Écarté à ce stade |

### 5.3 Stack recommandée

| Couche | Choix | Justification |
|---|---|---|
| Langage | Python (version stable actuelle, à figer au démarrage) | Cohérence avec les bots ; écosystème sécurité et données |
| Framework web | Django (dernière version LTS à la date de lancement) | Sécurité intégrée, administration, migrations, i18n |
| Base de données | PostgreSQL (16 ou plus récente) | Exigence du produit ; RLS pour l'isolation |
| Rendu et interactions | Gabarits Django, JavaScript minimal ; HTMX seulement si un besoin réel apparaît | Pas de SPA, peu de code client à sécuriser |
| Design system | Tokens CSS issus du branding (§2.1), composants internes | Identité conservée, pas de dépendance graphique lourde |
| Internationalisation | Catalogues gettext (`.po`) pour l'interface ; champs `*_fr` / `*_en` pour les contenus éditables | Standard Django, relecture par traducteur possible |
| Authentification | Authentification Django + sessions serveur ; TOTP (double authentification) pour les administrateurs et les rôles sensibles ; courriel de vérification | Réduit le code de sécurité personnalisé |
| Tâches asynchrones | Commandes de gestion et table de tâches dans PostgreSQL au départ ; file (Redis + worker) seulement si le volume l'exige | Moins de services à exploiter |
| Fichiers | Stockage objet compatible S3, chiffré, accès par URL signée, analyse antivirus des envois | Rapports et pièces jointes hors base |
| Courriel | Fournisseur transactionnel (à choisir) ; gabarits FR/EN | Relances, vérification, réinitialisation |
| Tests | pytest et pytest-django ; Playwright pour les parcours FR/EN ; import-linter pour les frontières de modules ; tests d'isolation dédiés | Chaque règle de sécurité a un test |
| Qualité | ruff, mypy progressif, pre-commit, scan de dépendances, scan de secrets | Réduit les défauts évitables |
| Conteneurs | Image Docker non-root, multi-étapes ; compose pour le développement | Déploiement reproductible |
| TLS et entrée | Reverse proxy avec TLS automatique (Caddy ou équivalent) | En-têtes et renouvellement de certificats |
| Observabilité | Journaux JSON sans données personnelles ; suivi d'erreurs optionnel | Diagnostic sans fuite |

### 5.4 Internationalisation : principes de conception

- La langue est déterminée par : préférence du compte › choix explicite › en-tête `Accept-Language` › français par défaut.
- Chaque courriel, export et rapport est généré dans la langue du destinataire.
- Les formats de dates, de nombres et de montants suivent la locale (fuseau horaire du compte).
- **Les contenus pédagogiques et les avertissements de risque existent dans les deux langues avant publication.** Un contenu sans traduction ne se publie pas.
- Pas de texte en dur dans les gabarits ni dans le code : tout passe par les catalogues.
- Test de parité FR/EN en CI.
- La langue n'est pas un argument de sécurité. En revanche, les messages d'erreur d'authentification sont les mêmes quel que soit le compte, et traduits de façon identique : ils ne doivent révéler ni l'existence d'un compte, ni la raison d'un échec.

### 5.5 Agent VPS

- Paquet Python distinct, sans dépendance lourde, déployé sur le VPS sous un utilisateur système dédié.
- Fonctions : lecture de l'état des bots, génération de rapports, envoi de heartbeats.
- Communication : HTTPS sortant uniquement ; requêtes signées (HMAC-SHA256 sur méthode, chemin, horodatage, nonce et empreinte du corps) ; secret propre à chaque agent ; révocation immédiate ; rejet des requêtes trop anciennes ou rejouées.
- **Aucune commande d'exécution de trading.** L'agent ne reçoit que des configurations validées, et seulement en phase 6.

---

## 6. Modules et responsabilités

### 6.1 `core` (partagé)

Responsabilités : identité, profils, organisations, appartenances, rôles, permissions, audit, consentements, notifications, fichiers, configuration par organisation, traductions, outbox d'événements.

Ne fait pas : aucune logique métier pédagogique, commerciale ou de bots.

### 6.2 `partners`

| Responsabilité | Détail |
|---|---|
| Registre des liens d'affiliation | Libellé, code, pays ciblés, statut, date de dernière revue, responsable |
| Attribution du parrainage | Lien unique par partenaire ; attribution au prospect par jeton signé de courte durée, **sans cookie tiers ni traceur** sans consentement explicite |
| Prospects | Coordonnées, source, pays, consentement daté, finalités, statut |
| Onboarding et vérification | Statuts d'historique : nouveau, contacté, inscription confirmée, vérification en cours, vérifié, démo actif, abandonné, à revoir. **Seul le statut est stocké**, jamais la pièce d'identité |
| Interactions et relances | Journal en ajout seul ; tâches de relance ; canal ; résultat |
| Conformité | Export et suppression d'un prospect ; durée de conservation ; motif de traitement |

Décision à prendre : le **statut de vérification** est une information fournie par Deriv ou saisie par le partenaire. Il faut définir la source de vérité et la procédure de mise à jour (§8).

### 6.3 `academy`

| Responsabilité | Détail |
|---|---|
| Programmes | Titre, description, public, prérequis, durée estimée, langues disponibles |
| Cours et leçons | Ordre, contenu structuré (texte, illustrations, exercices), publication par langue |
| Inscriptions | Statuts : demandé, actif, terminé, suspendu, annulé |
| Pré-évaluation d'admissibilité | Référentiel de critères **versionné** (âge, pays, document, fonds, compréhension du risque), issus de §2.5 ; résultat : favorable, à vérifier, ne pas poursuivre |
| Exercices et évaluations | Types : choix multiple, réponse courte, réflexion guidée ; correction déterministe ; tentatives limitées |
| Progression | Événements horodatés par leçon ; tableau de bord apprenant et instructeur |
| Attestations | Attestation **interne**, mention explicite sans valeur officielle, générée seulement après critères validés |

Points de conception :
- La notation **ne dépend jamais du solde** d'un compte de démo.
- Les contenus réservés aux inscrits ne sont jamais servis dans une page publique (vérifié par test).
- Les avertissements de risque sont affichés avant tout exercice de pratique démo.

### 6.4 `bots`

| Responsabilité | Détail |
|---|---|
| Utilisateurs de bots | Enregistrement géré par un opérateur ; lien optionnel avec un compte de connexion |
| Instances | Type (Differs, Over/Under, extensible), configuration de référence, état |
| Environnements | `demo` et `real` **obligatoires** et étiquetés sur chaque instance ; vues et actions réservées au réel renforcées |
| Identifiants Deriv | **Jamais stockés en clair** : le secret reste sur le VPS ; la plateforme ne garde qu'une empreinte et un libellé (§8) |
| Supervision | Heartbeat, état (en marche, arrêté, erreur, inconnu), dernière activité, latence |
| Incidents | Ouverture, gravité, responsable, actions, clôture ; journal immuable |
| Rapports | Rapports autorisés, filtrés par organisation et rôle, exportables ; aucune donnée d'autres utilisateurs |
| Configuration (phase 6) | Versions immuables ; validation des paramètres par type ; approbation à deux personnes pour le réel |
| Arrêt d'urgence | Interrupteur par instance et global, journalisé |

### 6.5 Interactions entre modules

| Événement | Émetteur | Consommateur | Usage |
|---|---|---|---|
| `partners.lead_qualified` | partners | academy | Proposer une inscription au programme |
| `academy.enrollment_activated` | academy | partners | Mettre à jour le statut d'onboarding |
| `bots.instance_status_changed` | bots | core (notifications) | Alerte aux opérateurs |
| `core.membership_changed` | core | tous | Révoquer les accès en cache |

Les événements passent par l'outbox PostgreSQL (écriture dans la même transaction, publication ensuite). Pas de bus externe au départ.

---

## 7. Fondations techniques nécessaires

### 7.1 Infrastructure de développement
- Dépôt : nouveau dossier applicatif à la racine ou dans `platform/`, sans toucher aux fichiers existants.
- Docker compose : application, PostgreSQL, stockage objet local, courriel de test.
- Environnements : local, préproduction, production. Configuration par variables d'environnement, aucun secret dans le dépôt.
- `.env.example` sans valeurs ; `.gitignore` étendu (`.env`, clés, certificats).

### 7.2 Sécurité de base (phase 1)
- Sessions serveur, cookies `__Host-` (`HttpOnly`, `Secure`, `SameSite=Lax`).
- Hachage Argon2id ; politique de mot de passe ; limitation de débit sur connexion et réinitialisation ; messages d'erreur uniformes.
- Double authentification (TOTP) : obligatoire pour `platform_admin`, `bot_risk_approver`, et toute action sur le réel.
- En-têtes HTTP : CSP stricte (sans `unsafe-inline`), HSTS, `frame-ancestors 'none'`, `Referrer-Policy`, `Permissions-Policy` (reprises de l'ancien `netlify.toml`, §2.7).
- Protection CSRF sur toutes les écritures ; vérification de l'en-tête `Origin`.
- Autoéchappement des gabarits ; interdiction de `|safe` sur les données utilisateur (règle de revue et test).
- Journal d'audit en ajout seul : acteur, organisation, action, cible, résultat, horodatage. Droits PostgreSQL sans `UPDATE` ni `DELETE` pour l'application.

### 7.3 Données et multi-tenancy
- Clés étrangères composites `(organization_id, id)` là où une entité référence une autre entité du même tenant.
- Manager ou requêteur de base qui filtre par organisation ; contournement interdit sauf pour les tâches système journalisées.
- Tests d'isolation pour chaque type de ressource : un utilisateur d'une autre organisation reçoit 404.
- Migrations réversibles pour les ajouts ; expansion puis contraction pour les renommages.

### 7.4 Confidentialité et données personnelles
- Registre des traitements, base légale par traitement, durée de conservation par catégorie.
- Consentement distinct pour chaque finalité (prospection, relance, communication pédagogique).
- Droits d'accès, de rectification et d'effacement : fonctions d'export et de suppression dès la première version qui stocke des données personnelles.
- Minimisation : ne collecter que ce qui sert un parcours ; **ne jamais stocker de pièce d'identité** ni de photo de document.
- Journaux sans données personnelles en clair (adresses courriel masquées ou hachées).
- Sauvegardes chiffrées, rétention définie, procédure de restauration testée.

### 7.5 Intégration des bots
- Protocole de l'agent (§5.5) : signature, horodatage, nonce, révocation, versionnage.
- Inventaire des bots existants (langages, emplacements, formats de journaux, emplacement des identifiants) : préalable à la phase 4.
- Simulation locale de l'agent pour les tests, sans accès à un compte réel.

### 7.6 Qualité et livraison
- CI : tests unitaires, tests d'autorisation, tests d'isolation, parité FR/EN, import-linter, ruff, scan de dépendances, scan de secrets, build d'image.
- Revue de code obligatoire pour les modules `core` et `bots`.
- Documentation d'exploitation : sauvegarde, restauration, révocation d'agent, rotation de secrets, réponse à incident.

---

## 8. Risques de sécurité et de conformité

### 8.1 Sécurité

| # | Risque | Gravité | Mesures |
|---|---|---|---|
| SEC-1 | Vol ou fuite d'identifiants Deriv (jetons d'accès à des comptes financiers) | **Critique** | Secret conservé sur le VPS ; aucune valeur en base ; empreinte seulement ; droits minimaux ; rotation ; test d'absence de secret en base |
| SEC-2 | Ordre passé sur compte réel par erreur ou abus | **Critique** | Lecture seule en phases 1 à 5 ; approbation à deux personnes ; interrupteur d'arrêt ; environnement étiqueté ; journal |
| SEC-3 | Fuite de données entre organisations | Élevée | Isolation applicative et RLS ; tests d'isolation obligatoires ; revue |
| SEC-4 | Compromission d'un compte administrateur | Élevée | TOTP obligatoire ; sessions courtes pour les rôles élevés ; alertes de connexion ; journal |
| SEC-5 | Usurpation d'agent VPS ou rejeu de messages | Élevée | HMAC, horodatage, nonce, révocation, TLS, mTLS envisageable |
| SEC-6 | Injection (SQL, gabarits, commandes) | Élevée | ORM, gabarits à échappement automatique, aucun shell avec entrées utilisateur, validation stricte |
| SEC-7 | Fuite via journaux ou sauvegardes | Moyenne | Journaux sans données personnelles ; chiffrement des sauvegardes ; accès restreint |
| SEC-8 | Dépendances vulnérables | Moyenne | Versions figées, scan automatique, mises à jour régulières |
| SEC-9 | Accès à la base depuis l'extérieur | Élevée | Base sur réseau privé, pas d'exposition publique, comptes applicatifs à droits limités |
| SEC-10 | Téléversement malveillant (rapports, pièces jointes) | Moyenne | Pas de téléversement de pièce d'identité ; type et taille contrôlés ; analyse antivirus ; stockage hors du serveur web |
| SEC-11 | Usurpation de parrainage ou attribution frauduleuse | Moyenne | Jetons signés et courts ; validation côté serveur ; journal d'attribution |
| SEC-12 | Enumération de comptes | Faible | Réponses uniformes, limitation de débit |

### 8.2 Conformité et contenu (à valider avec un juriste et le responsable)

| # | Sujet | Enjeu | Mesure proposée |
|---|---|---|---|
| CONF-1 | Statut des activités de trading automatisé sur comptes réels | Une plateforme qui gère des bots pour des tiers peut relever d'un cadre réglementé selon les pays | Phase 1 à 5 en lecture seule ; aucune exécution d'ordres pour le compte de tiers avant validation écrite |
| CONF-2 | Relation avec Deriv (affiliation, API, conditions d'utilisation) | Les conditions peuvent restreindre le partage de données, la communication et les usages automatisés | Revue des conditions à chaque changement ; clauses dans les documents internes |
| CONF-3 | Public jeune et formation au trading | Risque de mineurs, de pression commerciale, de fausses attentes | Vérification de l'âge déclaré et contrôle du public ; aucun contenu destiné aux mineurs |
| CONF-4 | Promesses et preuves | Témoignages ou affirmations non vérifiés (ex. carte d'électeur RDC) | Aucun témoignage ou statistique sans source vérifiée ; retrait de l'affirmation non sourcée |
| CONF-5 | Données personnelles (RGPD et équivalents) | Prospection, relance, profilage possibles | §7.4 ; registre ; DPIA si profilage |
| CONF-6 | Avertissements de risque | Obligatoires et doivent être lisibles | Texte officiel en anglais, traduction distincte ; affichage avant tout accès à la pratique |
| CONF-7 | Attestations | Risque de confusion avec une certification | Mention « interne, sans valeur officielle » sur chaque attestation |
| CONF-8 | Transferts internationaux | Données stockées ou traitées hors de la zone de résidence | Choix d'hébergement documenté ; clauses contractuelles |
| CONF-9 | Droit de la marque | Usage du nom et du logo Deriv | Mention de distinction ; pas de logo Deriv sans autorisation |
| CONF-10 | Versets religieux | Droits de traduction selon l'édition | Vérifier la source avant publication |

---

## 9. Feuille de route de construction progressive

Chaque phase a un **critère de sortie vérifiable**. Aucune phase ne commence sans approbation de la précédente. Les estimations sont pour une personne à temps plein et indicatives.

### Phase 1 — Fondations (3 à 4 semaines)
**Objectif** : une application vide mais sûre, bilingue, multi-organisation, testée.

- Squelette du projet, Docker, PostgreSQL, CI, tests, import-linter.
- Identité : comptes, sessions, mots de passe, TOTP pour les rôles sensibles, réinitialisation.
- Organisations, appartenances, rôles, politique d'autorisation avec refus par défaut.
- Journal d'audit.
- Internationalisation : langue par compte, catalogues FR/EN, parité en CI.
- Design system minimal : tokens issus de §2.1, gabarits de base, pages de connexion et de profil.
- Politique de confidentialité et mentions légales réécrites (brouillon).

**Critère de sortie** : tests d'authentification et d'isolation verts ; FR et EN complets sur les écrans existants ; déploiement de test réussi ; revue de sécurité interne.

### Phase 2 — ACADEMY (4 à 6 semaines)
**Objectif** : formation autonome de bout en bout.

- Programmes, cours, leçons (modèle bilingue), import des huit séquences Match/Differs après relecture pédagogique.
- Inscriptions et statuts.
- Pré-évaluation d'admissibilité (référentiel versionné, §6.3).
- Exercices, évaluations, progression.
- Attestation interne (mention explicite).
- Tableaux de bord apprenant et instructeur.

**Critère de sortie** : parcours complet d'un apprenant en FR et EN ; isolation testée ; aucune donnée d'un apprenant visible par un autre ; contenus validés par le responsable pédagogique.

### Phase 3 — PARTNERS (3 à 5 semaines)
**Objectif** : suivi des prospects et des liens, sans traceur non consenti.

- Registre des liens d'affiliation ; attribution par jeton signé.
- Prospects, consentements, statuts d'onboarding (sans pièce d'identité).
- Journal des interactions et relances.
- Export et suppression ; durée de conservation.
- Passage d'un prospect qualifié vers ACADEMY (événement).

**Critère de sortie** : validation juridique écrite avant mise en production ; tests de consentement ; export et suppression vérifiés ; aucune donnée de prospect dans les journaux.

### Phase 4 — BOT MANAGEMENT en lecture seule (5 à 7 semaines)
**Objectif** : superviser les bots sans rien modifier à distance.

- Inventaire des bots existants (préalable bloquant).
- Modèle : utilisateurs de bots, instances, types (Differs, Over/Under), environnements démo et réel.
- Agent VPS signé : heartbeats, états, rapports.
- Supervision, incidents, rapports autorisés.
- Aucun identifiant Deriv n'est saisi ni stocké dans la plateforme en phase 4 : l'agent utilise ses propres secrets locaux. La question des empreintes (§8, SEC-1) ne se pose donc qu'en phase 5.

**Critère de sortie** : requête non signée, rejouée ou révoquée refusée (tests) ; aucun secret en base (test de schéma) ; supervision fiable sur un bot de démonstration ; revue de sécurité du protocole.

### Phase 5 — BOT MANAGEMENT : configuration et démo (4 à 6 semaines)
**Objectif** : configurer des instances sur l'environnement démo, avec traçabilité.

- Configurations versionnées et immuables ; validation par type de bot.
- Application par l'agent seulement sur signature valide et version croissante ; retour arrière.
- Interrupteur d'arrêt d'urgence.
- Actions sur le démo uniquement.

**Critère de sortie** : tests de bout en bout sur démo ; refus automatique de toute action réelle ; journal complet.

### Phase 6 — Réel, sous conditions (à décider)
**Objectif** : permettre des actions sur comptes réels **seulement** si le cadre est validé.

- Approbation à deux personnes ; rôle `bot_risk_approver` avec TOTP.
- Limites de risque configurables (mise maximale, pertes maximales) appliquées côté agent.
- Revue de sécurité externe.

**Critère de sortie** : validation juridique écrite ; test d'intrusion sans constat critique ; procédure d'arrêt testée. **Cette phase n'est pas engagée par défaut.**

### Phase 7 — Durcissement et exploitation (3 à 4 semaines)
- Politiques de ligne PostgreSQL (RLS) pour l'isolation.
- Test d'intrusion de l'application et de l'agent.
- Sauvegardes chiffrées, restauration testée.
- Observabilité : tableaux de bord techniques, alertes sur authentifications échouées et rejets d'agent.
- Procédures d'exploitation et de réponse à incident.

**Critère de sortie** : aucun constat critique ouvert ; restauration validée ; procédures relues.

### Calendrier indicatif

| Phase | Durée | Cumul |
|---|---|---|
| 1 | 3 à 4 semaines | 3 à 4 |
| 2 | 4 à 6 semaines | 7 à 10 |
| 3 | 3 à 5 semaines (parallélisable avec la fin de 2 après validation juridique) | 9 à 14 |
| 4 | 5 à 7 semaines | 14 à 21 |
| 5 | 4 à 6 semaines | 18 à 27 |
| 6 | Non engagée par défaut | — |
| 7 | 3 à 4 semaines | 21 à 31 |

Le contenu pédagogique (cours, exercices, évaluations, traductions relues) est souvent le goulot d'étranglement réel. À estimer séparément.

---

## 10. Mise à jour des documents existants

Pour éviter les contradictions, les trois documents suivants sont marqués « remplacés » en tête : `PROPOSED_ARCHITECTURE.md`, `MIGRATION_PLAN.md`, `IMPLEMENTATION_ROADMAP.md`. Leur contenu historique est conservé. `CURRENT_STATE.md` et `GAP_ANALYSIS.md` restent valables.

---

## 11. Décisions qui nécessitent votre approbation

Classées par ordre d'urgence. Les décisions 1 à 4 bloquent la phase 1.

1. **Framework** : Django (recommandé) ou FastAPI. Cette décision conditionne toute la structure du code.
2. **Hébergement de la plateforme** : VPS Ubuntu existant (conteneurs, base sur réseau privé, utilisateur dédié) ou plateforme managée. Recommandation : séparer la plateforme du VPS des bots dès que possible ; accepter le VPS seulement pour la préproduction.
3. **Nom de domaine et sous-domaine** de la plateforme.
4. **Périmètre des comptes** : les utilisateurs de bots sont-ils des comptes de connexion ou des fiches gérées par un opérateur ? (Recommandation : fiches gérées par défaut.)
5. **Identifiants Deriv** (bloque la phase 4) : confirmer que la plateforme **ne stocke aucun jeton**, que le secret reste sur le VPS, et que seules des empreintes sont conservées. Vérifier les conditions d'API Deriv et les portées disponibles.
6. **Canal WhatsApp** : le retirer de la plateforme, ou le cadrer par une politique écrite.
7. **Réel** : confirmer que la phase 6 n'est pas engagée sans validation juridique écrite.
8. **Validation juridique** : affiliation, données de prospects, public visé, pays cibles, statut des bots.
9. **Source de vérité du statut de vérification Deriv** (phase 3) : fournie par Deriv, saisie par le partenaire, ou les deux.
10. **Contenus** : responsable pédagogique désigné pour relire les huit séquences en FR et EN.
11. **Droits** : vérifier la source de la traduction Louis Segond avant publication, et la question des photos du fondateur (consentement et usage).
12. **Canal de communication avec les apprenants** et politique de rétention.
13. **Fournisseur de courriel transactionnel** et fournisseur de stockage objet.
14. **Langue par défaut** et stratégie de repli (français par défaut, `Accept-Language`).
15. **Premier tenant** : SYSTEM-C seul, ou ouverture à d'autres organisations dès la phase 1 (recommandation : architecture prête, ouverture après phase 3).

---

## 12. Prochaine action proposée

Après approbation des décisions 1 à 4 : créer le squelette de la phase 1 dans un dossier séparé, sans toucher aux fichiers existants, puis démarrer les tests d'authentification et d'isolation **avant** les écrans.
