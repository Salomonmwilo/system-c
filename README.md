# System-C — site vitrine

Site statique responsive bilingue (français / anglais), conçu pour un déploiement sur Netlify.

## Fichiers
Le site publié se trouve dans le dossier `public/` (seul ce dossier est servi par Netlify) :
- `index.html` : structure et contenu des pages/sections.
- `404.html` : page d'erreur bilingue.
- `og-image.png`, `apple-touch-icon.png` : aperçu de partage (réseaux sociaux, WhatsApp) et icône iOS.
- `robots.txt` : autorise l'indexation.
- `styles.css` : design noir et or, responsive, styles d'accessibilité.
- `script.js` : bascule FR/EN et pré-évaluation locale côté navigateur.
- `favicon.svg` : icône System-C.

À la racine : `netlify.toml` (publication de `public/`, en-têtes de sécurité dont une politique CSP), `.gitignore`.

## Tester en local
Ouvrir `public/index.html` dans un navigateur. Pour un test plus fidèle, lancer un serveur statique local depuis `public/` (par ex. `python3 -m http.server`).

## Déployer sur Netlify
1. Décompresser l'archive.
2. Importer le dossier dans un dépôt GitHub.
3. Dans Netlify, créer un nouveau site depuis Git.
4. Choisir le dépôt. Le répertoire de publication (`public`) est lu depuis `netlify.toml`; aucune commande de build n'est requise.
5. Déployer et tester les liens sur mobile et ordinateur.

## Avant publication — important
1. Les conditions Deriv pour les affiliés demandent un avertissement de risque visible et peuvent exiger que le site promotionnel soit examiné/approuvé avant mise en ligne. Confirmer les exigences applicables à votre compte et pays avec votre Partner Manager.
2. Le lien affilié est fourni par le propriétaire du site : `https://t.deriv.link?t=L9CTBT5XUH3M`.
3. La carte d'électeur de RDC n'est pas présentée comme document accepté : le candidat doit confirmer l'acceptation auprès de Deriv. Les règles peuvent varier.
4. Le questionnaire fonctionne entièrement dans le navigateur et n'envoie pas les réponses à un serveur.
5. Le site ne collecte aucune pièce d'identité et ne fournit pas de conseil financier personnalisé.
6. Vérifier le contenu, les conditions applicables dans le pays ciblé et la conformité locale avant diffusion publique.

## Personnalisation
Modifier les traductions dans `script.js`. Mettre à jour les liens uniquement avec des URLs officielles vérifiées.

## Notes
- Après le premier déploiement, ajouter l'URL définitive dans `og:image` (URL absolue recommandée par certains réseaux) et ajouter une balise `canonical` si un domaine personnalisé est utilisé.
- Ajouter `.netlify` au `.gitignore` (déjà fait) si le site est lié via la CLI.

## Version 3 — décisions du responsable
- Avertissement de risque : texte anglais officiel (Deriv Affiliates Terms R26|03, §1.10) et traduction française affichés ensemble ; l'anglais fait foi.
- Slogan validé par le responsable : « Solus cum plenitudine, inopi est alia ».
- Questionnaire : âge légal, pays autorisé, document accepté par Deriv, appareil, fonds (argent emprunté/essentiel/perdable), compréhension du risque. Trois issues : favorable / à vérifier / ne pas poursuivre.
- Groupe WhatsApp : https://chat.whatsapp.com/JhM2CR2smAa3oKmWvfyWwV (bouton, FAQ et résultat favorable).
- Carte d'électeur RDC : mentionnée comme retour d'expérience de membres, sans garantie ; acceptation à confirmer auprès de Deriv.
- Liens d'aide Deriv adaptés à la langue (FR/EN) ; ajout du guide « Comment vérifier ton profil ».
- Approbation Deriv : en cours de demande auprès du responsable pays après mise en ligne.
- Si un domaine personnalisé est utilisé, mettre à jour `canonical`, `og:url` et `og:image` dans `index.html`.

