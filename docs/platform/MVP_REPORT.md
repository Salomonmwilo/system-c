# SYSTEM-C Platform : rapport de la première version (MVP)

Date : 2026-11-09 · Code : `platform/` · Référence de conception : `NEW_PROJECT_DIRECTION.md` (révision 3) et `BOT_CRM_SPEC.md`.

Ce rapport distingue ce qui est **terminé et vérifié** de ce qui **reste à faire**. Une fonctionnalité n'est listée comme terminée que si elle est couverte par un test automatisé ou a été vérifiée dans un navigateur.

---

## 1. Vérifications effectuées

| Vérification | Résultat |
|---|---|
| Suite de tests automatisés (`python manage.py test`, PostgreSQL 16) | **108 tests, tous réussis** |
| `manage.py check` | Aucun problème |
| `manage.py check --deploy` avec une configuration de production simulée | 2 avertissements volontaires : HSTS sur les sous-domaines et préchargement HSTS, à activer après choix du domaine |
| `makemigrations --check` | Aucune migration manquante |
| Parcours complet dans Chromium (Playwright) : connexion, tableau de bord, affiliés, fiche, fiche robot, brouillon, validation d'un compte réel, paramètres, bascule EN, mobile | Aucune erreur JavaScript, aucune violation de CSP, aucune réponse 4xx ou 5xx, aucun débordement horizontal sur mobile (iPhone 13) |
| Catalogue français | 473 chaînes, toutes traduites (vérifié par test) |

---

## 2. Fonctionnalités terminées

### 2.1 Socle (`core`)
- Modèle utilisateur personnalisé dès la première migration : connexion par adresse électronique, insensible à la casse, identifiants UUID.
- Mots de passe hachés en Argon2id, politique de 12 caractères minimum.
- Connexion et déconnexion (POST uniquement), messages d'erreur identiques quel que soit le motif.
- Limitation des tentatives : 5 par compte, 20 par adresse IP, 15 minutes de blocage, via le cache en base.
- Organisations, appartenances, rôles multiples par personne, changement d'organisation limité à celles dont on est membre.
- Politique de permissions centralisée, avec refus par défaut. Un test vérifie que **chaque route** déclare sa protection et que chaque page privée redirige un visiteur anonyme.
- Un super-utilisateur Django n'a accès à aucune donnée d'organisation sans rôle.
- Gestion des membres par `org_admin` : création de compte, attribution des rôles. Un administrateur ne peut pas retirer son propre rôle d'administrateur.
- Seuils d'alerte configurables par organisation, avec bornes vérifiées en base et changements journalisés.
- Journal d'audit **en ajout seul, protégé en base** par un déclencheur PostgreSQL. Il ne contient ni note, ni mot de passe, ni token.
- En-têtes de sécurité : CSP stricte sans script ni style en ligne, `X-Frame-Options: DENY`, `nosniff`, `Referrer-Policy`, `Permissions-Policy`, `Cache-Control: no-store` sur les pages privées. Cookies `Secure` et `__Host-` hors développement.
- Interface FR/EN : français par défaut, préférence mémorisée par compte, bascule en un clic, redirections externes refusées.
- Commande `bootstrap_platform` : organisation et administrateur initial.

### 2.2 Partners (propriétaire de la fiche affilié)
- Ajout, modification, archivage et restauration d'un affilié. Les doublons d'adresse sont refusés dans une organisation, et autorisés entre organisations.
- Suivi de l'inscription Deriv, de la vérification et du compte démo : étapes datées, avec source et note. L'historique est **en ajout seul** (déclencheur en base).
- Interactions et notes internes. Le « dernier contact » ignore les notes internes et les contacts plus anciens.
- Relances planifiées, avec échéance, responsable, clôture et liste « à faire ».
- Liens de parrainage (HTTPS uniquement).
- Visibilité : un `partner_advisor` ne voit que les affiliés qui lui sont attribués ; un `crm_viewer` voit les données personnelles masquées.
- Alertes : sans contact, inscription inachevée, vérification inachevée.

### 2.3 Bots (CRM administratif)
- Association d'un affilié à une fiche robot, avec le type DIFFERS ou OVER/UNDER, sans compte de connexion. Une fiche par affilié.
- Versions de configuration : brouillon, puis validation, puis version **immuable**, aussi bien dans le code qu'en base (déclencheurs sur les versions et leurs paramètres). Toute modification crée une nouvelle version, pré-remplie avec la précédente.
- Liste blanche fermée des 12 paramètres, valeurs **numériques uniquement**, bornes configurables. Toute clé inconnue est refusée par le service **et** par une contrainte en base.
- Compte démo ou réel : **seul `crm_admin`** peut préparer, valider, déclarer appliquée ou corriger une configuration réelle. La validation d'un compte réel exige une case de confirmation, une date, une note, et crée une entrée d'audit dédiée. La base refuse aussi une version réelle validée sans ces éléments.
- Déclaration manuelle « appliquée sur le VPS », avec date et note. Elle n'est possible que sur la dernière version validée, jamais à une date future, mais peut être rétroactive. Les corrections se font par ajout, sans rien effacer.
- Pause, désactivation et réactivation, avec motif obligatoire et historique.
- Statuts calculés : À configurer, Configuration appliquée, Modification demandée, En pause, Désactivé. Chaque statut porte la mention « déclaré, non vérifié sur le VPS ».
- Alertes : modification en attente, configuration à revalider.
- **Aucune connexion au VPS ni à Deriv.** Des tests vérifient qu'aucun module réseau ou shell n'est importé, qu'aucune route ne pilote un robot, qu'aucun champ ne porte un nom de secret, et qu'aucune connexion réseau n'a lieu pendant une déclaration de compte réel.

