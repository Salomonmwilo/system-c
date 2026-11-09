> **Document remplacé (2026-11-09).** Cette version supposait une vitrine à préserver. L'orientation actuelle est décrite dans `NEW_PROJECT_DIRECTION.md`. Contenu conservé comme historique.

# SYSTEM-C — Feuille de route par phases

Découpage en phases livrables, chacune avec un critère de sortie vérifiable. Les phases 1 et 2 peuvent commencer dès approbation ; les suivantes dépendent des décisions listées en fin de document.

Complexité : **S** (≤ 2 jours), **M** (≈ 1 semaine), **L** (2–4 semaines), **XL** (> 1 mois). Estimations pour une personne ; à recalibrer après la phase 1.

Ce document ne modifie aucun code. Il n'a pas de caractère contractuel.

---

## Vue d'ensemble

| Phase | Titre | Durée indicative | Dépend de | Impact sur la vitrine |
|---|---|---|---|---|
| 0 | Audit et documentation (ce document) | Terminée | — | Aucun |
| 1 | Stabiliser la vitrine et poser le filet de sécurité | 2 à 3 semaines | Approbation | Correction S1 visible pour les visiteurs sans JS |
| 2 | Socle plateforme : application, base, authentification, RBAC, isolation | 4 à 6 semaines | Phase 1 (tests) ; décision d'hébergement | Aucun |
| 3 | ACADEMY : contenu, inscription, exercices, progression | 4 à 6 semaines | Phase 2 | Aucun (lien vers l'espace membre en fin de phase) |
| 4 | PARTNERS : liens, prospects, onboarding, relances | 3 à 5 semaines | Phase 2 ; validation juridique (§6 `GAP_ANALYSIS.md`) | Formulaire de contact et mise à jour de la confidentialité |
| 5 | BOT MANAGEMENT lecture seule : registre, agent, supervision, incidents | 5 à 7 semaines | Phase 2 ; inventaire du VPS ; R-SEC-3 | Aucun |
| 6 | BOT MANAGEMENT écriture : configuration versionnée et approbations | 4 à 6 semaines | Phase 5 ; gouvernance validée | Aucun |
| 7 | Durcissement : RLS, tests d'intrusion, sauvegardes, observabilité | 3 à 4 semaines | Phases 2 à 6 | Aucun |

Ordre des modules recommandé : **ACADEMY** (valeur immédiate, contenu prêt, risque réglementaire faible) puis **PARTNERS** (dépend de la conformité) puis **BOT MANAGEMENT** (risque le plus élevé, lecture seule d'abord).

---

## Phase 0 — Audit (terminée)

- **Livrables** : `CURRENT_STATE.md`, `GAP_ANALYSIS.md`, `PROPOSED_ARCHITECTURE.md`, `MIGRATION_PLAN.md`, `IMPLEMENTATION_ROADMAP.md`, dans `docs/platform/`.
- **Fichiers modifiés** : aucun fichier de `public/`, de configuration ou de workflow.
- **Critère de sortie** : approbation du responsable des décisions de la section « Décisions attendues » ci-dessous.

---

## Phase 1 — Stabiliser la vitrine

**Objectif** : corriger les constats de sécurité et de confidentialité, et poser le filet de tests avant toute évolution.

| Tâche | Réf. migration | Fichiers | Cplx | Cassant ? | Sécurité |
|---|---|---|---|---|---|
| Captures de référence et tag `v9-baseline` | M-0 | aucun dans `public/` | S | Non | — |
| Tests de fumée Playwright (FR/EN, mobile, sans JS, aucune requête externe) | M-1 | `tests/site/*` | M | Non | Garde-fou confidentialité |
| Masquer le formulaire sans JS et ajouter `<noscript>` (S1) | M-2 | `public/styles.css`, `public/index.html` | S | **Oui, visible sans JS** | Supprime la fuite des réponses dans l'URL |
| Décider de `pages.yml` (S2, S3) | M-3 | `.github/workflows/pages.yml` | S | Possible (liens GitHub Pages) | Une seule politique d'en-têtes |
| Épingler les actions GitHub par SHA | R-DEBT-4 | `.github/workflows/*.yml` | S | Non | Chaîne d'approvisionnement |
| Consolider les tokens de thème | M-6 | `public/styles.css` | S | Non si identique | — |
| Nettoyage documentaire (README, `robots.txt`, `sitemap.xml`, clés inutilisées) | M-7 | `README.md`, `public/robots.txt`, `public/sitemap.xml` | S | Non | — |
| Validation HTML en CI | R-DEBT-3 | `.github/workflows/ci.yml` | S | Non | — |

**Critères de sortie** :
- Tous les tests M-1 passent, y compris « sans JS, aucune réponse dans l'URL ».
- Comparaison visuelle avec `v9-baseline` : identique hors changements approuvés (S1 et ses messages).
- Décision documentée pour `pages.yml`.
- README à jour (aucune mention d'un fichier absent).

**Risques** : le masquage sans JS (S1) est un changement visible pour une minorité d'utilisateurs ; il doit être annoncé dans le README.

---

## Phase 2 — Socle de la plateforme

**Objectif** : une application vide mais sûre : authentification, organisations, rôles, isolation testée, base PostgreSQL, CI.

### Lots

| Lot | Contenu | Fichiers | Cplx |
|---|---|---|---|
| 2.1 Squelette | FastAPI, configuration par variables d'environnement, `/healthz`, Dockerfile non-root, `compose.yml` (PostgreSQL privé), ruff, pytest, CI | `platform/**`, `.github/workflows/ci.yml`, `.gitignore` | M |
| 2.2 Base | SQLAlchemy 2, Alembic, migrations `0001` (identité, organisations, rôles) et `0002` (`audit_log` append-only) | `platform/app/models/*`, `platform/migrations/*` | M |
| 2.3 Authentification | Sessions serveur (cookie `__Host-`), Argon2id, limitation de débit, réinitialisation de mot de passe, TOTP pour administrateurs | `platform/app/auth/*` | L |
| 2.4 Autorisation | RBAC avec refus par défaut, décorateur ou dépendance `authorize`, test qui échoue si une route n'a pas de permission | `platform/app/auth/policy.py`, `platform/tests/test_policy.py` | M |
| 2.5 Multi-organisation | `organization_id` partout, clés composites, contexte d'organisation résolu côté serveur, tests d'isolation | `platform/app/services/tenancy.py`, `platform/tests/test_isolation.py` | L |
| 2.6 Sécurité HTTP | En-têtes, CSP propre à l'application, CSRF, cookies, vérification `Origin` | `platform/app/middleware/*` | S |
| 2.7 i18n serveur | Lecture de `shared/i18n/*.json`, bascule FR/EN de l'application (cookie non-traceur ou paramètre d'URL — à décider) | `platform/app/i18n.py`, `shared/i18n/*` | M |
| 2.8 Hébergement | Déploiement de test sur sous-domaine `app.` (option A VPS ou option B PaaS) | `docs/platform/OPERATIONS.md` (à créer) | M |

**Critères de sortie** :
- Tests d'authentification : mot de passe incorrect, réutilisation de session après déconnexion, expiration, fixation de session.
- Tests d'isolation : un utilisateur de l'organisation A obtient 404 sur les ressources de B, pour chaque type de ressource créé.
- Toute route est couverte par une permission déclarée (test automatique).
- Sauvegarde et restauration d'une base de test effectuées une fois.
- Aucune modification de `public/`.

**Risques** : la complexité est concentrée dans l'authentification et l'isolation. Ne pas passer à la phase 3 tant que les tests d'isolation ne couvrent pas tous les types de ressources.

---

## Phase 3 — ACADEMY

**Objectif** : des étudiants inscrits suivent un programme, font des exercices, et leur progression est suivie.

| Lot | Contenu | Fichiers | Cplx |
|---|---|---|---|
| 3.1 Modèle contenu | `programme`, `course`, `lesson`, `lesson_content` (FR/EN) | `platform/app/models/academy.py`, migration `0003` | M |
| 3.2 Import du module Match/Differs | Script qui lit les 8 séquences (source : `index.html` section `#module`, ou `shared/` si extrait) | `platform/scripts/import_module_content.py` | M |
| 3.3 Inscription | Demande et validation d'inscription par un instructeur ; statuts | `platform/app/services/enrollment.py` | M |
| 3.4 Exercices et évaluations | `exercise`, `submission`, correction déterministe, tentatives | `platform/app/services/assessment.py` | L |
| 3.5 Progression | `progress_event`, complétion de leçon, tableau pour l'étudiant et l'instructeur | `platform/app/services/progress.py`, `platform/templates/academy/*` | M |
| 3.6 Attestation interne | Génération seulement si validée (§6 `GAP_ANALYSIS.md`), mention « sans valeur officielle » | `platform/app/services/attestation.py` | S |
| 3.7 Lien depuis la vitrine | Bouton « Espace membre » dans l'en-tête | `public/index.html`, `shared/i18n/*` | S |

**Critères de sortie** :
- Un instructeur crée un cours, un étudiant s'inscrit, réalise un exercice, sa progression est mise à jour, et un autre étudiant ne voit pas ces données.
- Notation indépendante du solde du compte démo (vérifié par test).
- FR et EN complets pour l'interface et les contenus de la première formation.
- Test de fumée de la vitrine : le nouveau lien n'apparaît qu'après mise en service.

**Risques** : la qualité pédagogique du contenu, et la cohérence entre la version publique et la version membre des 8 séquences. Décider d'une source unique (M-13).

---

## Phase 4 — PARTNERS

**Objectif** : gérer les prospects issus du site, leur onboarding et leurs relances, avec consentement et traçabilité.

| Lot | Contenu | Fichiers | Cplx |
|---|---|---|---|
| 4.1 Registre de liens | `referral_link` : libellé, code, pays, statut actif, dernière revue | `platform/app/models/partners.py`, `platform/app/services/referral.py` | M |
| 4.2 Formulaire de contact | Formulaire **séparé** du questionnaire ; consentement explicite et daté ; finalités | `public/index.html` (nouveau formulaire), `platform/app/routes/leads.py` | M |
| 4.3 Prospects et statuts | `lead`, `onboarding_status`, historique immuable | `platform/app/services/leads.py` | M |
| 4.4 Relances | `follow_up` en ajout seul ; tâches par partenaire | `platform/app/services/follow_up.py` | S |
| 4.5 Droits des personnes | Export et suppression d'un prospect, durée de conservation, journal | `platform/app/services/privacy.py`, `platform/scripts/purge_leads.py` | M |
| 4.6 Mise à jour de la confidentialité | Texte public modifié **dans la même version** que le formulaire (M-8) | `shared/i18n/*.json`, `public/index.html` | S |
| 4.7 Liens : statique ou dynamique | Décision (M-16) | `public/index.html`, éventuellement `public/config.json` | S/M |

**Critères de sortie** :
- Aucun prospect n'est enregistré sans consentement (test).
- Export et suppression fonctionnels, journalisés.
- Texte de confidentialité et formulaire cohérents en FR et EN.
- Validation juridique obtenue (§6 `GAP_ANALYSIS.md`) **avant** la mise en production du formulaire.

**Risques** : conformité et réputation. Ne pas activer le formulaire public sans validation écrite.

---

## Phase 5 — BOT MANAGEMENT (lecture seule)

**Objectif** : voir l'état des bots et les incidents, sans rien modifier à distance.

| Lot | Contenu | Fichiers | Cplx |
|---|---|---|---|
| 5.1 Inventaire | Recensement des bots Python sur le VPS : langage, versions, emplacement, format de journaux, emplacement des jetons | `docs/platform/BOT_INVENTORY.md` (à créer, hors secrets) | S |
| 5.2 Modèle | `bot_user`, `bot_environment` (demo / real, obligatoire), `bot_type` (Differs, Over/Under) | `platform/app/models/bots.py` | M |
| 5.3 Agent | `systemc-agent` : lecture locale, heartbeat, rapports, signature HMAC avec anti-rejeu | `platform/agent/systemc_agent/*` | L |
| 5.4 Ingestion | Endpoints d'agent, vérification de signature, rejets journalisés, révocation | `platform/app/api/agent.py`, `platform/app/auth/agent_signature.py` | L |
| 5.5 Supervision | État, dernière activité, latence, alertes simples | `platform/app/services/monitoring.py`, `platform/templates/bots/*` | M |
| 5.6 Incidents | Ouverture, gravité, suivi, clôture ; journal | `platform/app/services/incidents.py` | M |
| 5.7 Rapports | Rapports en lecture seule, filtrés par organisation et rôle | `platform/app/services/reports.py` | M |
| 5.8 Jetons Deriv | Application de R-SEC-3 : aucun jeton dans la base, empreintes seulement | `platform/app/models/bots.py`, documentation d'exploitation | M |

**Critères de sortie** :
- Un agent signé publie un heartbeat ; une requête non signée, expirée ou rejouée est refusée (tests).
- Un agent révoqué ne peut plus rien envoyer.
- Aucun champ de la base ne contient de jeton (test de schéma).
- Aucun chemin de code n'exécute d'ordre de trading.

**Risques** : dépendance au VPS non documenté (§8 `GAP_ANALYSIS.md`) ; exposition des données de compte si le périmètre du rapport n'est pas strictement défini.

---

## Phase 6 — BOT MANAGEMENT (configuration)

**Objectif** : modifier la configuration des bots de façon versionnée, approuvée et traçable.

| Lot | Contenu | Fichiers | Cplx |
|---|---|---|---|
| 6.1 Gouvernance | Rôles approbateur et opérateur ; règle des deux personnes pour `real` | `platform/app/auth/policy.py` | M |
| 6.2 Versions | `bot_config` et `bot_config_version` immuables, diff, validation des paramètres par type | `platform/app/services/bot_config.py` | L |
| 6.3 Application par l'agent | Application seulement si signature valide et version croissante ; rollback | `platform/agent/systemc_agent/apply.py` | L |
| 6.4 Arrêt d'urgence | Interrupteur par bot et global, journalisé | `platform/app/services/kill_switch.py` | S |
| 6.5 Tests de bout en bout | Scénario complet sur environnement démo ; scénario de refus sur `real` sans approbation | `platform/tests/e2e/*` | M |

**Critères de sortie** :
- Une configuration `real` ne peut pas être appliquée sans deux approbations distinctes (test).
- Un agent refuse une version non signée ou inférieure.
- Revue de sécurité externe effectuée.

**Risques** : impact financier direct sur les utilisateurs. Phase conditionnée à la validation juridique et à la revue de sécurité. Ne pas livrer sans interrupteur d'arrêt.

---

## Phase 7 — Durcissement

| Lot | Contenu | Fichiers | Cplx |
|---|---|---|---|
| 7.1 RLS PostgreSQL | Politiques de ligne par organisation, rôle applicatif sans contournement | `platform/migrations/versions/*_rls.py` | L |
| 7.2 Tests d'intrusion | Test externe de la plateforme et de l'agent ; corrections | rapport hors dépôt | L |
| 7.3 Sauvegardes | Sauvegarde chiffrée hors machine, rétention, restauration testée tous les trimestres | `docs/platform/OPERATIONS.md` | M |
| 7.4 Observabilité | Journaux JSON sans données personnelles, alertes sur échecs d'authentification et rejets d'agent | `platform/app/logging.py` | M |
| 7.5 Mises à jour | Politique de mises à jour des dépendances, scan `pip-audit`, revue mensuelle | `.github/workflows/security.yml` | S |
| 7.6 Documentation d'exploitation | Procédures : incident, révocation d'agent, rotation de secrets, restauration | `docs/platform/OPERATIONS.md` | S |

**Critères de sortie** : tests d'intrusion sans constat critique ouvert ; restauration validée ; procédures d'exploitation relues.

---

## Calendrier indicatif et effort

| Phase | Effort (personnes-semaines) | Cumul |
|---|---|---|
| 1 | 2 à 3 | 2 à 3 |
| 2 | 4 à 6 | 6 à 9 |
| 3 | 4 à 6 | 10 à 15 |
| 4 | 3 à 5 | 13 à 20 (en parallèle possible avec 3 après validation juridique) |
| 5 | 5 à 7 | 18 à 27 |
| 6 | 4 à 6 | 22 à 33 |
| 7 | 3 à 4 | 25 à 37 |

Ces chiffres supposent une personne à temps plein et ne tiennent pas compte des délais juridiques ni de la production de contenu pédagogique. Le contenu (cours, exercices, évaluations) est souvent le goulot d'étranglement réel : à estimer séparément.

---

## Décisions attendues avant la phase 1

1. **Approbation** de la phase 1, en particulier de la correction S1 (formulaire masqué sans JavaScript).
2. **Cible de publication** : Netlify seul ou Netlify et GitHub Pages (R-SEC-2).
3. **Vérification de l'état de GitHub Pages** : actif ou non.

## Décisions attendues avant la phase 2

4. **Hébergement de la plateforme** : VPS existant (option A) ou plateforme managée (option B).
5. **Nom de domaine** et sous-domaine de la plateforme.
6. **Confirmation de la stack** (FastAPI, Jinja2, PostgreSQL) ou choix alternatif.
7. **Inventaire du VPS Ubuntu** (services, utilisateurs, ports, bots, sauvegardes).

## Décisions attendues avant les phases 4 à 6

8. **Validation juridique** : affiliation, données de prospects, public visé, bots sur comptes réels, pays cibles.
9. **Responsable de la gouvernance** des configurations de bots (règle des deux personnes).
10. **Ordre des modules** : ACADEMY en premier (recommandé).

---

## Prochaine action proposée

Après approbation : démarrer la **phase 1** par M-0 et M-1 (filet de tests), puis M-2 (correction S1). Aucun changement de `public/` n'est effectué avant que M-1 soit en place et vert.
