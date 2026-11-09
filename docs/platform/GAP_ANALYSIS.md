# SYSTEM-C — Analyse des écarts (vision SYSTEM-C Platform)
> **Amendement rév. 2 (2026-11-09).** Le §2.3 (BOT MANAGEMENT) décrivait un agent, des commandes et une intégration technique. Ces lignes sont **retirées** : le module est un CRM administratif (`NEW_PROJECT_DIRECTION.md` §6.4). Les écarts restants sont la gestion des affiliés, des configurations déclarées, des interventions et des tâches.


Compare l'existant décrit dans `CURRENT_STATE.md` à la vision produit : trois modules (ACADEMY, PARTNERS, BOT MANAGEMENT) et les objectifs techniques transverses.

Légende de complexité : **S** (≤ 2 jours), **M** (≈ 1 semaine), **L** (2–4 semaines), **XL** (> 1 mois). Estimations indicatives pour une personne, à affiner en phase de cadrage.

---

## 1. Synthèse

| Domaine | Existant | Écart | Réutilisable |
|---|---|---|---|
| ACADEMY | Contenu pédagogique rédigé (8 séquences Match/Differs, 6 compétences, guide) dans la page | Aucun modèle de cours, leçons, inscription, exercices, évaluations ou suivi | Contenu, ton, structure en séquences |
| PARTNERS | Lien d'affiliation codé en dur, bouton WhatsApp | Aucune gestion de prospects, de statuts, de relances, ni de liens multiples | Lien d'affiliation (à externaliser), mentions de transparence |
| BOT MANAGEMENT | Néant (seulement du contenu sur Differs / Over-Under) | Tout : utilisateurs-bots, environnements démo/réel, configuration, supervision, rapports, incidents, communication avec le VPS | Vocabulaire et avertissements |
| Authentification | Néant | Tout | — |
| Base de données | Néant | Tout (PostgreSQL) | — |
| Multi-organisation | Néant | Tout | — |
| RBAC | Néant | Tout | — |
| Français / anglais | Oui, côté client, 219 clés | Externalisation des contenus, traductions de données dynamiques | Dictionnaire FR/EN, logique de bascule |
| Responsive | Oui (points de rupture 950/700/420 px) | Vérification des vues d'administration | Feuilles de style, tokens |
| Intégration bots Python | Néant | Tout | — |

**Lecture globale** : les écarts sont structurels (aucun backend), pas de qualité. La partie vitrine est un actif à préserver ; la plateforme doit être ajoutée à côté, sans transformer la page actuelle.

---

## 2. Écarts par module

### 2.1 ACADEMY

| Besoin de la vision | État actuel | Écart | Remédiation proposée | Cplx |
|---|---|---|---|---|
| Programmes autonomes | Un programme « Cohorte Alpha » (texte) et un module Match/Differs (8 séquences dépliables) | Pas de modèle `programme → cours → leçon` ; contenu figé dans le HTML | Modèle de données éducatif ; import initial des 8 séquences depuis `index.html` | M |
| Cours et leçons | Séquences avec objectif et exercice | Pas de contenu structuré, pas de versionnage, pas de médias gérés | Tables `course`, `lesson` avec contenu localisé FR/EN ; médias via stockage (voir §4) | M |
| Inscription d'étudiants | Néant | Compte, inscription, statut | Authentification + `enrollment` (organisation, utilisateur, programme, statut) | L |
| Exercices et évaluations | Questionnaire d'éligibilité (règles métier, pas pédagogiques) | Moteur d'exercices et de quiz, correction, tentatives | Modèle `exercise`, `submission`, notation déterministe ; **aucune notation liée au compte démo** (la note « Assessment » du module exclut le solde) | L |
| Suivi de progression | Néant | Progression par leçon, dates, complétion | `progress` par inscription et leçon, événements horodatés | M |
| Certificat | Mention « certificat interne, sans valeur officielle » | Éviter toute promesse de certification | Attestation interne générée seulement si l'exigence est validée (§6) | S |

