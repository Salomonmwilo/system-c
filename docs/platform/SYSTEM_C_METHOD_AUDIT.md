# SYSTEM-C Method : audit de validation des phases A et B

Date : 2026-11-11. Branche `claude/zealous-fermi-lxtqkl`.
Périmètre : le code réellement présent dans le dépôt après les commits `9af2253` (phase A), `5db5a83` (phase B), `b2adf0e` et `3656b91` (administration Django), comparé à l'état précédent `fabaac4`.

Méthode :
1. une suite de tests complète lancée avant toute modification ;
2. une sonde jetable qui reproduit chaque défaut supposé sur le code d'origine ;
3. une lecture du code ;
4. des corrections limitées aux défauts constatés ;
5. de nouveaux tests, dont un contrôle par mutation ;
6. des migrations rejouées sur une base vierge, sur une copie conforme à votre poste et sur la base de développement existante.

Aucune fonctionnalité commerciale nouvelle n'a été ajoutée. Aucune donnée n'a été effacée.

## Verdict

Les phases A et B, telles que livrées, **n'étaient pas valides**. Un test de sécurité existant échouait. L'administration Django réactivée contournait l'isolation entre organisations. Une commande remboursée conservait son accès payant. Plusieurs exigences du cahier des charges n'avaient pas de support dans le modèle de données : devise, lien entre ressources et offres, langue, version et visibilité des ressources.

Après correction, les fondations sont saines et vérifiées : 147 tests passent, dont 33 pour academy, et les règles critiques sont aussi garanties par PostgreSQL. La recommandation figure à la fin du document.

## 1. Fichiers créés ou modifiés

### Livrés par les phases A et B (commits précédents)

| Fichier | État après l'audit |
|---|---|
| `apps/academy/models.py` | Réécrit (voir §5 et §6) |
| `apps/academy/migrations/0002_extend_academy_for_commerce.py` | Conservé tel quel : il est déjà appliqué sur votre poste |
| `apps/academy/admin.py` | **Supprimé** (problème P1) |
| `apps/academy/management/commands/seed_system_c_method.py` | Réécrit (P9, P13) |
| `apps/academy/tests.py` | Réécrit (P11) |
| `config/urls.py`, `config/settings.py` | Administration Django retirée ; réglage des fichiers privés ajouté |

### Ajoutés par l'audit

| Fichier | Rôle |
|---|---|
| `apps/academy/access.py` | Règle d'accès aux ressources, évaluée côté serveur |
| `apps/academy/migrations/0003_rename_fields.py` | Renommages sans perte : `price_usd` devient `price` avec une devise, `resource_type` devient `category`, `file_path` devient `file`, `user` devient `actor` |
| `apps/academy/migrations/0004_integrity_and_resource_fields.py` | Nouveaux champs et contraintes (générée par Django) |
| `apps/academy/migrations/0005_reshape_seeded_content.py` | Remise en forme du contenu créé par l'ancienne commande, uniquement sur les textes d'origine exacts |
| `apps/academy/migrations/0006_integrity_triggers.py` | Protections en base (déclencheurs PostgreSQL) |
| `.gitignore`, `platform/.env.example` | Dossier `private_media/` ignoré ; variable `SYSTEMC_PRIVATE_MEDIA_ROOT` documentée |
| `locale/translate_fr.py`, `locale/fr/LC_MESSAGES/django.po` et `.mo` | 44 nouvelles chaînes traduites, une reformulée |
| `platform/README.md` | Commande `seed_system_c_method`, fichiers privés, administration désactivée |

### Passe de texte (tirets longs et marques de texte généré)

