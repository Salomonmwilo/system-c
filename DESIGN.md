---
version: 1
name: SYSTEM-C Platform
description: Système de design de SYSTEM-C Platform, application d'administration (CRM des affiliés et des utilisateurs de robots, programmes Academy, commandes). Noir et or, sobre et institutionnel ; univers du registre et du sceau. Source de vérité des valeurs : platform/static/css/systemc.css.

colors:
  black: "#000000"
  nav-hover: "#17150f"
  nav-line: "#2a2618"
  nav-text: "#d6d2c8"
  nav-muted: "#9c978b"
  gold: "#c9a44c"
  gold-light: "#e5c97f"
  gold-deep: "#6b4f0e"
  paper: "#f5f5f3"
  surface: "#ffffff"
  ink: "#17150f"
  stone: "#57534b"
  muted: "#6f6b62"
  rule: "#dfddd8"
  rule-strong: "#c9c5ba"
  ok: "#1e6b45"
  ok-bg: "#e6f2eb"
  wait: "#7f5300"
  wait-bg: "#fbf0db"
  stop: "#a3261c"
  stop-bg: "#fbe8e6"
  demo: "#1f4e89"
  demo-bg: "#e7eef8"
  focus: "{colors.gold-deep} sur fond clair, {colors.gold} sur fond noir"

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

La navigation est un bandeau vertical **noir franc** (`{colors.black}`), seul aplat sombre de l'application. Le contenu vit sur un papier neutre (`{colors.paper}`) avec des cartes blanches (`{colors.surface}`) bordées d'un filet (`{colors.rule}`). L'**or** (`{colors.gold}`) est l'unique accent : il marque l'action principale d'une zone, la rubrique active et le filet de signature. Sur fond clair, l'or devient **or profond** (`{colors.gold-deep}`) pour les liens, le code et l'anneau de focus, afin de rester lisible.

**Signature.** Un filet d'or vertical de 2 px (`.sc-declared`) précède toute information « déclarée, non vérifiée » : statut d'un robot, étape Deriv, paiement confirmé à la main. Il ne sert à rien d'autre.

**Moment.** Le registre « À traiter » du tableau de bord : une colonne de chiffres en serif, alignés à droite et séparés par des filets, avec le libellé et une seule action par ligne. L'or n'y marque que la ligne la plus urgente.

**Caractéristiques :**
- un fond noir, un fond papier, des cartes blanches ; pas d'ombre, la profondeur vient des filets et des paliers de surface ;
- un seul accent (or), utilisé une ou deux fois par écran ;
- une serif (Source Serif 4, 600) pour les titres et les chiffres clés, une sans (IBM Plex Sans, 400 et 500) pour tout le reste ;
- des états toujours écrits en mots, avec une icône, jamais par la couleur seule.

## Colors

> Contrastes mesurés selon WCAG 2.2 (2026-11-11).

### Marque et accent
- **Noir** (`{colors.black}`) : barre latérale, menu mobile, côté gauche de la connexion. Voulu franc, par décision du responsable.
- **Or** (`{colors.gold}`) : fond du bouton principal (texte noir dessus : 8,9:1), rubrique active, filets de signature, puce de la chronologie, anneau de focus sur fond noir (8,9:1).
- **Or clair** (`{colors.gold-light}`) : survol du bouton principal.
- **Or profond** (`{colors.gold-deep}`) : liens, code (`MAX_TRADES`), case cochée, anneau de focus sur fond clair (7,6:1 sur blanc, 7,0:1 sur papier). L'or simple sur papier ne fait que 2,2:1 : jamais comme texte ni comme focus sur fond clair.

### Surfaces
- **Papier** (`{colors.paper}`) : fond des pages.
- **Surface** (`{colors.surface}`) : cartes, champs, tableaux.
- **Filet** (`{colors.rule}`) et **filet appuyé** (`{colors.rule-strong}`) : séparations, bordures de champs.
- **Navigation** : texte `{colors.nav-text}` (13,9:1 sur noir), texte atténué `{colors.nav-muted}` (7,2:1), survol `{colors.nav-hover}`, filet `{colors.nav-line}`.

### Texte (trois rôles)
- **Encre** (`{colors.ink}`) : texte principal (16,7:1 sur papier).
- **Pierre** (`{colors.stone}`) : texte secondaire (7,7:1 sur blanc).
- **Atténué** (`{colors.muted}`) : libellés de listes de définitions, métadonnées, en-têtes de tableau, mention d'absence « Non renseigné » (4,9:1 sur papier, 5,3:1 sur blanc).