**Point d'attention** : le contenu Match/Differs est déjà public. Le transformer en parcours payant ou exclusif modifie le statut juridique de la communication ; à valider (§6).

### 2.2 PARTNERS

| Besoin | État actuel | Écart | Remédiation proposée | Cplx |
|---|---|---|---|---|
| Gestion des prospects (leads) | Le questionnaire ne stocke rien (choix délibéré, v4) | Pas de capture, pas de consentement, pas de rétention | Formulaire de contact **séparé** avec consentement explicite et date ; table `lead` | L |
| Gestion des liens Deriv | Lien codé en dur (`t.deriv.link?t=…`) dans le HTML | Pas de registre de liens, pas de campagnes ni de suivi | Table `referral_link` (libellé, code, pays, actif, date de révision) ; affichage piloté par configuration | M |
| Suivi d'onboarding | Néant | Statuts (nouveau, contacté, éligible, inscrit, vérifié, démo actif, abandonné) | Table `onboarding_status` avec historique immuable | M |
| Historique de relances | Néant | Journal de suivi par prospect | Table `follow_up` (auteur, date, canal, résultat) ; jamais de modification, seulement ajout | S |
| Rôles | Néant | Accès restreint aux données personnelles de prospects | RBAC (voir §3) | — |

**Point d'attention majeur** : la politique actuelle (« rien n'est stocké ») est une **promesse publique**. La capture de prospects est une rupture à communiquer clairement, avec un nouvel avis de confidentialité. Ne pas réutiliser le questionnaire existant comme point de capture sans consentement distinct.

### 2.3 BOT MANAGEMENT

| Besoin | État actuel | Écart | Remédiation proposée | Cplx |
|---|---|---|---|---|
| Gestion des utilisateurs-bots | Néant | Entité `bot_user` (propriétaire, organisation, statut) | Modèle de données + écran d'administration | M |
| Types Differs et Over/Under | Contenu pédagogique uniquement | Référentiel de types de contrats, paramètres autorisés | Table de référence `bot_type` avec paramètres bornés et validés côté serveur | M |
| Environnements démo et réel | Néant | Séparation stricte, étiquetage obligatoire, alertes sur le réel | Colonne `environment ∈ {demo, real}` sur toutes les entités bot ; contrôles d'accès renforcés sur `real` | M |
| Configuration des bots | Néant | Versions de configuration, validation, historique, approbation | `bot_config` versionné (immuable par version), diff, approbation à deux personnes pour `real` | L |
| Supervision de service | Néant | Heartbeat, état, dernière activité, latence | Ingestion de heartbeats signés depuis le VPS ; vue d'état | L |
| Rapports autorisés | Néant | Rapports exportables, périmètre limité | Rapports en lecture seule, filtrés par organisation et rôle | M |
| Incidents | Néant | Ouverture, gravité, suivi, clôture, journal | Table `incident` + `incident_event` | M |
| Communication sécurisée avec le VPS Ubuntu | Néant ; VPS absent du dépôt | Pas d'interface, pas de contrat d'API, pas de modèle de menace | Agent poussé depuis le VPS vers la plateforme (sortant uniquement), requêtes signées (HMAC, horodatage, anti-rejeu) — voir `PROPOSED_ARCHITECTURE.md` | L |
| Intégration avec bots Python existants | Néant | Pas de SDK ni de format de message | Petit paquet Python `systemc-agent` (client HTTP signé, sans dépendance lourde) | M |

**Point d'attention critique** : les identifiants de l'API Deriv (jetons) donnent accès à des comptes financiers. La plateforme ne doit **jamais** les stocker en clair ni les afficher. Voir la recommandation R-SEC-3 dans `PROPOSED_ARCHITECTURE.md`.

---

## 3. Écarts sur les objectifs techniques transverses

