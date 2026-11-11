# SYSTEM-C Method : rapport de la phase C (commandes et paiements manuels)

Date : 2026-11-11, actualisé après les décisions précédant la phase D (§9). Branche `claude/zealous-fermi-lxtqkl`. Fait suite à `SYSTEM_C_METHOD_AUDIT.md` (phases A et B).

## Statut

**SYSTEM-C Method n'est pas prêt à être commercialisé.** Le parcours de commande et la confirmation manuelle des paiements fonctionnent et sont testés. En revanche :
- aucun contenu pédagogique n'est rédigé (0 leçon sur 25) ;
- aucun fichier de ressource n'existe ;
- les conditions générales de vente, la politique de remboursement et les modalités de paiement ne sont pas écrites ;
- les trois offres réelles restent en brouillon et ne peuvent pas être commandées.

## 1. Décisions validées et mise en œuvre

| Décision | Mise en œuvre | Preuve |
|---|---|---|
| **D1.** Permission `payments.confirm_order`, accordée à `org_admin` ; `finance_admin` plus tard ; jamais au super-utilisateur ; vérifiée côté serveur ; auditée | Permissions `payments.view_orders`, `payments.confirm_order`, `payments.cancel_order` et `payments.refund_order`, toutes réservées à `org_admin` (`apps/core/permissions.py`). Vérification dans la vue et à nouveau dans le service. Chaque confirmation enregistre l'auteur, la date et l'heure, le montant, la devise, la référence, la note, l'ancien et le nouveau statut (`OrderAudit`), plus une entrée du journal d'audit de la plateforme. | `PaymentConfirmationTests` |
| **D2.** Remboursement intégral : accès retiré immédiatement ; inscription, progression et historique conservés ; auteur, date, montant et justification enregistrés ; pas de réactivation accidentelle | Service `refund` : le statut passe à « remboursée » et l'inscription à « annulée », sans rien supprimer. PostgreSQL interdit de quitter « remboursée » ou « annulée » et de réactiver une inscription liée à une telle commande. | `RefundTests` |
| **D2.** Remboursement partiel : pas de retrait automatique | Le montant est enregistré, la commande reste « payée » et les droits ne changent pas. Les pages de la commande signalent le remboursement partiel. Si les remboursements partiels atteignent le prix payé, c'est un remboursement intégral. | `test_partial_refund_keeps_access_and_is_recorded` |
| **D3.** Clarifier les leçons | Voir §2. Contraintes d'unicité ajoutées en base. | `LessonUniquenessTests` |
| **D4.** Clarifier les tests | Voir §3. | Commandes reproductibles |
| **D5.** Phase C | Voir §4 | Voir §5 |
| **D6.** Tests obligatoires | Voir §5 | 183 tests, OK |
| **D7.** Rapport | Ce document | Sans objet |

Aucun paiement n'est confirmé automatiquement et aucun prestataire n'est connecté. Une commande ne peut devenir « payée » qu'avec une ligne d'historique qui porte un auteur, une note, le montant et la devise. C'est vérifié par PostgreSQL : même une requête SQL directe est refusée.

## 2. D3 : 15 leçons, puis 25

| Moment | Commit | Leçons | Origine |
|---|---|---|---|
| Phase B | `5db5a83` | 15 (3 par étape) | La première commande d'initialisation ne reprenait que 3 des 5 objectifs de chaque étape du cahier des charges |
| Audit A et B | `4842bba` | 25 (5 par étape) | La commande crée les 10 objectifs manquants. La migration 0005 renomme et repositionne les 15 leçons existantes, sans en créer de nouvelles. |

**Nombre réel : 25 leçons, 5 par étape** :
1. Comprendre ;
2. Préparer ;
3. Décider ;
4. Documenter ;
5. Évaluer.

**Contrôle sans doublon.** Le parcours exact de votre base a été rejoué sur une base temporaire :
1. initialisation de la phase B (`3656b91`) ;
2. migrations et initialisation de l'audit (`736b25d`) ;
3. migrations actuelles.

Résultat : 25 leçons, 5 étapes, aucune position en double, aucun contenu rédigé.