### États (fond pâle, texte foncé, bordure intermédiaire)
| État | Texte / fond | Contraste | Usage |
|---|---|---|---|
| Correct | `{colors.ok}` / `{colors.ok-bg}` | 5,6:1 | Validée, appliquée, payée, accès ouvert |
| Attente | `{colors.wait}` / `{colors.wait-bg}` | 5,9:1 | À configurer, en attente de paiement |
| Arrêt | `{colors.stop}` / `{colors.stop-bg}` | 6,2:1 | En retard, remboursée, erreurs |
| Compte réel | blanc / `{colors.stop}` | 7,4:1 | Badge « Réel », toujours avec l'icône octogone |
| Démo | `{colors.demo}` / `{colors.demo-bg}` | 7,2:1 | Badge « Démo » |
| Neutre | `#46433c` / `#eeede9` | 8,4:1 | En pause, annulée, accès fermé |

## Typography

### Familles
- **Source Serif 4**, graisse 600 : titres de page, titres de carte importants, chiffres du registre et des résumés.
- **IBM Plex Sans**, 400 et 500 (600 rare) : interface, tableaux, formulaires.
- Les deux polices sont servies depuis le serveur (licence SIL OFL 1.1), jamais depuis un CDN.

### Hiérarchie
| Rôle | Taille | Graisse | Police |
|---|---|---|---|
| Titre de page | 28px | 600 | Serif |
| Titre de section | 20px | 600 | Serif |
| Chiffre du registre | 40px (28px sur téléphone) | 600 | Serif, chiffres tabulaires |
| Texte courant | 15px, interligne 1,55 | 400 | Sans |
| Libellé de champ | 14px | 500 | Sans |
| Petit texte, en-tête de tableau | 14px | 400 ou 500 | Sans |
| Aide, badge, mention déclarée | 13px | 400 ou 500 | Sans |

### Principes
- Casse de phrase partout : jamais de capitales espacées (« Inscription Deriv », pas « INSCRIPTION DERIV »).
- Hiérarchie par la taille et la couleur, pas par la graisse.
- Chiffres tabulaires dans les tableaux et les montants ; un seul format : `12 500,00 USD`.
- Rien sous 13px. Pas d'italique d'insistance (seule la devise latine, une citation, est en italique).
- Titres équilibrés (`text-wrap: balance`).

## Layout

### Espacement
Grille de 4px : 4, 8, 16, 24, 40, 64 (`{spacing.1}` à `{spacing.6}`). Plus petit à l'intérieur d'un groupe qu'entre deux groupes.

### Structure
- Barre latérale fixe de `{spacing.sidebar}` à gauche ; contenu fluide, limité à `{spacing.content-max}`.
- Barre supérieure collante de 56px ; `scroll-padding-top` de 80px pour qu'un élément focalisé ne passe jamais dessous.
- Fiches : colonne d'informations à gauche, actions et historiques à droite.
- Listes : filtre en carte, puis tableau dans une carte, puis pagination.

### Responsive
- Sous 992px, la barre latérale devient un menu plein écran (fond noir).
- Sous 768px, les filtres et les colonnes passent en pleine largeur ; les tableaux défilent dans leur carte, jamais la page (WCAG 1.4.10, vérifié à 390px).
- Écran tactile : boutons, liens de pagination et champs de 44px au moins ; champs en 16px sur téléphone, pour que le navigateur n'agrandisse pas la page.

## Elevation & Depth

Aucune ombre portée. La profondeur vient de trois paliers (noir, papier, blanc) et des filets. Seul relief : le registre « À traiter » porte un filet d'or de 3px en haut.

## Shapes

| Élément | Rayon |
|---|---|
| Petits repères (cases du `+` des sections repliables) | `{rounded.xs}` |
| Boutons, champs, bandeaux, sections repliables | `{rounded.sm}` |
| Cartes, registre, résumés | `{rounded.md}` |
| Badges d'état | `{rounded.pill}` |

## Components

### Navigation
Rangées de 36px (44px sur mobile), icône dans une colonne fixe, titres de groupe en casse de phrase (« Gestion des robots »). La rubrique active : fond `{colors.nav-hover}`, filet d'or à gauche, texte or.