| Objectif | État actuel | Écart | Remédiation | Cplx |
|---|---|---|---|---|
| Application web responsive | Oui (vitrine) | Vues d'administration à concevoir | Réutiliser `styles.css` et ses tokens ; composants admin dédiés | M |
| Français et anglais | Oui (client, 219 clés) | Données dynamiques localisées ; formats de dates et de montants | Dictionnaire serveur partagé (export JSON depuis `script.js`) ; champs `*_fr` / `*_en` pour les contenus éditables | M |
| Contrôle d'accès basé sur les rôles | Néant | Modèle de rôles et permissions | Rôles globaux (`platform_admin`) et par organisation (`org_admin`, `partner_manager`, `academy_instructor`, `student`, `bot_operator`, `viewer`) ; vérification côté serveur à chaque requête | L |
| PostgreSQL | Néant | Tout | PostgreSQL 16, migrations versionnées (Alembic) | M |
| Authentification sécurisée | Néant | Tout | Sessions serveur, cookies `HttpOnly`/`Secure`/`SameSite=Lax`, mots de passe hachés (Argon2id), verrouillage progressif, TOTP pour les administrateurs | L |
| Architecture multi-organisation | Néant | Tout | Colonne `organization_id` partout où la donnée est locataire ; contraintes de clés étrangères composites ; RLS PostgreSQL en phase 7 | L |
| Isolation stricte des données | Néant | Tests d'isolation inexistants | Tests automatisés « un utilisateur d'une organisation ne voit jamais les données d'une autre » en CI, dès la première entité | M |
| Intégration avec bots Python | Néant | Tout | Voir §2.3 | M |

---

## 4. Écarts d'infrastructure et d'exploitation

| Sujet | État | Écart | Remédiation | Cplx |
|---|---|---|---|---|
| Dépendances | Aucune | Pas de manifeste, pas de verrouillage | `pyproject.toml` (plateforme) et `package.json` **uniquement** si un outil front l'exige ; lockfiles commités | S |
| Build | Aucun | Pas de build pour la plateforme | Image Docker multi-étapes ; site vitrine inchangé (`publish = "public"`) | M |
| Tests | Aucun | Tout | pytest (serveur), tests d'intégration PostgreSQL, Playwright (parcours FR/EN, mobile) — le site vitrine gagne aussi des tests de fumée | M |
| Qualité | Aucune | Lint, format, typage | ruff, mypy (progressif), pre-commit ; HTML validé en CI pour le site vitrine | S |
| CI | GitHub Pages uniquement | Pipeline de tests, scan de dépendances, scan de secrets | GitHub Actions : tests, `pip-audit`, scan de secrets, build d'image | M |
| Sauvegardes | Non applicable | Sauvegardes PostgreSQL chiffrées, test de restauration | `pg_dump` chiffré hors machine, rétention, test trimestriel | M |
| Observabilité | Non applicable | Journaux structurés, erreurs, disponibilité | Journaux JSON sans données personnelles, Sentry optionnel (auto-hébergé ou désactivé) | M |
| Environnements | Un seul (production implicite) | Développement, préproduction, production | Trois environnements ; secrets hors dépôt | M |

---

## 5. Cartographie : préserver / faire évoluer / ajouter

| Élément existant | Décision | Justification |
|---|---|---|
| `public/index.html`, `styles.css`, `script.js` (site vitrine) | **Préserver** à l'identique au départ | Vitrine publique et SEO ; aucun gain à la réécrire |
| Dictionnaire `translations` | **Faire évoluer** : extraire vers un fichier de données partagé | Une seule source de vérité FR/EN |
| Tokens CSS | **Réutiliser** pour la plateforme | Identité visuelle cohérente |
| Lien d'affiliation et constante WhatsApp | **Faire évoluer** : passer en configuration | Gérer plusieurs liens, changer sans republier |
| Formulaire d'éligibilité | **Préserver** ; corriger S1 | Fonctionnalité publique appréciée ; promesse de confidentialité à tenir |
| `netlify.toml` (en-têtes, CSP) | **Préserver** ; étendre aux sous-domaines de la plateforme | Sécurité déjà bien posée |
| `pages.yml` | **Décider** : garder ou retirer (voir migration) | Deux cibles de publication actuellement |
| Contenu Match/Differs | **Réutiliser** comme premier contenu ACADEMY | Déjà rédigé en FR et EN |
| Mécanique de progression et animations | **Préserver** | Sans lien avec la plateforme |
| Backend, base, auth, bots | **Ajouter** | Absents aujourd'hui |

