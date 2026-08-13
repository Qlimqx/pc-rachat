# pc-rachat — Design

## Contexte et objectif

Outil en ligne de commande pour estimer la valeur de marché des composants d'un PC d'occasion (CPU, RAM, stockage, carte graphique), afin d'aider à décider combien proposer pour le racheter en vue de revente. L'outil donne une estimation de la **valeur marché des composants** ; la marge de revente reste une décision manuelle de l'utilisateur (pas de calcul de marge intégré, pas de coefficient d'état du PC).

## Architecture

Script Python 3, structuré en modules :

- `cli.py` — point d'entrée. Boucle de saisie interactive (CPU, RAM taille+type, stockage taille+type, GPU optionnel), affichage du résultat.
- `ebay_client.py` — client de l'API eBay Browse (authentification OAuth2 client-credentials, recherche d'annonces d'occasion sur le marketplace `EBAY_FR`).
- `estimator.py` — logique métier d'estimation par composant (CPU/GPU via eBay + fallback ; RAM/stockage via formule).
- `data/reference_prices.json` — table de secours éditable : prix de base par modèle CPU/GPU connu.
- `data/component_rates.json` — tarifs €/Go éditables par type de RAM (DDR3/DDR4/DDR5) et de stockage (HDD/SSD/NVMe).
- `.env` (non versionné) — identifiants API eBay (`EBAY_CLIENT_ID`, `EBAY_CLIENT_SECRET`).
- `.env.example` (versionné) — modèle du fichier `.env`, sans valeurs réelles.

## Flux de données

1. L'utilisateur lance le script. Saisie interactive :
   - CPU : modèle en texte libre (ex: "i5-10400")
   - RAM : taille en Go + type (DDR3/DDR4/DDR5)
   - Stockage : taille en Go + type (HDD/SSD/NVMe)
   - GPU : modèle en texte libre, ou vide si carte graphique intégrée
2. **Estimation CPU et GPU** :
   - Construction d'une requête de recherche eBay (ex: "Intel Core i5-10400 processor"), filtrée sur les annonces d'occasion, marketplace France.
   - Récupération des prix des annonces retournées (jusqu'à ~20), calcul de la **médiane**.
   - Si l'appel API échoue (pas de clé configurée, timeout, quota dépassé, 0 résultat) → recherche du modèle (normalisé : minuscules, espaces réduits) dans `data/reference_prices.json`.
   - Si absent des deux sources → composant marqué **"prix inconnu"**, exclu du total, affiché avec un avertissement clair.
3. **Estimation RAM et stockage** :
   - Aucune recherche eBay. Calcul direct : `taille (Go) × taux €/Go` selon le type, à partir de `data/component_rates.json`.
   - Si le type saisi n'existe pas dans la table → composant marqué "prix inconnu", exclu du total.
4. **Affichage** :
   - Détail par composant (méthode utilisée : "médiane sur N annonces eBay" ou "table de référence" ou "formule €/Go"), et total des composants dont le prix est connu.
   - Si un ou plusieurs composants sont "prix inconnu", le total est explicitement annoncé comme incomplet, avec la liste des composants manquants.

## Intégration API eBay

- Authentification : OAuth2 client credentials flow (App ID + Client Secret), token mis en cache en mémoire pour la durée du script (pas de persistance disque du token).
- Endpoint : `Browse API` (`item_summary/search`), avec :
  - `q` = requête construite à partir du modèle saisi
  - filtre condition = occasion (used)
  - header `X-EBAY-C-MARKETPLACE-ID: EBAY_FR`
- Aucune clé API committée dans le repo. Si `.env` absent ou clés manquantes, l'outil ignore silencieusement eBay et n'utilise que les fallbacks (RAM/stockage fonctionnent toujours ; CPU/GPU utilisent directement la table de référence).

## Gestion des erreurs

- Erreurs réseau/API eBay (timeout, HTTP 4xx/5xx, quota dépassé, JSON invalide) : interceptées, jamais de crash — bascule automatique vers le fallback, avec un message discret en cas d'échec (pas une erreur bloquante).
- Composant non trouvé nulle part : affiché comme "prix inconnu", jamais une valeur inventée.
- Saisie utilisateur invalide (ex: taille non numérique, type RAM/stockage non reconnu) : redemande la saisie plutôt que de planter.

## Configuration et dépôt GitHub

- `requirements.txt` : `requests`, `python-dotenv`
- `.gitignore` : `.env`, `__pycache__/`, etc.
- `README.md` : instructions d'installation, étapes pour créer un compte développeur eBay gratuit et obtenir une clé API, exemples d'utilisation.
- Projet initialisé comme repo git local, poussable sur GitHub par l'utilisateur quand il le souhaite (aucun push automatique par l'outil).

## Tests

- Tests unitaires (pytest) couvrant :
  - Calcul de la médiane des prix eBay
  - Formules RAM/stockage (€/Go selon type)
  - Lookup et normalisation dans la table de référence CPU/GPU
  - Parsing de réponses eBay simulées (mock, aucun appel réseau réel dans les tests)
- Pas de test contre l'API eBay réelle (nécessiterait des clés valides et une connexion réseau ; hors du périmètre des tests automatisés).

## Hors périmètre (explicitement exclu)

- Scraping de leboncoin ou d'autres sites (bloqué / contraire aux CGU)
- Calcul de marge de revente automatique
- Coefficient d'état du PC (esthétique, usure)
- Interface graphique ou web
- Fuzzy matching avancé sur les noms de modèles (normalisation simple uniquement pour la v1)