### Boutons
- **Principal** : fond or, texte noir. Un seul par zone ; il marque l'action la plus importante.
- **Secondaire** : contour neutre (`{colors.rule-strong}`), texte encre. C'est le cas par défaut des actions qui ne sont pas les plus urgentes.
- **Accent secondaire** (contour or profond) : réservé à l'action positive d'une fiche (« Modifier », « Marquer faite »).
- **Danger** : contour rouge (`{colors.stop}`), pour désactiver, annuler ou rembourser, toujours avec une confirmation.
- Survol : changement de couleur en 150ms ; appui : réduction à 98 %.

### Formulaires
Libellé visible au-dessus de chaque champ, astérisque rouge pour les champs obligatoires, aide en dessous, erreur sous le champ. Un résumé d'erreurs en tête du formulaire prend le focus et pointe vers chaque champ. Les fiches saisies pour un tiers (affilié, membre) désactivent le remplissage automatique du navigateur. Jamais de champ pour un mot de passe de courtier, un jeton ou une donnée bancaire.

### Cartes et sections repliables
Carte blanche, filet `{colors.rule}`, en-tête séparé par un filet. Une carte ne contient pas d'autres cartes : à l'intérieur, les colonnes se séparent par des filets (suivi Deriv). Les formulaires secondaires sont repliés dans une section `+` / `−` qui expose son état.

### Badges et mentions
- Badge d'état : icône et mot, couleur d'état, forme de pilule, 13px.
- Absence : « Non renseigné », « Jamais déclarée », etc., en texte atténué, pour ne pas ressembler à une donnée.
- Mention déclarée (`.sc-declared`) : filet d'or de 2px, texte atténué de 13px.

### Composants propres au produit
- **Registre « À traiter »** : chiffre en serif à gauche (rouge si urgent, grisé si nul), libellé et raison au centre, une action à droite.
- **Résumés** : deux registres côte à côte, libellé à gauche, chiffre en serif aligné à droite.
- **Chronologie** : filet vertical, puce d'or, ligne de métadonnées « le … , par … », puis le contenu.

### Tableau de bord en verre fumé (exception)
Demandé par le responsable d'après une maquette « glassmorphism ». Il ne s'applique qu'au tableau de bord (classe `sc-glass-page` sur `<body>`) ; les autres écrans gardent le papier et les filets.
- **Fond :** dégradés radiaux or et ambre sur `#0b0a08`, générés en CSS (pas de photo).
- **Verre :** panneau `rgba(22, 19, 14, .62)`, flou `blur(24px) saturate(140%)`, filet blanc à 10 %, rayon 24px (panneau) ou 20px (widget), 16px (tuile).
- **Texte sur verre :** `#f3eee3` (13,2:1 sur la zone la plus claire), secondaire `#c8c0ae` (8,4:1), atténué `#a59c88` (5,6:1).
- **Graphiques (skill dataviz) :** SVG calculé sur le serveur (`apps/core/charts.py`), barres de 24 unités au plus, bout arrondi de 4 et base carrée, période en cours en or, trait de 2 et aire à 10 %, grille en filet. Infobulle au survol et au clavier (flèches), tableau « Voir les données » pour chaque graphique. Les répartitions par statut sont une liste de jauges (`<meter>`) d'une seule teinte, pas un anneau.
- **Widget mis en avant (`is-feature`) :** voile or à 34 % ; texte secondaire à 4,6:1 au pire.
- **Repli :** fond plein `#1b1813` sans `backdrop-filter` ou avec `prefers-reduced-transparency`.
- Les jetons `--g-*` sont en fin de `systemc.css`, sous « Tableau de bord en verre fumé ».

## Do's and Don'ts

### Do
- Dire ce qui est déclaré et non vérifié, avec le filet d'or.
- Garder l'or pour une seule chose par zone.
- Écrire les états en mots, avec une icône.
- Relier les métadonnées par des mots (« le 09/11/2026, attribuée à … »), pas par un point médian.
- Vérifier chaque nouvelle page à 390px, au clavier et avec axe.

### Don't
- Pas de dégradé, de lueur, d'ombre colorée ni de verre dépoli, sauf l'exception du tableau de bord ci-dessus.
- Pas de violet ni de bleu de marque générique ; le bleu ne sert qu'au badge « Démo ».
- Pas de capitales espacées, d'émoji, de point d'exclamation ni de mot publicitaire.
- Pas de tiret long dans les textes.
- Pas de carte dans une carte dans une carte.
- Pas de CDN, de police distante, de script ni de style en ligne (CSP stricte).
- Pas de chiffre inventé ni de témoignage : seulement des données réelles ou marquées « [Démo] ».
