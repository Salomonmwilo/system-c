# Skills tierces du projet : provenance et revue

Ces skills sont des instructions pour Claude Code, chargées automatiquement dans les sessions ouvertes sur ce dépôt. `frontend-design` et `frontend-design-audit` ne contiennent que du Markdown. `ui-ux-pro-max` et `unslop` contiennent aussi des scripts, audités ci-dessous.

Chaque skill a été lue intégralement avant installation. Elle est figée à un commit précis : une mise à jour en amont n'est jamais récupérée automatiquement.

| Skill | Source | Commit figé | Licence | Rôle |
|---|---|---|---|---|
| `frontend-design` | [anthropics/skills](https://github.com/anthropics/skills/tree/41bbe19d1a1a7eaab5e7bb9050a417e5c6cffc8f/skills/frontend-design) (officiel Anthropic) | `41bbe19d1a1a7eaab5e7bb9050a417e5c6cffc8f` (2026-09-03) | Apache 2.0 (`frontend-design/LICENSE.txt`) | Direction visuelle, typographie, éviter les rendus « génériques » |
| `frontend-design-audit` | [mistyhx/frontend-design-audit](https://github.com/mistyhx/frontend-design-audit/tree/c0fae73d6a4911d59f4658cb13103e9e6f51eeb3) | `c0fae73d6a4911d59f4658cb13103e9e6f51eeb3` | MIT (`frontend-design-audit/LICENSE`) | Audit d'ergonomie selon 15 principes, puis corrections |
| `ui-ux-pro-max` | [nextlevelbuilder/ui-ux-pro-max-skill](https://github.com/nextlevelbuilder/ui-ux-pro-max-skill/tree/4f2dbb67e64969a9a30ab00742f2d55d66ddec2b/.claude/skills/ui-ux-pro-max) | `4f2dbb67e64969a9a30ab00742f2d55d66ddec2b` | MIT (`ui-ux-pro-max/LICENSE`) | Base de connaissances consultable : 192 profils produits, 74 typographies, 120 règles d'ergonomie, styles, palettes |
| `unslop` | [heydamir/unslop](https://github.com/heydamir/unslop/tree/97daa3eb365670ea3f87ed85356cbfcee18105a5/skills/unslop) | `97daa3eb365670ea3f87ed85356cbfcee18105a5` | CC BY 4.0 (`unslop/LICENSE`), auteur : Damir Sokolovsky ([@heydamir](https://x.com/heydamir)) | Méthode en neuf passes pour retirer l'aspect « généré » et donner du caractère |
| `web-interface-guidelines` | Règles : [vercel-labs/web-interface-guidelines](https://github.com/vercel-labs/web-interface-guidelines/tree/434b7f91364665f2f733b310ec54809bf8f37937) ; enveloppe d'origine : [vercel-labs/agent-skills](https://github.com/vercel-labs/agent-skills/tree/1a2c79d4e6c4a2283dc2c614b6538cbe1ed5ca62/skills/web-design-guidelines) | `434b7f91364665f2f733b310ec54809bf8f37937` (2026-10-05) et `1a2c79d4e6c4a2283dc2c614b6538cbe1ed5ca62` (2026-10-27) | MIT (`web-interface-guidelines/LICENSE` ; MIT déclaré dans le README de agent-skills) | Revue du code d'interface selon les règles de Vercel : accessibilité, focus, formulaires, typographie, contenus, navigation, tactile |
| `accessibility` | [addyosmani/web-quality-skills](https://github.com/addyosmani/web-quality-skills/tree/afa8da942115f2961fdbfa80807ea0b232ff6c00/skills/accessibility) | `afa8da942115f2961fdbfa80807ea0b232ff6c00` (2026-08-24) | MIT (`accessibility/LICENSE`), auteur : Addy Osmani | Audit WCAG 2.2 fondé sur les pages rendues (Lighthouse ou axe), puis corrections |

## Empreintes SHA-256 des fichiers téléchargés

Troisième lot (2026-11-11) :

```
f4647ca866a3accf763777f83e7682954f0187cd6bea7eea0399796652414e8f  agent-skills/skills/web-design-guidelines/SKILL.md   (non copié : remplacé par une enveloppe locale)
d246b026f4f29b5823a9cc857f9edf3d2507002e055e32040cadeaf3b38e0234  web-interface-guidelines/command.md
6cd1609c9c12233507cdd2ce0d32e9a721e3c27494951be06b90090deeeb7af2  web-interface-guidelines/LICENSE
267fb2a0707d6142f2871f22688203a42ba21291a2aa200fb740936e41362b5d  accessibility/SKILL.md   (avant modification)
f10e238dd4dd3c4f51134c2056bc02d3dd4f8fb6ccc9145c2c1ba7aab4d58140  accessibility/references/A11Y-PATTERNS.md
16683e025e3833d931c9d880645d98a448827f97e10189b6c8f12c832e7a2361  accessibility/references/WCAG.md
c122223ac43e86421958e18623979942c21b642951e2e3736dcb63eff13587c3  accessibility/LICENSE
```

Deuxième lot (2026-11-09) :

```
14f43337edfbf7822e091428e4ae0c6f92f86e3353deda6a30f6613121e2cf2d  ui-ux-pro-max/SKILL.md   (avant modification)
738f69dfa83db5c347c678fb9d90e560877059f0de93a327c39001bff92dc014  ui-ux-pro-max/LICENSE
19afd7f1841316ddff3f854ea8ead675c738e08b30c41e51a8f1822fa0111947  unslop/SKILL.md
9ba9550ad48438d0836ddab3da480b3b69ffa0aac7b7878b5a0039e7ab429411  unslop/LICENSE
```

Premier lot :

```
d91970639e9f5c37682ac7ab60094d35f1c7c1f38d731bd56396563aee10c1d3  frontend-design/SKILL.md
0d542e0c8804e39aa7f37eb00da5a762149dc682d7829451287e11b938e94594  frontend-design/LICENSE.txt
f2e3ccf4ec24d3418b731e6e8045403ab6bcd4bfcd9afa032e6ded12d45f9437  frontend-design-audit/SKILL.md   (avant modification)
9797995b7cba88bb8cc747bed4a8dd869af28a7c8ef627a71ee31ec5b87e776a  frontend-design-audit/LICENSE
859a47e391c13d1555270554fdb4c888de91ed76ae8ddbbd72a68e178cf27814  frontend-design-audit/references/heuristics.md
678dd8f7edd701ce327bac010674ef81fb8e53afd4ff25b1c1837c993fc0c205  frontend-design-audit/references/patterns.md
```

## Modifications locales

- `frontend-design-audit/SKILL.md` : les chemins `../../../references/` (structure du dépôt d'origine) ont été remplacés par `references/`, où les fichiers sont installés ici.
- `ui-ux-pro-max/SKILL.md` : `${CLAUDE_PLUGIN_ROOT}/.claude/skills/ui-ux-pro-max` remplacé par `.claude/skills/ui-ux-pro-max` (chemin depuis la racine du dépôt), la skill n'étant pas installée comme extension.
- `ui-ux-pro-max` : seule la skill principale est copiée, sans `scripts/tests/` ni les sous-skills `banner-design`, `brand`, `design`, `design-system`, `slides` et `ui-styling` du même dépôt.
- `web-interface-guidelines/SKILL.md` : enveloppe écrite pour ce projet. L'original télécharge les règles depuis la branche `main` à chaque utilisation ; ici, elles sont lues dans `command.md`, figé au commit indiqué. Elle ajoute les exceptions du projet : casse de phrase en français, guillemets français, pas de règles React, pas de style ni de script en ligne.
- `accessibility/SKILL.md` : le lien vers la skill voisine `web-quality-audit`, non installée, est remplacé par une mention.

Aucun autre changement.

## Candidats écartés (2026-11-09)

- `Leonxlnx/taste-skill` (MIT) : conçu pour des sites vitrines d'entreprise (accroches, photographies, effets 3D, composants animés) ; 41 Mo. Hors sujet pour un CRM d'administration.
- `superdesigndev/superdesign-skill` : non examinée en détail ; sa description la dit « propulsée par superdesign.dev », un service externe, ce que le projet exclut.
- Recueils géants (centaines de skills non vérifiables une à une) : écartés par prudence.

## Revue de sécurité (2026-11-11)

- `web-interface-guidelines` : liste de règles en Markdown. Aucune commande. L'instruction d'origine de télécharger les règles à chaque usage est retirée, pour qu'elles ne changent pas sans relecture.
- `accessibility` et ses deux références : Markdown et exemples de code. Les seules commandes citées (`npx lighthouse`, `axe`) sont facultatives et visent une page fournie par l'utilisateur. Aucune instruction relative aux secrets, aux identifiants ou à l'envoi de données.

## Revue de sécurité (2026-11-09)

- `frontend-design`, `frontend-design-audit` : aucune commande, aucun téléchargement. `frontend-design-audit` peut lire une page web **quand on lui demande d'auditer une URL**.
- `ui-ux-pro-max/scripts/*.py` (bibliothèque standard Python uniquement) :
  - aucun accès réseau (`urllib.parse` sert seulement à analyser des chaînes), aucun `subprocess`, aucun `eval` ;
  - recherche en lecture seule dans `data/*.csv` ;
  - écriture uniquement avec `--persist`, dans `design-system/<projet>/` du dossier indiqué par `--output-dir`, sans écraser un fichier existant sans `--force`.
- `unslop/scripts/snapshot.mjs` : capture une URL **fournie par l'utilisateur** et ses ressources (Playwright), écrit le fichier demandé.
- `unslop/scripts/story.mjs` : rendu vidéo facultatif.
  - Serveur HTTP local sur 127.0.0.1, qui refuse les chemins hors du dossier ;
  - appel de `ffmpeg` avec des arguments fixes ;
  - supprime uniquement son dossier temporaire `.story-frames`.
- Aucune instruction relative aux secrets, aux identifiants ou à l'envoi de données.
- **Exécution des scripts :** dans cette session, l'exécution du script de recherche de `ui-ux-pro-max` a été refusée par le contrôle automatique de sécurité (code d'origine externe). La base a donc été consultée en lisant directement ses fichiers CSV. Pour autoriser le script, ajoutez une règle de permission Bash dans les réglages de Claude Code, par exemple pour `python3 .claude/skills/ui-ux-pro-max/scripts/search.py`.

## Mettre à jour une skill

1. Relire le nouveau contenu en entier (les instructions d'une skill s'exécutent avec les droits de l'agent).
2. Remplacer les fichiers, mettre à jour le commit figé et les empreintes ci-dessus.
3. Commiter avec un message qui cite le nouveau commit.

## Réutiliser ces skills dans un autre projet

Copier le dossier `.claude/skills/` (avec ce fichier et les licences) à la racine de l'autre dépôt. Voir aussi la section correspondante de `CLAUDE.md`.
