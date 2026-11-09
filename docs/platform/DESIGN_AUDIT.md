# SYSTEM-C Platform — Audit d'ergonomie et plan de design

Date : 2026-11-09. Réalisé avec les skills du projet `frontend-design-audit` (15 principes d'ergonomie, sévérité de 0 à 4) et `frontend-design` (direction visuelle). Voir `.claude/skills/SOURCES.md`.

**Périmètre :** interface de `platform/` : gabarits `templates/` et `apps/*/templates/`, `static/css/systemc.css`, rendus vérifiés dans Chromium sur ordinateur et sur mobile.
**Type d'interface :** outil d'administration (CRM et tableau de bord).

## Synthèse

| Sévérité | Nombre |
|---|---|
| 4 : bloquant | 0 |
| 3 : majeur | 3 |
| 2 : mineur | 6 |
| 1 : cosmétique | 3 |
| **Total** | **12** |

### Corrections prioritaires
1. **Confirmation des actions irréversibles** (sévérité 3) : demander confirmation avant de supprimer un brouillon, désactiver, archiver ou corriger.
2. **Tableau de bord sans priorités** (sévérité 3) : remplacer la grille de tuiles identiques par une liste « À traiter », triée par urgence.
3. **Libellés en capitales espacées** (sévérité 2) : passer en casse normale, plus lisible en français.

## Constats

### Sévérité 3
**A1. Actions irréversibles sans confirmation.** *Principes :* prévention des erreurs, tolérance.
- **Où :** `bots/version_form.html` (supprimer le brouillon), `bots/botuser_detail.html` (désactiver), `bots/version_detail.html` (corriger une déclaration), `partners/affiliate_detail.html` (archiver), `partners/referral_links.html` (désactiver un lien).
- **Impact :** un clic de trop supprime un brouillon ou inscrit une correction définitive dans un historique en ajout seul.
- **Correction :** attribut `data-confirm` sur ces formulaires, géré par un fichier JavaScript externe (compatible avec la CSP). Sans JavaScript, le formulaire reste utilisable.

**A2. Le tableau de bord ne dit pas quoi faire.** *Principes :* design minimaliste, perceptibilité, reconnaissance plutôt que rappel.
- **Où :** `core/dashboard.html` et les deux sections fournies par les modules.
- **Impact :** neuf tuiles de même poids visuel, et des alertes en petits liens. L'administrateur doit lire chaque tuile pour trouver ce qui est urgent.
- **Correction :** un registre « À traiter », trié par urgence (relances en retard, configurations à appliquer, modifications en attente, parcours bloqués, contacts anciens). Chaque ligne affiche un compte et une action. Les volumes passent ensuite dans un résumé compact.

**A3. Fiche robot surchargée.** *Principes :* structure, design minimaliste.
- **Où :** `bots/botuser_detail.html`.
- **Impact :** les formulaires de pause et de désactivation sont toujours dépliés, avec des champs obligatoires vides, à côté des informations.
- **Correction :** les replier dans des sections à ouvrir, qui exposent leur état ouvert ou fermé.

### Sévérité 2
- **A4. Capitales espacées** sur les titres de navigation, les libellés de tuiles et les en-têtes de tableau. Les mots français longs (« VÉRIFICATIONS EN ATTENTE ») se lisent mal et occupent deux lignes. → Casse normale, graisse et taille pour la hiérarchie.
- **A5. Typographie générique** (polices système et Georgia), chiffres non alignés dans les tableaux. → IBM Plex Sans pour l'interface, Source Serif 4 pour les titres et les chiffres clés, chiffres tabulaires. Les polices sont servies en local.
- **A6. États vides sans action.** Les listes vides disent « aucun » sans proposer la suite. → Bouton d'action dans l'état vide, selon les permissions.
- **A7. Focus clavier peu visible** sur la navigation noire. → Contour or explicite au focus clavier sur tous les éléments interactifs.
- **A8. Métadonnées liées par « · »** (« 09/11/2026 · Administrateur ») : la relation n'est pas dite. → « le 09/11/2026, par Administrateur ».
- **A9. Filtre « Afficher les archivés » mal aligné** avec les autres champs du filtre. → Alignement sur la grille du formulaire.

### Sévérité 1
- **A10.** Fond crème et cartes toutes identiques : rendu « gabarit ». → Fond papier neutre, cartes réservées aux blocs d'information, rayons limités à deux valeurs.
- **A11.** Noir teinté (#09090a) à la place du noir. → Noir franc pour la navigation, conformément à l'identité.
- **A12.** Ombres et bordures en valeurs libres. → Jetons d'espacement, de rayon et de bordure.

## Points forts à conserver
- Statuts toujours accompagnés de « déclaré, non vérifié sur le VPS » (correspondance avec la réalité).
- Badges d'état avec icône **et** texte, pas seulement une couleur (accessibilité, perceptibilité).
- Fil d'Ariane sur les fiches, lien d'évitement, champs reliés à leur aide et à leurs erreurs (reconnaissance, accessibilité).
- Actions masquées selon les permissions (cohérence, prévention des erreurs).
- Interface bilingue complète.

## Plan de design (skill `frontend-design`)

**Cadre imposé :** noir et or, sobre et institutionnel. La skill demande de suivre le brief à la lettre sur les axes qu'il fixe ; les choix ci-dessous portent sur les axes laissés libres.

- **Couleurs :**
  - Noir `#000000` pour la navigation ;
  - Or `#C9A44C` pour les surfaces d'action et les filets ;
  - Or profond `#6B4F0E` pour les liens et le texte d'accent sur fond clair ;
  - Papier `#F5F5F3` (neutre, pas crème) ;
  - Encre `#17150F` ;
  - Pierre `#66625A` pour le texte secondaire ;
  - Filet `#DDDAD2`.
- **Typographie :**
  - Source Serif 4 (600) pour les titres de page et les chiffres du registre ;
  - IBM Plex Sans (400, 500, 600) pour toute l'interface ;
  - chiffres tabulaires dans les tableaux.
- **Mise en page :** navigation noire fixe à gauche, contenu aligné à gauche. Le tableau de bord s'ouvre sur le registre « À traiter » : une colonne de chiffres en serif, alignés, séparés par des filets fins, avec le libellé et l'action à droite.
- **Principe :** l'audace est concentrée dans un seul élément, le registre du jour, qui reprend la notion de registre déclaratif au cœur du produit. Tout le reste reste discret : moins de cadres, pas d'ombres, casse normale.

**Revue du plan :** la première version reprenait la grille de tuiles chiffrées, qui est le traitement par défaut. Elle est remplacée par le registre, propre à ce produit. Le fond crème, l'un des marqueurs de rendu généré cités par la skill, est remplacé par un papier neutre.

## État des corrections (2026-11-09)

Les douze constats (A1 à A12) sont corrigés dans `platform/` et couverts par des tests :
- `DesignRevisionTests` vérifie le registre « À traiter », les confirmations et les polices locales ;
- le test existant sur les gabarits garantit l'absence de script et de style en ligne.

Vérification dans Chromium :
- polices chargées ;
- aucune erreur de console ni violation de CSP ;
- la confirmation s'affiche, et la refuser n'envoie pas le formulaire ;
- aucun débordement horizontal sur mobile.
