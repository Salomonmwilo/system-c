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
| `taste-skill` (nom : `design-taste-frontend`), **copie partielle** | [Leonxlnx/taste-skill](https://github.com/Leonxlnx/taste-skill/tree/f6b76575f949707b4e3c37cd86cb44b0b98643e8/skills/taste-skill) | `f6b76575f949707b4e3c37cd86cb44b0b98643e8` (2026-11-07) | MIT (`taste-skill/LICENSE`), auteur : Leonxlnx | Règles de rédaction (marques de texte généré), de système, de formulaires et d'accessibilité. Installée à la demande du responsable (2026-11-11). |
| `image-to-code` | [Leonxlnx/imagegen-skills](https://github.com/Leonxlnx/imagegen-skills/tree/beb16b0d0f4dae9a6f5cb04ea41e97b93a54ab8e/skills/image-to-code) | `beb16b0d0f4dae9a6f5cb04ea41e97b93a54ab8e` (2026-10-19) | MIT (`image-to-code/LICENSE`), auteur : Leonxlnx | Traduire une image (maquette, capture) en interface ; règles contre les boîtes imbriquées et les micro-étiquettes |
| `design-md` | Format et exemples : [VoltAgent/awesome-design-md](https://github.com/VoltAgent/awesome-design-md/tree/fcc70284932276d085f01ef9f83edde90b1258cb) | `fcc70284932276d085f01ef9f83edde90b1258cb` (2026-10-28) | MIT (`design-md/LICENSE`) | Tenir `DESIGN.md` (racine du dépôt), le système de design lisible par les agents. `SKILL.md` écrit pour ce projet ; deux exemples figés (`mercury`, `ibm`). |

## Empreintes SHA-256 des fichiers téléchargés

Quatrième lot (2026-11-11) :

```
0c7a5852a5217be79cab422c6d58329b776f0c25bd6da8a7a01707ce75be6206  taste-skill/SKILL.md   (avant modification)
5efe5057a414b9c11c75ec7840eb1536be24aaccc18c6e1cd7f24a41b17959f4  taste-skill/references/*.md   (concaténés par ordre alphabétique, non modifiés)
4575a543ab88dad12ccea7d97e563d0bce5b448b06072e65d3264497dad326df  taste-skill/LICENSE   (identique à image-to-code/LICENSE)
4c060a8064a8b13380bc2ef3d6e6a1d0b1e316aa093cd9807d0ce9e4eeb037fa  image-to-code/SKILL.md   (avant modification)
6d4bdc9a9cf30e7beb593475fdcdbf29f981ea6bd7923f202866145409f87b44  design-md/LICENSE
dabb3683422a9841369b0db53ff13ed375b0b6f019157a5c90e9fca165cc111f  design-md/references/mercury.DESIGN.md
46f6fd65b5e7524fed1133b9b3c0dd619f9a0f145fbb2b87f3675c701a88f3bd  design-md/references/ibm.DESIGN.md
```

`unslop` et `web-interface-guidelines` ont été revérifiés le même jour : l'amont de `unslop` est toujours au commit figé (`97daa3eb`), et la copie locale est identique (seule la licence a été ajoutée).

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
- `taste-skill` : seuls `SKILL.md`, `references/` et la licence sont copiés. Pas de `scripts/` (17 000 lignes), d'`assets/` (38 Mo) ni de `library/`. Dans `SKILL.md` : le crochet `Stop` de l'en-tête est retiré, et une section « Installation dans SYSTEM-C » précise ce qui manque et les règles du projet qui l'emportent.
- `image-to-code/SKILL.md` : section « Utilisation dans SYSTEM-C » ajoutée en tête (pas de génération d'images ici, identité imposée, CSP).

Aucun autre changement.

## Candidats écartés (2026-11-09)

- `Leonxlnx/taste-skill` (MIT) : écartée le 2026-11-09, car conçue pour des sites vitrines. Installée partiellement le 2026-11-11 à la demande du responsable (voir le tableau et la revue de sécurité).
- `superdesigndev/superdesign-skill` : non examinée en détail ; sa description la dit « propulsée par superdesign.dev », un service externe, ce que le projet exclut.
- Recueils géants (centaines de skills non vérifiables une à une) : écartés par prudence.

## Revue de sécurité (2026-11-11), quatrième lot

- **`taste-skill` :**
  - le `SKILL.md` et les 24 références sont lus ; ce sont des règles en Markdown ;
  - les scripts n'ont pas été installés. Leur revue a relevé :
    - le lancement de Chrome en tâche de fond ;
    - des téléchargements depuis Wikimedia Commons, picsum.photos et cdn.jsdelivr.net, et des liens vers Google Fonts ;
    - un crochet `Stop` qui exécutait `gate.mjs` automatiquement.

    Ce sont trop de lignes pour une relecture complète, et cela contredit la règle « aucun CDN ni service externe ».
- **`image-to-code` :** Markdown seul, aucune commande. Son flux principal suppose un outil de génération d'images, absent ici.
- **`design-md` :** deux fichiers de description de marque en Markdown (couleurs, typographie, composants), sans instruction d'exécution.

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
