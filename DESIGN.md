---
version: 1
name: SYSTEM-C Platform
description: Système de design de SYSTEM-C Platform, application d'administration (CRM des affiliés et des utilisateurs de robots, programmes Academy, commandes). Noir et or, sobre et institutionnel, en verre fumé ; univers du registre et du sceau. Source de vérité des valeurs : platform/static/css/systemc.css.

colors:
  black: "#000000"
  nav-hover: "#2a251b"
  nav-line: "#2a2618"
  nav-text: "#d6d2c8"
  nav-muted: "#aaa18d"
  gold: "#c9a44c"
  gold-light: "#e5c97f"
  gold-deep: "#6b4f0e"
  paper: "#0a0907"
  surface: "#1b1813"
  ink: "#f3eee3"
  stone: "#c8c0ae"
  muted: "#aaa18d"
  rule: "rgba(243, 238, 227, .12)"
  rule-strong: "rgba(243, 238, 227, .42)"
  ok: "#7fd1a0"
  ok-bg: "#11291c"
  wait: "#eec46b"
  wait-bg: "#33260a"
  stop: "#ff9b90"
  stop-bg: "#3a1512"
  demo: "#9ebff0"
  demo-bg: "#142238"
  stop-solid: "#a3261c"
  glass: "rgba(24, 21, 16, .52)"
  focus: "{colors.gold}"

typography:
  page-title:
    fontFamily: Source Serif 4
    fontSize: 28px
    fontWeight: 600
    lineHeight: 1.2
    letterSpacing: -0.005em
  section-title:
    fontFamily: Source Serif 4
    fontSize: 20px
    fontWeight: 600
    lineHeight: 1.3
  ledger-figure:
    fontFamily: Source Serif 4
    fontSize: 40px
    fontWeight: 600
    lineHeight: 1
    fontFeature: lining-nums tabular-nums
  body:
    fontFamily: IBM Plex Sans
    fontSize: 15px
    fontWeight: 400
    lineHeight: 1.55
  label:
    fontFamily: IBM Plex Sans
    fontSize: 14px
    fontWeight: 500
  small:
    fontFamily: IBM Plex Sans
    fontSize: 14px
    fontWeight: 400
  caption:
    fontFamily: IBM Plex Sans
    fontSize: 13px
    fontWeight: 400

rounded:
  xs: 4px
  sm: 8px
  md: 12px
  pill: 999px

spacing:
  "1": 4px
  "2": 8px
  "3": 16px
  "4": 24px
  "5": 40px
  "6": 64px
  sidebar: 264px
  content-max: 1440px
---

## Overview

SYSTEM-C Platform est un registre administratif. Rien n'y est piloté à distance : chaque statut est une déclaration enregistrée, datée et attribuée. L'interface doit donc paraître exacte, posée et solennelle, comme un registre tenu à la main et scellé.

**Verre fumé** (décision du responsable, 2026-11-12). Toute l'application repose sur un fond noir (`{colors.paper}`) éclairé de trois halos d'or et d'ambre, fixes. Navigation, barre du haut, cartes, registre, résumés, menus et page de connexion sont des panneaux de verre sombre (`{colors.glass}`, flou de 20 px) bordés d'un filet clair (`{colors.rule}`), avec un reflet en haut. Le texte est crème (`{colors.ink}`). L'**or** (`{colors.gold}`) reste l'unique accent : action principale d'une zone, rubrique active, filet de signature, anneau de focus. Les liens passent en **or clair** (`{colors.gold-light}`).

**Signature.** Un filet d'or vertical de 2 px (`.sc-declared`) précède toute information « déclarée, non vérifiée » : statut d'un robot, étape Deriv, paiement confirmé à la main. Il ne sert à rien d'autre.

**Moment.** Le registre « À traiter » du tableau de bord : une colonne de chiffres en serif, alignés à droite et séparés par des filets, avec le libellé et une seule action par ligne. L'or n'y marque que la ligne la plus urgente.