Fait avec la skill `unslop` du projet, passe « Texte ».
- **Gabarits :** 11 gabarits de `bots`, `partners`, `core` et `templates/includes`. Le tiret long servait de valeur vide ; il est remplacé par un libellé traduit et précis : « Non renseigné », « Pas encore choisi », « Jamais déclarée », « Pas encore validée », « Non identifié », « Aucun ». Un lecteur d'écran annonçait auparavant « tiret cadratin ». Les notes séparées par un tiret passent sur leur propre ligne.
- **Plages de valeurs :** les plages écrites avec un tiret court deviennent « de 7 à 180 ».
- **Documents :** `docs/platform/*.md` et `README.md`, environ 100 occurrences. Titres avec deux-points, cellules vides nommées, phrases reformulées une à une.
- **Ce qui reste :** il ne reste aucun tiret long ni court dans le projet actif. `public/` et les skills tierces ne sont pas modifiés, conformément à `CLAUDE.md`. Aucun émoji, point d'exclamation ni mot publicitaire n'a été trouvé dans l'interface.
- **Pas de nouvelle skill :** aucune autre skill n'a été installée. Les quatre skills du projet viennent de GitHub ; elles ont été choisies et vérifiées lors des passes précédentes (voir `.claude/skills/SOURCES.md`). En ajouter une autre aurait signifié exécuter des instructions tierces non relues.

## 2. Modèles et relations

```
Organization (core)
└── Program ─────────────────────────── catalogue
    ├── Course (une étape) ── Lesson ── contenu pédagogique
    ├── Resource ──┐                    contenu pédagogique (fichier privé ou adresse)
    │              │ incluse dans (M2M, même programme)
    └── ProgramOffer ┘ ─────────────── offres (prix + devise)
          └── Order ── OrderAudit ──── commandes (historique en ajout seul)
                └── Enrollment ─────── droits d'accès (au plus une par commande)
                      └── LessonProgress   progression
Enrollment.affiliate → partners.Affiliate (référence seule, aucune copie)
```

Comportements de suppression :

| Relation | Comportement | Justification |
|---|---|---|
| Program → Organization | PROTECT | Une organisation n'emporte jamais un programme |
| Course, Lesson, Resource, ProgramOffer → parent | CASCADE | Un programme sans inscription ni commande peut être retiré avec son contenu |
| Order → offre, acheteur, organisation | PROTECT | Une offre commandée ne peut pas disparaître |
| OrderAudit → Order, acteur | PROTECT (auparavant CASCADE et SET_NULL) | L'historique ne disparaît pas avec la commande |
| Enrollment → Order | PROTECT (auparavant SET_NULL) | Une inscription garde sa provenance |
| Enrollment → programme, offre, affilié, utilisateur | PROTECT | Inchangé |

L'identité d'un affilié reste dans `partners`. Un test vérifie qu'`Enrollment` ne porte aucun champ d'identité (nom, adresse, téléphone) et qu'un affilié d'une autre organisation est refusé.

## 3. Migrations vérifiées