### 2.4 Tableau de bord
Chiffres réels issus de la base, avec liens vers les listes filtrées :
- total des affiliés, dont prospects ;
- affiliés actifs ;
- inscriptions et vérifications en attente ;
- relances à effectuer (dues ou en retard) ;
- utilisateurs de robots ;
- configurations à appliquer ;
- modifications en attente ;
- configurations appliquées et en pause ;
- alertes, avec leurs seuils.

### 2.5 Academy
Structure initiale uniquement : modèles bilingues (programmes, cours, leçons, inscriptions référençant l'affilié) et page d'accueil réservée aux rôles Academy.

### 2.6 Interface
Thème noir et or (palette de l'identité SYSTEM-C) sur Bootstrap 5.3.8, fourni en local. Navigation latérale sur ordinateur, menu escamotable sur mobile. Tableaux adaptatifs, fiches détaillées et badges d'état. Accessibilité : lien d'évitement, champs reliés à leur aide et à leurs erreurs, liens de navigation d’au moins 40 px, mouvement réduit respecté.

---

## 3. Choix par défaut retenus (à confirmer ou modifier)

| Sujet | Choix | Où le changer |
|---|---|---|
| Version de Django | 5.2.19 LTS (supportée jusqu'en avril 2028) | `requirements.txt` |
| Statuts d'un affilié | Prospect, Actif, Inactif. Le « total » exclut les archivés, les « actifs » sont le statut Actif | `partners/models.py` |
| Inscription en attente | Compte Deriv non déclaré créé | `partners/services.py` |
| Vérification en attente | Compte créé et vérification ni validée ni refusée | `partners/services.py` |
| Configurations à appliquer | Statut « À configurer » et « souhaite un robot » | `bots/services.py` |
| Paramètres | Les 12 clés activées pour les deux robots, **toutes marquées « à vérifier »**, minimum 0, pas de maximum, unité vide, toutes facultatives | Page « Paramètres autorisés » (`crm_admin`) |
| Capital | Saisi sur chaque version. Les clés `CAPITAL` et `DEMO_CAPITAL` restent saisissables en attendant la décision D7 | `BOT_CRM_SPEC.md` §10 |
| Devise | USD par défaut | Seuils d'alerte, puis devise par défaut |
| Seuils d'alerte | Contact 30 j, modification 7 j, revalidation 30 j, inscription 7 j, vérification 14 j | Page « Seuils d'alerte » |
| Fuseau horaire | UTC | `TIME_ZONE` dans `.env` |
| Une fiche robot par affilié | Oui (décision D3 recommandée) | `bots/models.py` |
| Double validation des versions réelles | **Non implémentée** (décision D6 ouverte) | Sans objet |
| Administration Django (`/admin`) | Désactivée : elle contournerait l'isolation par organisation | `config/settings.py` |

---

## 4. Limites restantes

### Sécurité
- **Pas de double authentification (TOTP)** pour `platform_admin` et `crm_admin`, alors que la conception la prévoit. C'est la prochaine priorité de sécurité.
- Pas de réinitialisation de mot de passe par courriel, faute de fournisseur de courriel. Un `org_admin` crée les comptes avec un mot de passe initial ; chacun peut ensuite changer le sien.
- Les **notes libres** peuvent techniquement contenir un secret saisi par erreur. La protection repose sur l'absence de champ dédié et sur la liste blanche. Les avertissements visibles sont un rappel, pas une garantie.
- Pas de politiques de ligne PostgreSQL (RLS). L'isolation est assurée par le code, des déclencheurs ciblés et des tests.
- Le verrouillage concurrent (`select_for_update`) est en place mais n'a pas été testé sous charge réelle.

### Fonctionnel
- **La liste blanche n'est pas vérifiée contre les fichiers réels des robots** : ils n'étaient pas accessibles (voir `BOT_CRM_SPEC.md` §0). Tant qu'un paramètre n'est pas vérifié, il reste marqué « à vérifier » dans l'interface.
- Pas de tâches génériques sur les fiches robot : les relances sont rattachées à l'affilié.
- Pas de rappels par courriel ni de notifications.
- Pas d'export CSV ou PDF.
- Academy : aucun écran de création de contenu ni d'espace apprenant.
- Historiques limités aux 50 derniers éléments par fiche, recherche simple par nom ou adresse.

### Exploitation
- Pas de configuration de production livrée (serveur d'application, reverse proxy, sauvegardes).
- Pas de pipeline d'intégration continue : les tests se lancent localement.
- Les vérifications dans le navigateur ont été faites manuellement avec Playwright et ne font pas partie de la suite automatisée.

---

## 5. Prochaines étapes proposées

1. Vérifier les 12 paramètres sur les fichiers réels, sans valeurs, puis marquer « vérifiés » ceux qui sont confirmés, avec leurs unités et bornes.
2. Ajouter la double authentification TOTP pour les rôles administrateurs.
3. Trancher D6 (double validation des comptes réels) et D7 (capital).
4. Mettre en place l'intégration continue (tests sur PostgreSQL) et une configuration de production.
5. Exports CSV journalisés, puis rappels par courriel.
6. Phase Academy : écrans de contenu, import des huit séquences Match/Differs relues.