**Caractéristiques :**
- un fond noir éclairé d'or, des panneaux de verre fumé, un filet clair et un reflet ; une seule recette de verre pour toutes les surfaces ;
- un seul accent (or), utilisé une ou deux fois par écran ;
- une serif (Source Serif 4, 600) pour les titres et les chiffres clés, une sans (IBM Plex Sans, 400 et 500) pour tout le reste ;
- des états toujours écrits en mots, avec une icône, jamais par la couleur seule.

## Colors

> Contrastes WCAG 2.2 calculés au pire cas : le verre posé sur la zone la plus claire du fond (halo or et ambre), soit une surface de `#3e311a`. axe ne sait pas mesurer sous un flou ; l'audit le refait avec cette teinte en aplat (2026-11-12).

### Fond et verre
- **Fond** (`{colors.paper}`) : noir chaud, sous trois dégradés radiaux fixes (or 42 %, ambre 30 %, or clair 16 %).
- **Verre** (`{colors.glass}`) : cartes, registre, résumés, bandeau d'information ; flou `blur(20px) saturate(140%)`, reflet `linear-gradient` blanc de 7 % à 0, liseré clair en haut, ombre douce.
- **Verre appuyé** (`rgba(16, 14, 11, .82)`) : menus déroulants et menu mobile, qui passent au-dessus du contenu.
- **Navigation et barre du haut** : verre noir (`rgba(0, 0, 0, .42)` et `rgba(10, 9, 7, .55)`).
- **Champs** : creux sombre `rgba(10, 9, 7, .45)`, bordure `{colors.rule-strong}` (3,3:1, WCAG 1.4.11).
- **Surface pleine** (`{colors.surface}`) : remplace le verre quand le flou n'existe pas ou quand le système demande moins de transparence ou plus de contraste.
- Un verre posé dans un verre ne se floute pas deux fois : voile de 3 % seulement.

### Marque et accent
- **Or** (`{colors.gold}`) : fond du bouton principal (texte noir : 8,9:1), rubrique active, filets de signature, anneau de focus (5,4:1 au pire), puce de la chronologie, contour des cases.
- **Or clair** (`{colors.gold-light}`) : liens, code, boutons d'accent secondaire, survol du bouton principal.
- **Or profond** (`{colors.gold-deep}`) : fond des cases cochées (coche blanche à 8:1). Jamais comme texte sur le verre.
- **Noir** (`{colors.black}`) : texte posé sur l'or ou sur le crème.
- **Choix inversé** (`.btn-dark`) : fond crème, texte noir, pour l'état choisi (langue, filtre).

### Texte (trois rôles)
- **Encre** (`{colors.ink}`) : texte principal (11:1 au pire).
- **Pierre** (`{colors.stone}`) : texte secondaire (7:1).
- **Atténué** (`{colors.muted}`) : libellés de listes de définitions, métadonnées, en-têtes de tableau, « Non renseigné » (4,95:1).
- **Zéro du registre** : `#8a8170`, chiffre de 40 px (texte large, 3,3:1 pour 3:1 exigé).

### États (fond sombre teinté, texte clair, bordure intermédiaire)
| État | Texte / fond | Contraste | Usage |
|---|---|---|---|
| Correct | `{colors.ok}` / `{colors.ok-bg}` | 8,5:1 | Validée, appliquée, payée, accès ouvert |
| Attente | `{colors.wait}` / `{colors.wait-bg}` | 9:1 | À configurer, en attente de paiement |
| Arrêt | `{colors.stop}` / `{colors.stop-bg}` | 7,7:1 | En retard, remboursée, erreurs ; contour des actions dangereuses |
| Compte réel | blanc / `{colors.stop-solid}` | 7,4:1 | Badge « Réel », toujours avec l'icône octogone |
| Démo | `{colors.demo}` / `{colors.demo-bg}` | 8,5:1 | Badge « Démo » |
| Neutre | `#e4ded0` / `#2c2820` | 10,9:1 | En pause, annulée, accès fermé |

## Elevation & Depth

Le verre donne la profondeur : un panneau flou, un liseré clair en haut (`inset 0 1px 0`, blanc à 8 %) et une ombre douce et neutre (`0 16px 40px`, noir à 32 %). Jamais d'ombre colorée ni de lueur. Le registre « À traiter » garde son filet d'or de 3px en haut.