| Vérification | Résultat |
|---|---|
| `python manage.py makemigrations --check --dry-run` | `No changes detected` : les migrations décrivent exactement les modèles |
| `0002` (écrite à la main) comparée aux modèles de la phase A | Conforme : aucun écart détecté avant correction |
| Base vierge (base de test créée par `manage.py test`) | Les 6 migrations academy et celles des autres modules s'appliquent ; 147 tests passent ensuite |
| Copie conforme de votre poste | Base temporaire créée avec le code de `3656b91`, remplie par l'ancienne commande, plus une commande payée, une ligne d'historique et une inscription ; puis migrée avec le nouveau code. La commande garde 29,00 et reçoit USD. L'historique garde son auteur. Les titres d'étape, les leçons et les ressources sont remis en forme. Cette base temporaire a ensuite été supprimée. |
| Base de développement existante | Migrée de `0001` à `0006`. Comptage de toutes les tables avant et après : identique (61 entrées d'audit, 6 affiliés, 4 fiches robot, etc.) |
| Test automatisé `MigrationTests` | Revient à `0002`, crée des données à l'ancienne, migre jusqu'à `0006`, vérifie chaque transformation. Le chemin inverse est donc lui aussi exercé. |

Objets présents en base après migration :
- **8 contraintes de vérification ou d'unicité :** prix non négatifs, ressource publiée avec fichier ou adresse, date de publication, leçon publiée avec contenu, une inscription par commande, etc.
- **10 déclencheurs academy :**
  - `academy_*_parent_guard` (×4) : un programme ne change pas d'organisation, une étape, une offre ou une ressource ne change pas de programme ;
  - `academy_lesson_guard` ;
  - `academy_order_guard` : organisation de l'offre ; organisation, acheteur, offre, prix et devise immuables ; seule une commande en brouillon peut être supprimée ;
  - `academy_orderaudit_append_only` ;
  - `academy_enrollment_guard` : programme, offre, commande (même acheteur, même offre) et affilié de la même organisation ;
  - `academy_resource_offer_guard` ;
  - `academy_progress_guard`.

## 4. Tests exécutés

| Moment | Commande | Résultat |
|---|---|---|
| Avant toute modification | `python manage.py test` | **128 tests, 1 échec** : `RouteProtectionTests.test_every_route_declares_its_protection` (64 routes `/admin/` sans permission déclarée) |
| Sonde sur le code d'origine | test jetable, supprimé ensuite | 8 défauts reproduits (voir §5) |
| Après correction | `python manage.py test apps.academy` | 33 tests, OK |
| Après correction | `python manage.py test` | **147 tests, OK** |
| Contrôle par mutation | retrait volontaire de la condition « commande payée » dans `access.py` | 5 sous-tests échouent, puis le fichier est restauré : les tests détectent bien le défaut |

Le projet comptait 114 tests avant la phase A, et non 108 : ils passent tous. Les 33 tests academy couvrent :

| Domaine | Ce qui est vérifié |
|---|---|
| Accès | Ressource gratuite sans compte. Achat sans fiche affilié ni robot. Aucun accès pour une commande en brouillon, en attente ou à vérifier. Complete n'ouvre pas Guided, Starter n'ouvre pas Complete. Annulation, remboursement, expiration et suspension retirent l'accès, et l'historique d'inscription reste en place. Une inscription dans une autre organisation ne donne rien. |
| Intégrité des commandes | Prix et devise figés à la commande. Organisation de l'offre imposée. Suppression limitée aux brouillons. Historique en ajout seul, en Python et en base. Inscription conforme à sa commande. Une inscription par commande. |
| Intégrité du contenu | Pas de publication sans fichier ni adresse. Date de publication posée automatiquement. Pas de leçon publiée sans contenu. Pas de lien vers l'offre d'un autre programme. Les parents ne changent pas. La progression reste dans le programme de l'inscription. |
| Fichiers privés | Stockage privé utilisé par le champ. Écriture dans la racine privée. Aucune adresse publique (`url()` refusé). 404 sur `/`, `/media/`, `/static/` et `/academy/`. Racine hors de `static/` et des applications, ignorée par Git. |
| Sécurité et isolation | Aucun champ de type jeton, mot de passe, carte, IBAN ou identifiant de compte. Administration Django absente (`/admin/` répond 404). L'accueil Academy ne montre que les programmes de l'organisation courante. Un rôle sans permission Academy reçoit 403. |
| Commande d'initialisation | Structure créée sans contenu inventé. Rejouable, sans écraser une retouche manuelle. Aucun tiret long dans les textes créés. |
| Migrations | Voir §3. |

La vérification « chaque route déclare sa permission » et le test des redirections anonymes, déjà présents dans `core`, couvrent la route Academy.

## 5. Problèmes découverts

Sévérité : 4 critique, 3 majeur, 2 mineur.

| N° | Sév. | Problème | Preuve |
|---|---|---|---|
| P1 | 4 | **Administration Django réactivée.** La décision `MVP_REPORT.md` §95 la désactivait parce qu'elle contourne l'isolation. Un super-utilisateur y voyait les commandes de toutes les organisations. Les actions « vérifier le paiement », « rembourser » et « annuler » n'exigeaient ni rôle de la plateforme, ni organisation, ni référence, ni note. Le test de protection des routes échouait. | Sonde : « superuser sees orders of an organization it does not belong to : DEFECT » ; échec du test existant |
| P2 | 4 | Une commande de l'organisation B pouvait viser l'offre de l'organisation A | Sonde : « cross-org order accepted : DEFECT » |
| P3 | 4 | Une commande remboursée, annulée ou en attente laissait l'inscription donner accès (`is_access_valid` ignorait la commande) | Sonde : « refunded order keeps access : DEFECT » |
| P4 | 3 | Prix modifiable après commande, et aucune devise : le champ s'appelait `price_usd` | Sonde : « price editable after order », « order has no currency field » |
| P5 | 3 | Historique des commandes modifiable, supprimable, et supprimé en cascade avec la commande ; aucun champ de référence de transaction | Sonde : « order audit editable/deletable : DEFECT » |
| P6 | 3 | Ressource publiable sans fichier ni adresse. Absence de la langue, de la version, de la date de publication, de la visibilité et des catégories exigées. | Sonde : « resource published without file : DEFECT » |
| P7 | 3 | Aucun lien entre ressource et offre : impossible d'établir que Complete n'ouvre pas Guided | Sonde : « resource has no offer link » |
| P8 | 3 | Fichiers enregistrés dans `platform/` (le code source), non ignorés par Git : un document payant pouvait être commité et publié avec le dépôt | Sonde : emplacement `/home/user/system-c/platform` |
| P9 | 3 | Contenu : la phrase d'une ligne de chaque leçon était stockée comme **contenu**, donc présentée comme rédigée. 15 leçons pour 25 objectifs. Tirets longs et capitales dans les titres. Descriptions inventées (« 7 points à vérifier »). Ressources Starter (guide introductif, journal simplifié) et exercices absents. | Lecture de la commande et de la base |
| P10 | 3 | Inscription : aucune cohérence imposée avec le programme, l'offre, la commande ou l'affilié ; plusieurs inscriptions possibles par commande ; provenance perdue (SET_NULL) | Lecture du modèle, tests ajoutés |
| P11 | 2 | Tests de la phase B : 14 tests (le message de commit en annonçait 17) ; aucun test d'accès, d'isolation par organisation ou de protection en base ; un `assertRaises(Exception)` trop large | Lecture |
| P12 | 2 | Libellés et statuts nouveaux non traduits. Le test de traduction passait uniquement parce que le catalogue n'avait pas été régénéré. | `makemessages` : 45 chaînes sans traduction |
| P13 | 2 | Commande d'initialisation en anglais, avec coches, non rejouable : elle s'arrêtait si le programme existait | Lecture |
| P14 | 2 | Commits poussés sans lancer la suite de tests, contrairement à `CLAUDE.md` | Le test en échec au départ |

## 6. Corrections effectuées

| N° | Correction |
|---|---|
| P1 | `django.contrib.admin` retiré des réglages et des URL ; `academy/admin.py` supprimé ; test `AdminSiteTests` ajouté. Les écrans de gestion seront des vues de la plateforme, filtrées par organisation et protégées par permission (phases C et D), comme partners et bots. |
| P2, P10 | Déclencheurs `academy_order_guard` et `academy_enrollment_guard` ; contrainte « une inscription par commande » ; PROTECT au lieu de SET_NULL |
| P3 | `Enrollment.is_access_valid()` et `access.active_enrollments()` exigent une commande payée et confirmée quand l'inscription en a une |
| P4 | Champs `price` et `currency` (code ISO validé, USD par défaut) sur l'offre et la commande. Copie depuis l'offre à la création. Immuabilité garantie en base. |
| P5 | `OrderAudit` en ajout seul (Python et déclencheur), PROTECT, champs `actor` et `reference` |
| P6 | Champs `category`, `language`, `version`, `visibility`, `published_at` ; contraintes « publiée avec contenu » et « publiée avec date » |
| P7 | Lien `Resource.offers`, limité aux offres du même programme (déclencheur) ; règle dans `access.py` |
| P8 | Stockage `PrivateStorage` sans URL publique, dans `SYSTEMC_PRIVATE_MEDIA_ROOT` (par défaut `platform/private_media/`, ignoré par Git) |
| P9 | Champs `summary_fr` et `summary_en` et indicateur `is_published` sur la leçon. La migration 0005 déplace les phrases d'origine dans le résumé. La commande crée les 25 objectifs du cahier des charges et les ressources manquantes, en brouillon. |
| P11 | 33 tests ciblés (voir §4) |
| P12 | Catalogue régénéré, 44 traductions ajoutées et une reformulée, test de traduction vert sur le catalogue réel |
| P13 | Commande en français, rejouable, qui n'écrase jamais une retouche |
| P14 | Suite complète lancée avant ce commit : 147 tests, OK |

## 7. Risques encore ouverts

| Risque | Conséquence | Traitement proposé |
|---|---|---|
| **Aucun chemin de confirmation de paiement** depuis le retrait de l'administration | Impossible de confirmer une commande aujourd'hui. C'est voulu, en attendant un service correct. | Phase C : un service réservé à un rôle autorisé, avec référence et note obligatoires, qui écrit `OrderAudit` et le journal d'audit et active l'inscription dans la même transaction |
| Les transitions de statut d'une commande ne sont pas encadrées (un modèle accepte « remboursée » vers « payée ») | Dépend du code qui modifiera le statut | Phase C : table des transitions autorisées dans le service, testée |
| Aucune permission de gestion Academy (`academy.view` seulement) | Personne ne peut encore gérer offres, ressources et commandes dans l'interface | Phase C : `academy.manage_content`, `academy.manage_offers`, `academy.verify_payment` |
| Aucune vue de téléchargement | Les fichiers privés ne sont servis nulle part : c'est sûr, mais pas encore utilisable | Phase C ou D : vue qui appelle `can_access_resource` puis sert le fichier |
| Ressource payante avec une adresse externe (vidéo hébergée ailleurs) | L'adresse peut être partagée par un acheteur | Décision D4 ci-dessous |
| Inscription sans commande (attribution manuelle) active | Donne accès sans paiement | Phase C : attribution réservée à un rôle, motif obligatoire, auditée |
| Guided peut techniquement être publiée | Contraire au cahier des charges tant que l'accompagnement n'est pas organisé | Phase D : publication soumise à une confirmation ; règle à décider |
| Repli de traduction | Si l'anglais manque, le titre ou le résumé s'affiche en français | `Lesson.has_english_content` existe pour signaler l'absence ; à afficher en phase D |
| Texte libre (`transaction_ref`, `notes`) | Une donnée bancaire peut y être collée par erreur | Aide affichée ; pas de détection par expression régulière, conformément à votre principe. Former l'équipe. |
| Compte super-utilisateur créé sur votre poste | Sans effet : la plateforme ignore ce statut (`permissions.py`) | Le garder ou le supprimer, au choix |
| Avertissement `xgettext` sur « Configuration to review » (module bots) | Antérieur à ce travail, sans effet visible | À traiter lors d'une prochaine passe sur bots |

## 8. Contenu pédagogique réellement disponible

État après `seed_system_c_method` (programme non publié) :

| Étape | Leçons | Titre FR/EN | Résumé FR/EN | Contenu rédigé | Publiée |
|---|---|---|---|---|---|
| 1. Comprendre | 5 | Oui | Oui, une phrase | Non | Non |
| 2. Préparer | 5 | Oui | Oui, une phrase | Non | Non |
| 3. Décider | 5 | Oui | Oui, une phrase | Non | Non |
| 4. Documenter | 5 | Oui | Oui, une phrase | Non | Non |
| 5. Évaluer | 5 | Oui | Oui, une phrase | Non | Non |

Classement demandé :
- **Contenu pédagogique réellement rédigé :** 0 leçon sur 25.
- **Titre et résumé de l'objectif :** 25 leçons sur 25, en français et en anglais.
- **Contenu provisoire présenté comme rédigé :** 0 depuis la correction. Avant, 15 leçons portaient leur résumé dans le champ du contenu.

Les résumés reprennent les objectifs du cahier des charges. Aucun ne contient d'affirmation financière, de stratégie ni de promesse.

Ressources :

| Ressource | Catégorie | Offres | Fichier | Statut |
|---|---|---|---|---|
| Guide principal SYSTEM-C Method | Guide | Complete, Guided | Absent | Brouillon |
| Guide introductif | Guide | Starter | Absent | Brouillon |
| Journal de suivi sur 30 jours | Journal | Complete, Guided | Absent | Brouillon |
| Journal simplifié | Journal | Starter | Absent | Brouillon |
| Feuille de gestion du capital et du risque | Feuille de risque | Les trois | Absent | Brouillon |
| Checklist avant une décision | Checklist | Les trois | Absent | Brouillon |
| Plan d'apprentissage de quatre semaines | Plan | Complete, Guided | Absent | Brouillon |
| Vidéo d'introduction | Vidéo | Starter | Absente | Brouillon |
| Exercices et feuilles de réflexion | Exercice | Complete, Guided | Absent | Brouillon |
| 7 questions à se poser avant une décision de trading | Découverte | Gratuite | Absent | Brouillon |

Aucun fichier n'existe. Les 6 à 8 mini-vidéos de l'offre Complete ne sont pas créées : une fiche par vidéo sera ajoutée quand la vidéo existera. Aucune ressource ne peut être publiée sans fichier ni adresse (contrainte en base).

Offres : Starter Kit (9,00 USD), Complete (29,00 USD), Guided (79,00 USD), toutes en brouillon et modifiables. Le contenu numérique de Guided est celui de Complete ; ses ateliers et son groupe ne sont pas des ressources.

## 9. Fonctionnalités restant à développer

- **Phase C :**
  - permissions de gestion Academy ;
  - service de commande : création, prix figé, transitions autorisées ;
  - service de confirmation manuelle d'un paiement (rôle, référence, note, audit, activation de l'inscription dans la même transaction) ;
  - annulation et remboursement ;
  - attribution et suspension manuelles d'un accès ;
  - vue de téléchargement protégée.