---

## 6. Points de conformité et de contenu (à faire valider par un juriste et le responsable)

Ces points ne relèvent pas du code mais conditionnent la mise en œuvre. Ils sont listés pour que la feuille de route les prenne en compte.

1. **Affiliation** : les conditions d'affiliation Deriv exigent un avertissement visible et peuvent imposer une revue du contenu promotionnel (README, « Avant publication »). Les obligations diffèrent par pays.
2. **Données personnelles des prospects** : la capture de prospects et le suivi de relances imposent une base légale, un consentement distinct, une durée de conservation, un droit d'accès et d'effacement, et un registre des traitements. Obligation supplémentaire si des résidents de l'UE ou du Royaume-Uni sont concernés.
3. **Public visé** : le site cible des jeunes adultes et utilise des messages de formation au trading. Vérifier les conditions d'âge (le questionnaire vérifie l'âge déclaré, pas l'âge réel).
4. **Bots et réel** : l'exploitation de bots sur comptes réels peut relever d'un statut réglementé selon les pays. La plateforme doit commencer en **lecture seule** et ne pas exécuter d'ordres de trading.
5. **Certification** : la mention d'attestation interne doit rester explicitement sans valeur officielle.
6. **Données de comptes financiers** : les jetons d'accès à un compte de trading sont des données sensibles. Limiter leur collecte au strict nécessaire (voir R-SEC-3).
7. **Cohérence des promesses** : le texte « rien n'est stocké » doit être mis à jour dès qu'une capture de données est ajoutée.

---

## 7. Risques principaux

| Risque | Probabilité | Impact | Mitigation |
|---|---|---|---|
| Rupture de la promesse de confidentialité du site vitrine | Élevée si la capture est ajoutée sans mise à jour | Élevé | Corriger S1 ; formulaire séparé ; nouvel avis |
| Fuite de jetons de compte de trading | Moyenne | Très élevé | Ne pas stocker les jetons ; stockage chiffré et rotatif si indispensable |
| Ordres passés sur compte réel par erreur de configuration | Moyenne | Très élevé | Environnements séparés, approbation à deux personnes, mode lecture seule par défaut |
| Fuite entre organisations | Moyenne (sans tests dédiés) | Élevé | Tests d'isolation dès la phase 2 ; RLS en phase 7 |
| Dérive entre traductions HTML et JavaScript | Élevée | Moyen | Source unique (§3) |
| Retard de la conformité sur la phase Partners | Moyenne | Élevé | Gel des fonctionnalités de capture jusqu'à validation |
| Dépendance au VPS non documenté | Moyenne | Moyen | Inventaire du VPS (phase 0 complémentaire) ; contrat d'API versionné |

---

## 8. Informations manquantes (bloquantes pour certaines décisions)

- État réel du déploiement GitHub Pages (actif ou non) : conditionne S2 et S3.
- Contenu, configuration et sécurité du **VPS Ubuntu** (services, ports, utilisateurs, emplacement des bots Python, sauvegardes).
- Liste des bots existants : langage, versions, mode d'exécution, format de journalisation, lieu de stockage des jetons.
- Public et volume attendus (nombre d'étudiants, de prospects, de bots) : conditionne le choix d'hébergement.
- Pays cibles : conditionne la conformité (§6).
- Rapport d'audit mentionné dans le README (v5) : absent du dépôt.