## Shapes

| Élément | Rayon |
|---|---|
| Petits repères (cases du `+` des sections repliables) | `{rounded.xs}` |
| Boutons, champs, bandeaux, sections repliables | `{rounded.sm}` |
| Cartes, registre, résumés | `{rounded.md}` |
| Badges d'état | `{rounded.pill}` |

## Components

### Navigation
Rangées de 36px (44px sur mobile), icône dans une colonne fixe, titres de groupe en casse de phrase (« Gestion des robots »). La rubrique active : fond `{colors.nav-hover}`, filet d'or à gauche, texte or clair.

### Boutons
- **Principal** : fond or, texte noir. Un seul par zone ; il marque l'action la plus importante.
- **Secondaire** : contour neutre (`{colors.rule-strong}`), texte encre. C'est le cas par défaut des actions qui ne sont pas les plus urgentes.
- **Accent secondaire** (contour or, texte or clair) : réservé à l'action positive d'une fiche (« Modifier », « Marquer faite »).
- **Danger** : contour rouge clair (`{colors.stop}`), fond `{colors.stop-solid}` au survol, pour désactiver, annuler ou rembourser, toujours avec une confirmation.
- Survol : changement de couleur en 150ms ; appui : réduction à 98 %.

### Formulaires
Libellé visible au-dessus de chaque champ, astérisque rouge pour les champs obligatoires, aide en dessous, erreur sous le champ. Un résumé d'erreurs en tête du formulaire prend le focus et pointe vers chaque champ. Les fiches saisies pour un tiers (affilié, membre) désactivent le remplissage automatique du navigateur. Jamais de champ pour un mot de passe de courtier, un jeton ou une donnée bancaire.

### Cartes et sections repliables
Carte de verre, filet `{colors.rule}`, en-tête séparé par un filet. Une carte ne contient pas d'autres cartes : à l'intérieur, les colonnes se séparent par des filets (suivi Deriv). Les formulaires secondaires sont repliés dans une section `+` / `−` qui expose son état.

### Badges et mentions
- Badge d'état : icône et mot, couleur d'état, forme de pilule, 13px.
- Absence : « Non renseigné », « Jamais déclarée », etc., en texte atténué, pour ne pas ressembler à une donnée.
- Mention déclarée (`.sc-declared`) : filet d'or de 2px, texte atténué de 13px.

### Composants propres au produit
- **Registre « À traiter »** : chiffre en serif à gauche (rouge si urgent, grisé si nul), libellé et raison au centre, une action à droite.
- **Résumés** : deux registres côte à côte, libellé à gauche, chiffre en serif aligné à droite.
- **Chronologie** : filet vertical, puce d'or, ligne de métadonnées « le … , par … », puis le contenu.

## Do's and Don'ts

### Do
- Dire ce qui est déclaré et non vérifié, avec le filet d'or.
- Garder l'or pour une seule chose par zone.
- Écrire les états en mots, avec une icône.
- Relier les métadonnées par des mots (« le 09/11/2026, attribuée à … »), pas par un point médian.
- Vérifier chaque nouvelle page à 390px, au clavier et avec axe, verre remplacé par `#3e311a` en aplat (pire cas).

### Don't
- Pas de lueur, d'ombre colorée ni de dégradé sur un élément : les seuls dégradés sont les halos du fond et le reflet du verre.
- Pas de verre plus transparent que `{colors.glass}` : en dessous, le texte atténué tombe sous 4,5:1.
- Pas de violet ni de bleu de marque générique ; le bleu ne sert qu'au badge « Démo ».
- Pas de capitales espacées, d'émoji, de point d'exclamation ni de mot publicitaire.
- Pas de tiret long dans les textes.
- Pas de carte dans une carte dans une carte.
- Pas de CDN, de police distante, de script ni de style en ligne (CSP stricte).
- Pas de chiffre inventé ni de témoignage : seulement des données réelles ou marquées « [Démo] ».