- **Phase D :**
  - écrans de gestion filtrés par organisation : programmes, étapes, leçons, ressources, offres, commandes, inscriptions, progression ;
  - pages « Mes programmes », programme et leçon ;
  - page publique de présentation.
- **Phase E :**
  - ressource gratuite « 7 questions » ;
  - formulaire de contact avec consentement distinct, désinscription et preuve du consentement.
- **Phase F :**
  - pages juridiques provisoires, avec la version des conditions acceptée enregistrée sur la commande (champ à ajouter en phase C) ;
  - tests de parcours dans le navigateur, sur ordinateur et téléphone.

## Décisions attendues de votre part

| N° | Décision | Bloque |
|---|---|---|
| D1 | Quel rôle confirme un paiement : `crm_admin`, `org_admin` ou un nouveau rôle (par exemple `academy_manager`) ? | Le service de confirmation (phase C) |
| D2 | Après un remboursement, l'accès est retiré immédiatement : c'est la règle en place. La confirmez-vous ? | La politique de remboursement |
| D3 | Accès à vie ou limité dans le temps (champ `access_until` déjà prévu) ? | Les inscriptions |
| D4 | Hébergement des vidéos : fichiers privés servis par la plateforme, ou hébergeur externe avec accès restreint ? | Les mini-vidéos |
| D5 | Starter reçoit-il la même checklist que Complete ou une version courte ? La vidéo d'introduction est-elle aussi dans Complete ? (Le cahier des charges ne la cite que pour Starter.) | Le rattachement des ressources |
| D6 | Prestataire de paiement | Le paiement en ligne, pas la phase C manuelle |

## Recommandation

**La phase C peut commencer.** Les défauts constatés sont corrigés et couverts par des tests, le modèle de données porte toutes les exigences du cahier des charges, et les règles critiques tiennent en base même en cas d'erreur applicative.

Deux conditions :
1. trancher **D1** (rôle de confirmation) et **D2** (règle de remboursement) avant d'écrire le service de paiement ;
2. faire de ce service le premier livrable de la phase C, car aucun paiement ne peut être confirmé tant qu'il n'existe pas.

SYSTEM-C Method **n'est pas prêt à vendre** :
- aucun contenu n'est rédigé ;
- aucun fichier n'existe ;
- aucun parcours d'achat ni aucune condition commerciale n'est en place.
