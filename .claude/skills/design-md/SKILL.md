---
name: design-md
description: Maintain DESIGN.md, the plain-text design system of SYSTEM-C Platform (format introduced by Google Stitch and collected in VoltAgent/awesome-design-md). Use before building or restyling any screen, to read the tokens and rules, and after any change to colours, type, spacing, radii or components, to keep DESIGN.md in step with platform/static/css/systemc.css.
---

# DESIGN.md

`DESIGN.md`, à la racine du dépôt, décrit l'apparence de SYSTEM-C Platform pour les agents de code.
Il complète `CLAUDE.md` (comment construire) par la manière dont l'interface doit paraître.

## Format

Celui des fichiers de VoltAgent/awesome-design-md (exemples figés dans `references/`) :

1. un en-tête YAML : `colors`, `typography`, `rounded`, `spacing`, avec les valeurs exactes ;
2. puis, en Markdown : Overview, Colors, Typography, Layout, Elevation & Depth, Shapes, Components,
   Do's and Don'ts.

Les exemples (`mercury`, banque en ligne ; `ibm`, institutionnel) servent seulement de modèle de forme.
Ne jamais en reprendre les couleurs, les polices ni les composants : l'identité de SYSTEM-C est imposée
(noir et or, sobre et institutionnelle).

## Règles

- La source de vérité reste `platform/static/css/systemc.css` (jetons en tête du fichier). DESIGN.md
  reprend ses valeurs à l'identique ; une différence entre les deux est un défaut à corriger.
- Toute modification de jeton, de composant ou de règle d'interface met DESIGN.md à jour dans le même
  commit.
- Rédiger en français, sans tiret long, avec des faits vérifiables (valeurs, contrastes mesurés).
