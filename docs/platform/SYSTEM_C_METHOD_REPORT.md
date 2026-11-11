# SYSTEM-C Method : rapport de la phase C (commandes et paiements manuels)

Date : 2026-11-11. Branche `claude/zealous-fermi-lxtqkl`. Fait suite à `SYSTEM_C_METHOD_AUDIT.md` (phases A et B).

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
| **D6.** Tests obligatoires | Voir §5 | 170 tests, OK |
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

## 3. D4 : 108, 114, puis 147 et 170 tests

| Commit | Tests | Ce qui a été ajouté |
|---|---|---|
| `5809aa9` (rapport du MVP) | 108 | Suite du MVP |
| `83af063` | 111 | `DesignRevisionTests` (3 tests, audit d'ergonomie) |
| `fabaac4` | **114** | `SkillPolishTests` (3 tests, passe `unslop`). Référence de l'audit A et B. |
| `736b25d` | 147 | 33 tests academy (audit A et B) |
| Phase C | **170** | 23 tests de la phase C ; un test de `core` mis à jour (voir §5) |

Le rapport du MVP a été écrit avant les deux passes de design : son chiffre de 108 était exact à cette date.

Pour reproduire, depuis la racine du dépôt :

```bash
git worktree add /tmp/systemc-108 5809aa9 && cp platform/.env /tmp/systemc-108/platform/
cd /tmp/systemc-108/platform && ~/system-c/platform/.venv/bin/python manage.py test --noinput   # Ran 108 tests, OK
cd ~/system-c && git worktree add /tmp/systemc-114 fabaac4 && cp platform/.env /tmp/systemc-114/platform/
cd /tmp/systemc-114/platform && ~/system-c/platform/.venv/bin/python manage.py test --noinput   # Ran 114 tests, OK
cd ~/system-c/platform && python manage.py test --noinput                                      # Ran 170 tests, OK
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

170 tests, tous réussis (PostgreSQL 16) : 114 hérités du MVP et du design, 56 pour academy.

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
| D-C | Durée d'accès : à vie ou limitée (`access_until` est prévu, rien n'est appliqué). |
| D-D | Après un remboursement partiel, faut-il une règle, par exemple suspendre l'accès ? Aujourd'hui, aucune règle n'est appliquée et la page le signale. |
| D-E | Un administrateur peut-il confirmer sa propre commande ? Aujourd'hui, oui. Une séparation des tâches est possible avec un deuxième administrateur ou `finance_admin`. |
| D-F | Création du rôle `finance_admin` (une ligne par permission dans `permissions.py`, plus un libellé traduit) |
| D-G | Hébergement des vidéos et contenu exact de Starter (questions D4 et D5 de l'audit A et B) |

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
2. **Commandes** : ouvrez la commande et confirmez-la avec une note ;
3. **Mes commandes** : vérifiez que l'accès est ouvert ;
4. sur la fiche de la commande, enregistrez un remboursement : l'accès se ferme.