Les doublons sont désormais impossibles en base : une position unique par étape, un titre unique par étape, une position unique par programme pour les étapes.

**Aucune leçon n'est rédigée.** Chacune n'a qu'un titre et un résumé de l'objectif, en français et en anglais. Une leçon ne peut pas être publiée sans contenu rédigé (contrainte en base). Un titre ou un résumé n'est donc jamais présenté comme une leçon.

Pour vérifier sur votre poste :

```bash
python manage.py shell -c "from apps.academy.models import Lesson; print(Lesson.objects.count(), Lesson.objects.exclude(body_fr='').count())"
```

Résultat attendu : `25 0`.

## 3. D4 : 108, 114, puis 147, 170 et 183 tests

| Commit | Tests | Ce qui a été ajouté |
|---|---|---|
| `5809aa9` (rapport du MVP) | 108 | Suite du MVP |
| `83af063` | 111 | `DesignRevisionTests` (3 tests, audit d'ergonomie) |
| `fabaac4` | **114** | `SkillPolishTests` (3 tests, passe `unslop`). Référence de l'audit A et B. |
| `736b25d` | 147 | 33 tests academy (audit A et B) |
| Phase C | 170 | 23 tests de la phase C ; un test de `core` mis à jour (voir §5) |
| Ajustements avant la phase D | **183** | 13 tests (§9) |

Le rapport du MVP a été écrit avant les deux passes de design : son chiffre de 108 était exact à cette date.

Pour reproduire, depuis la racine du dépôt :

```bash
git worktree add /tmp/systemc-108 5809aa9 && cp platform/.env /tmp/systemc-108/platform/
cd /tmp/systemc-108/platform && ~/system-c/platform/.venv/bin/python manage.py test --noinput   # Ran 108 tests, OK
cd ~/system-c && git worktree add /tmp/systemc-114 fabaac4 && cp platform/.env /tmp/systemc-114/platform/
cd /tmp/systemc-114/platform && ~/system-c/platform/.venv/bin/python manage.py test --noinput   # Ran 114 tests, OK
cd ~/system-c/platform && python manage.py test --noinput                                      # Ran 183 tests, OK
cd ~/system-c && git worktree remove /tmp/systemc-108 && git worktree remove /tmp/systemc-114
```

Ces commandes ont été exécutées pour ce rapport, avec ces résultats.

## 4. Ce qui fonctionne (phase C)

### Pages acheteur (permission `academy.view`, commande avec `academy.buy`)

| Page | Contenu |
|---|---|
| **Offres** (`/academy/offers/`) | Seules les offres publiées d'un programme publié apparaissent. Elles affichent le prix et la devise venant de la base, jamais du code, ainsi que l'avertissement éducatif et financier. |
| **Fiche d'offre** | Ressources incluses, chacune avec son état réel : « En préparation », « Après paiement » ou « Accessible ». Commander exige de cocher la lecture de l'avertissement. La commande est enregistrée au prix affiché. Une deuxième demande renvoie vers la commande déjà ouverte. |
| **Mes commandes** et **fiche de commande** | Statut, accès ouvert ou fermé, ressources, historique (sans les notes internes de l'administration). Annulation possible tant que la commande n'est pas payée. |

Chaque commande enregistre les textes acceptés :
- la version de l'avertissement (`2026-11`) ;
- la version des conditions générales de vente : vide pour l'instant, la page indique « Pas encore publiées ».

### Pages d'administration (permission `payments.view_orders`)

| Page | Contenu |
|---|---|
| **Commandes** | Limitée à l'organisation courante. Filtre par statut (l'adresse garde le filtre), nombre de paiements à vérifier. |
| **Fiche de commande** | Détails, accès, textes acceptés, historique complet avec les notes. |

Actions de la fiche de commande :
- **Confirmer le paiement** : case « J'ai vérifié la réception de X USD », référence facultative, note obligatoire, confirmation avant envoi ;
- **Enregistrer un remboursement** : montant, justification et référence. Le montant proposé par défaut est le solde : rembourser le solde est un remboursement intégral, un montant inférieur un remboursement partiel ;
- **Annuler** une commande non payée, avec un motif obligatoire.

### Règles garanties par PostgreSQL (migration 0008)

| Règle | Effet |
|---|---|
| Création | Une commande naît non payée. |
| Transitions autorisées | Brouillon vers « en attente de paiement » ou « annulée » ; en attente vers « à vérifier », « payée » ou « annulée » ; « à vérifier » vers « payée » ou « annulée » ; « payée » vers « remboursée ». « Annulée » et « remboursée » sont définitives. |
| Historique obligatoire | Tout changement de statut exige la ligne d'historique correspondante. |
| Montants | Prix, devise, acheteur, offre, organisation et textes acceptés sont immuables après création. Le montant remboursé ne fait qu'augmenter et vaut toujours la somme des remboursements de l'historique. |
| Confirmation | Elle porte le prix et la devise exacts de la commande. |
| Historique | En ajout seul : ni modification ni suppression. |
| Réactivation | Aucune inscription active sur une commande annulée ou remboursée. |

Une confirmation répétée (double clic, deuxième onglet) ne change rien. La commande est verrouillée pendant l'opération, et le second envoi affiche « déjà confirmée ».

### Données de démonstration

`python manage.py seed_academy_demo --organization system-c --yes` (refusée hors `DEBUG`) crée :
- un programme et une offre « [Démo] » publiés, à 5,00 USD fictifs ;
- des ressources qui pointent vers example.org.

La commande ne crée aucune commande et ne simule aucun paiement : on commande l'offre, puis on la confirme à la main avec une note. Ce parcours a été suivi de bout en bout dans Chromium.

## 5. Tests

183 tests, tous réussis (PostgreSQL 16) : 114 hérités du MVP et du design, 69 pour academy (dont les 13 du §9).

Correspondance avec D6 :

| Exigence D6 | Test |
|---|---|
| Un utilisateur non autorisé ne peut pas confirmer | `test_unauthorised_roles_cannot_confirm` (crm_admin, crm_operator, instructor, student : 403 et refus du service) ; `test_superuser_gets_no_payment_permission` |
| Un administrateur d'une autre organisation ne peut pas confirmer | `test_admin_of_another_organization_cannot_confirm` (404 sur la page, refus du service) |
| Une commande non payée ne donne aucun accès | `test_unpaid_order_gives_no_paid_access`, `test_order_needs_the_notice_and_is_not_duplicated` |
| Une commande confirmée ne donne que son offre | `test_confirmation_is_audited_and_opens_only_the_offer`, `test_paid_offer_opens_only_its_own_resources` |
| Un remboursement intégral retire immédiatement les droits | `test_full_refund_removes_access_immediately_and_keeps_everything` |
| La progression est conservée | Même test : la progression terminée existe toujours |
| Une confirmation répétée ne crée pas de doublon | `test_repeated_confirmation_creates_no_duplicate` |
| Montants et devises immuables | `test_price_and_currency_are_frozen_at_order_time`, `test_refund_limits` |
| Historique non modifiable ni supprimable | `test_order_history_is_append_only` |
| Pas de réactivation accidentelle | `test_rights_cannot_be_reactivated_after_a_full_refund` |
| Pas de paiement sans historique | `test_database_refuses_a_payment_without_history` |

Également testés :
- offres en brouillon et programmes non publiés non commandables ;
- avertissement obligatoire, pas de commande en double ;
- l'acheteur ne voit et n'annule que ses propres commandes, et ne peut pas annuler une commande payée ;
- isolation des listes de commandes et des offres entre organisations ;
- refus des données de démonstration hors `DEBUG` ;
- unicité des leçons.

Un test existant de `core` (`test_academy_roles_have_no_crm_access`) fixe la liste exacte des permissions des rôles Academy. Il attend désormais `academy.buy` en plus de `academy.view`, et toujours aucun accès au CRM ni aux paiements.

## 6. Skills d'interface : recherche, installation, application

Deux skills ont été trouvées sur GitHub, lues en entier, puis installées figées à un commit (provenance et empreintes dans `.claude/skills/SOURCES.md`) :
- **`web-interface-guidelines`** : règles d'interface de Vercel (`vercel-labs/web-interface-guidelines`, MIT). L'original télécharge ses règles à chaque usage ; ici, elles sont figées localement et adaptées au projet (casse de phrase en français, pas de règles React, CSP).
- **`accessibility`** : audit WCAG 2.2 d'Addy Osmani (`addyosmani/web-quality-skills`, MIT), fondé sur les pages rendues.

Elles ont été appliquées à **toutes les pages** de la plateforme : 23 pages auditées avec axe-core 4.10.2 dans Chromium (règles WCAG 2.0, 2.1 et 2.2 A et AA, plus les bonnes pratiques), sur ordinateur et à 390 px de large.

| Constat | Correction |
|---|---|
| Défilement horizontal à 390 px sur Relances, Paramètres autorisés et Membres (WCAG 1.4.10) : les libellés masqués des tableaux sortaient de leur cadre défilant, et un téléphone dézoomait la page | `.table-responsive { position: relative; }` |
| Rôle ARIA non autorisé sur le formulaire de langue (sur toutes les pages) | Le groupe de boutons est déplacé dans un `div role="group"` |
| Page « Changer le mot de passe » sans titre de niveau 1 | Titre ajouté |
| Formulaires « affilié » et « nouveau membre » : le navigateur proposait les coordonnées de l'administrateur | `autocomplete="off"`, clavier téléphone pour le téléphone |
| Règles Vercel absentes : titres équilibrés, délai de double tape | `text-wrap: balance` sur les titres ; `touch-action: manipulation` |

Résultat après correction : **0 violation axe sur les 23 pages, 0 défilement horizontal, 0 erreur de console, 0 violation de la CSP.**

Les règles Vercel déjà respectées l'étaient grâce aux passes précédentes :
- focus visible ;
- `prefers-reduced-motion` ;
- transitions listées une à une ;
- chiffres tabulaires ;
- `theme-color` ;
- marge de défilement sous la barre fixe ;
- confirmation des actions irréversibles.

## 7. Ce qui reste à faire

### Décisions attendues

| N° | Décision |
|---|---|
| D-A | Prestataire de paiement (aucun n'est connecté). Il faudra aussi décider ce que vérifie la confirmation automatique : signature du prestataire, montant, devise. |
| D-B | Modalités de paiement manuel à communiquer aux acheteurs : virement, mobile money… Elles ne sont affichées nulle part, la page dit seulement qu'aucun paiement en ligne n'est proposé. |
| D-F | Création du rôle `finance_admin` (utile aussi parce qu'un administrateur ne peut plus confirmer sa propre commande) (une ligne par permission dans `permissions.py`, plus un libellé traduit) |
| D-G | Hébergement des vidéos et contenu exact de Starter (questions D4 et D5 de l'audit A et B) |
| D-H | Une ressource rattachée plus tard à une offre devient accessible aux acheteurs existants de cette offre. Ce n'est promis nulle part ; confirmer que ce comportement convient, ou demander que l'accès soit figé au contenu présent à l'achat. |
| D-I | Durée de l'accompagnement de Guided (l'offre accepte une durée en jours ; elle est aujourd'hui sans date d'expiration) |

Les questions D-C (durée d'accès), D-D (remboursement partiel) et D-E (confirmer sa propre commande) sont tranchées : voir §9.

### Fonctionnalités

| Domaine | Restant à construire |
|---|---|
| Écrans de gestion du contenu | Programmes, étapes, leçons, ressources, offres et prix, publication. Aujourd'hui, seule la commande `seed_system_c_method` crée ces données, et rien ne permet de les modifier dans l'interface. |
| Espace apprenant | Lecture des leçons, téléchargement protégé des ressources, suivi de progression, page « Mes programmes ». |
| Accès manuel | Attribution, suspension et réactivation, avec un motif. |
| Page publique et collecte de contacts | Page de présentation, ressource gratuite « 7 questions », formulaire avec consentement distinct (phase E). |
| Conditions commerciales et juridiques | CGV, politique de remboursement, conditions d'utilisation, politique de confidentialité. La version acceptée est déjà enregistrée sur chaque commande, mais aucun texte n'existe. |
| Courriels | Aucun envoi : ni accusé de commande, ni confirmation de paiement. Aucun fournisseur n'est configuré. |

### Limites réglementaires

Avant toute vente, une validation juridique est nécessaire pour :
- les conditions de vente et le droit de rétractation applicable aux contenus numériques ;
- la facturation et la fiscalité ;
- la protection des données des acheteurs ;
- la conformité des textes publics aux règles publicitaires (Meta).

Les avertissements affichés ne remplacent aucune de ces obligations.

## 8. Mettre à jour votre poste

```bash
cd ~/system-c && git pull origin claude/zealous-fermi-lxtqkl
cd platform && source .venv/bin/activate
python manage.py migrate
python manage.py test
python manage.py seed_academy_demo --organization system-c --yes   # facultatif, données [Démo]
python manage.py runserver
```

Connectez-vous avec un compte `org_admin` :
1. **Offres** : commandez l'offre « [Démo] » ;
2. **Commandes** : ouvrez la commande et confirmez-la avec une note. En `DEBUG`, vous pouvez confirmer votre propre commande uniquement parce qu'elle est « [Démo] » ;
3. **Mes commandes** : vérifiez que l'accès est ouvert, sans date d'expiration ;
4. sur la fiche de la commande, enregistrez un remboursement partiel (l'accès reste ouvert), puis révoquez l'accès avec un motif, ou remboursez le solde (l'accès se ferme).

## 9. Ajustements avant la phase D

### Confirmation de sa propre commande

- **Règle :** le service compare l'acheteur et la personne qui confirme, et refuse si c'est la même personne, avec le message « Vous ne pouvez pas confirmer le paiement de votre propre commande. Une autre personne autorisée doit le faire. » La page masque alors le formulaire et affiche ce message.
- **Exception :** une commande d'un programme de démonstration, quand `DEBUG` est actif. Hors `DEBUG`, une commande de démonstration ne peut plus être confirmée par personne.
- **En base :** PostgreSQL refuse aussi une confirmation où l'auteur est l'acheteur, sauf sur un programme marqué démonstration. L'indicateur de démonstration est fixé à la création du programme : un vrai programme ne peut pas être requalifié pour contourner la règle.
- **Tests :** `SelfConfirmationTests`. Refus par le service, par la page et par la base, y compris en `DEBUG` sur une offre réelle. Confirmation par un second administrateur possible. Exception de démonstration limitée à `DEBUG`.

### Durée d'accès

| Élément | Mise en œuvre |
|---|---|
| Valeur explicite | `AccessMode` vaut « Sans date d'expiration » ou « Durée limitée ». Il est porté par l'offre (valeur par défaut : sans date d'expiration) et recopié sur l'inscription à la confirmation. |
| Cohérence en base | « Sans date d'expiration » n'a jamais de date de fin ; « durée limitée » en a toujours une, et l'offre a alors un nombre de jours d'au moins 1. |
| Changement d'offre | Une inscription garde la durée accordée, même si l'offre change ensuite. |
| Affichage | La fiche d'offre et les commandes indiquent : « Accès au contenu de cette offre, sans date d'expiration. Les mises à jour futures, les autres programmes et les accompagnements ne sont pas inclus, sauf mention contraire. » Pour une durée limitée : « pendant N jours à partir de la confirmation du paiement », puis « Jusqu'au … ». |

Compatibilité avec le modèle et le contrôle d'accès : rien n'a été refondu. `access_until` existait déjà et le contrôle d'accès refusait déjà une date dépassée. La durée limitée réutilise ce mécanisme ; « sans date d'expiration » est l'absence de date, désormais nommée et vérifiée.

Tests : `AccessDurationTests`.

Pendant ce travail, un test a révélé un défaut de la première version de la contrainte : en SQL, `NULL >= 1` vaut NULL, ce qui laissait passer « durée limitée » sans nombre de jours. La contrainte vérifie désormais explicitement la présence de la durée.

### Remboursement partiel et révocation

- **Pas de retrait automatique :** inchangé.
- **Cumul des remboursements :** jamais supérieur au montant payé. C'est vérifié à quatre niveaux : le service, le formulaire, une contrainte en base (`refunded_amount <= price`) et le déclencheur, qui recalcule la somme depuis l'historique. Test : `test_cumulative_refunds_never_exceed_the_amount_paid` (10 + 10 acceptés, puis 9,01 refusé sur une commande de 29).
- **Révocation, une action distincte :**
  - permission `payments.revoke_access`, réservée à `org_admin` ;
  - motif obligatoire ;
  - possible seulement après un remboursement partiel d'une commande payée (vérifié aussi en base) ;
  - la commande reste « payée » ; l'inscription passe à « Accès révoqué » et ne peut plus redevenir active (base) ;
  - enregistrée dans l'historique de la commande (auteur, date, motif) et dans le journal d'audit ;
  - la répéter ne crée rien de plus.
- **Tests :** `PartialRefundAndRevocationTests`, dont le refus depuis une autre organisation.

### Données de démonstration

| Exigence | Vérification |
|---|---|
| Refus hors `DEBUG` | `test_refused_outside_debug` |
| Données clairement identifiées | Le programme porte `is_demo`. Une contrainte en base impose qu'un programme soit de démonstration si et seulement si son titre commence par « [Démo] ». L'offre et les ressources créées portent aussi « [Démo] », et un bandeau s'affiche sur les pages de l'offre et des commandes. |
| Pas d'offre de démonstration achetable en production | Hors `DEBUG`, elle n'apparaît pas dans les offres, sa fiche répond 404, la commande est refusée et une commande existante ne peut pas être confirmée, même si les données sont en base. Test : `test_demo_offer_is_not_purchasable_outside_debug`. |
| Pas de modification des vraies données | Comparaison complète des offres, commandes, ressources et programmes avant et après la commande : rien n'est modifié, aucune commande n'est créée. Test : `test_demo_seed_labels_everything_and_leaves_real_data_untouched`. |

### Vérification finale

- **Suite complète :** 183 tests, OK. `makemigrations --check` : aucune différence. `manage.py check` : aucun problème.
- **Migrations 0010 et 0011 :**
  - appliquées, annulées puis réappliquées sur la base de développement ;
  - rejouées sur une base dans l'état probable de la vôtre : programme « [Démo] » et commande de démonstration confirmée par l'acheteur avec l'ancienne règle. Après migration, le programme est marqué démonstration et l'inscription reste valide, sans date d'expiration.
- **Isolation et permissions :** couvertes par les tests (une autre organisation reçoit 404 ou un refus du service pour la confirmation, la révocation, les fiches et les listes). Les permissions `payments.*` restent réservées à `org_admin` ; le super-utilisateur n'en a aucune.
- **Parcours de démonstration complet dans Chromium :**
  1. commande ;
  2. auto-confirmation en `DEBUG` ;
  3. remboursement partiel de 2,00 USD, accès conservé ;
  4. révocation motivée : accès fermé, commande toujours payée ;
  5. vue acheteur avec l'avis de révocation.

  Résultat : 0 violation axe sur les pages concernées, 0 erreur de console. Une phrase devenue fausse après une révocation (« L'accès est inchangé ») a été corrigée.

### Risques restants

- **Séparation des tâches :** une organisation avec un seul `org_admin` ne peut confirmer aucune commande passée par cet administrateur. C'est voulu, mais il faudra un deuxième administrateur ou le rôle `finance_admin` (D-F).
- **Durée limitée de Guided :** prévue mais non configurée (D-I). Aucun écran ne permet encore de régler la durée d'une offre ; seule une modification en base le permet.
- **Ressources ajoutées plus tard :** une ressource rattachée ensuite à une offre devient accessible aux acheteurs existants (D-H).
- **Commandes de démonstration créées avant ce correctif :** une base locale peut en contenir, confirmées par leur acheteur avec l'ancienne règle. Elles restent valides (données de démonstration) et ne sont plus confirmables hors `DEBUG`.
- **Pas encore commercialisable :** le statut en tête de ce document reste vrai.