## Version 4 — confidentialité
- Google Fonts retiré : le site n'appelle plus aucun service externe au chargement (polices système : Georgia pour les titres, police système pour le texte). CSP stricte (`'self'` uniquement).
- Mémorisation de la langue (`localStorage`) supprimée : le site ne stocke rien sur l'appareil. La langue initiale suit la langue du navigateur (lue localement).
- Question FAQ « IA Deriv » supprimée.
- Mention de confidentialité ajoutée dans le pied de page.
- Pour retrouver les polices d'origine (DM Sans / Playfair Display) sans Google : télécharger les fichiers `.woff2`, les placer dans `public/fonts/`, ajouter des règles `@font-face` dans `styles.css` et remplacer les variables `--sans` et `--serif`.

## Version 5 (aperçu, non déployée)
- Suppression des glyphes qui s'affichent en emoji sur iOS (flèches, astérisque), du trait décoratif avant les titres de section et des tirets longs dans les textes.
- Logo System-C intégré (en-tête, pied de page, favicons, image de partage). Le logo d'origine est seulement recadré en disque, non modifié. Source basse résolution (480x279).
- Deux photos placées (section À propos et section finale). Photo à la tribune non utilisée : blason d'institution visible, à confirmer.
- Menu : barre de navigation fixe, bouton Menu avec panneau déroulant sur mobile (Escape, clic extérieur, aria-expanded).
- Liens du contenu et du pied de page soulignés.
- Corrections d'audit non encore appliquées : voir le rapport d'audit.

## Version 6 (aperçu, non déployée)
- Mode clair/sombre : suit le réglage du système au départ ; bouton dans l'en-tête (ordinateur) ou le menu (mobile). Aucun stockage sur l'appareil : le choix n'est pas mémorisé d'une visite à l'autre.
- Section « Le fondateur » (trois photos fournies, formats WebP avec repli JPEG, tailles adaptées). Aucun nom ni titre inventé : à compléter par le responsable.
- Motifs graphiques noir et or en SVG/CSS (grille de discipline, parcours des quatre modules, arcs de la section finale), décoratifs (masqués aux lecteurs d'écran).
- Images à fournir pour compléter (non obtenues, aucun réseau) : voir la liste dans la conversation.

## Version 7 (aperçu, non déployée)
Corrections d'accessibilité issues de l'audit, corroborées par la base UX du skill ui-ux-pro-max (utilisée comme source de recommandations, sans en importer de style ni de police) :
- Questionnaire : validation maison avec résumé d'erreurs (role=alert, focus automatique, liens vers chaque question), message d'erreur par question relié par aria-describedby, textes FR/EN. Le résultat reçoit le focus pour être annoncé.
- Lien « Aller au contenu » : le focus arrive bien sur le contenu.
- Cibles : options du questionnaire d'au moins 44 px de haut ; liens texte d'au moins 40 px.
- Liens externes : mention « s'ouvre dans un nouvel onglet » pour les lecteurs d'écran (FR/EN), y compris le bouton créé par le résultat.
- Libellés de navigation et du bandeau de principes traduits ; slogan balisé lang="la".
- Avertissement de risque : bannière à 12-13 px ; phrase de risque ajoutée sous le bouton « Continuer vers Deriv ».
- Mode clair : correction du contraste du bouton doré au survol (2,2:1 avant, 10:1 après).


## Version 8
- Hero avec photo, voile sombre et pastilles ; séparateurs en losange entre sections.
- Nouvelle section « Ce que tu apprendras » (6 compétences, icônes), cartes du programme illustrées, cartes « Rejoindre ».
- Barre de progression de lecture, apparition douce (désactivée si « réduire les animations »), rubrique active dans le menu.
- Page 404 réparée. Aucune dépendance externe, aucun stockage.

## Déploiement Netlify
Publish directory : `public` — aucune commande de build (voir `netlify.toml`).
