# Skills tierces du projet : provenance et revue

Ces skills sont des instructions pour Claude Code, chargées automatiquement dans les sessions ouvertes sur ce dépôt. Elles ne contiennent **aucun script ni exécutable** : uniquement du Markdown.

Chaque skill a été lue intégralement avant installation. Elle est figée à un commit précis : une mise à jour en amont n'est jamais récupérée automatiquement.

| Skill | Source | Commit figé | Licence | Rôle |
|---|---|---|---|---|
| `frontend-design` | [anthropics/skills](https://github.com/anthropics/skills/tree/41bbe19d1a1a7eaab5e7bb9050a417e5c6cffc8f/skills/frontend-design) (officiel Anthropic) | `41bbe19d1a1a7eaab5e7bb9050a417e5c6cffc8f` (2026-09-03) | Apache 2.0 (`frontend-design/LICENSE.txt`) | Direction visuelle, typographie, éviter les rendus « génériques » |
| `frontend-design-audit` | [mistyhx/frontend-design-audit](https://github.com/mistyhx/frontend-design-audit/tree/c0fae73d6a4911d59f4658cb13103e9e6f51eeb3) | `c0fae73d6a4911d59f4658cb13103e9e6f51eeb3` | MIT (`frontend-design-audit/LICENSE`) | Audit d'ergonomie selon 15 principes, puis corrections |

## Empreintes SHA-256 des fichiers téléchargés

```
d91970639e9f5c37682ac7ab60094d35f1c7c1f38d731bd56396563aee10c1d3  frontend-design/SKILL.md
0d542e0c8804e39aa7f37eb00da5a762149dc682d7829451287e11b938e94594  frontend-design/LICENSE.txt
f2e3ccf4ec24d3418b731e6e8045403ab6bcd4bfcd9afa032e6ded12d45f9437  frontend-design-audit/SKILL.md   (avant modification)
9797995b7cba88bb8cc747bed4a8dd869af28a7c8ef627a71ee31ec5b87e776a  frontend-design-audit/LICENSE
859a47e391c13d1555270554fdb4c888de91ed76ae8ddbbd72a68e178cf27814  frontend-design-audit/references/heuristics.md
678dd8f7edd701ce327bac010674ef81fb8e53afd4ff25b1c1837c993fc0c205  frontend-design-audit/references/patterns.md
```

## Modification locale

`frontend-design-audit/SKILL.md` : les chemins `../../../references/` (structure du dépôt d'origine) ont été remplacés par `references/`, où les fichiers sont installés ici. Aucun autre changement.

## Revue de sécurité (2026-11-09)

- Aucune commande système, aucun téléchargement, aucune installation de paquet demandés par les skills.
- Seul accès réseau mentionné : `frontend-design-audit` peut lire une page web **quand on lui demande d'auditer une URL**.
- Aucune instruction relative aux secrets, aux identifiants ou à l'envoi de données.

## Mettre à jour une skill

1. Relire le nouveau contenu en entier (les instructions d'une skill s'exécutent avec les droits de l'agent).
2. Remplacer les fichiers, mettre à jour le commit figé et les empreintes ci-dessus.
3. Commiter avec un message qui cite le nouveau commit.

## Réutiliser ces skills dans un autre projet

Copier le dossier `.claude/skills/` (avec ce fichier et les licences) à la racine de l'autre dépôt. Voir aussi la section correspondante de `CLAUDE.md`.
