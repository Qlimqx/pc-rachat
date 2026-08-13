# pc-rachat — Grille d'achat & prix de revente — Design

## Contexte et objectif

Extension du projet `pc-rachat` (voir [2026-08-13-pc-rachat-design.md](2026-08-13-pc-rachat-design.md) pour le socle existant : estimation de la valeur marché des composants via eBay + fallback).

**Principe central, à respecter strictement dans toute l'implémentation : une config PC saisie = une seule analyse de rachat/revente en sortie.** Le livrable pour l'utilisateur n'est pas juste "la valeur des pièces" (ce que fait déjà l'outil existant) mais une recommandation exploitable, au même format que l'exemple de référence fourni par l'utilisateur :

1. Une **grille de prix d'achat** (plusieurs seuils en €, chacun avec un avis 🔥/✅/🟢/🟠/🔴/❌)
2. Une **fourchette de prix de revente visé** (min–max en €)

Ces deux éléments sont calculés à partir d'un **prix de PC neuf équivalent**, trouvé en agrégeant plusieurs sources — pas à partir de la simple somme des pièces d'occasion (qui sous-estime fortement la valeur d'un PC monté, testé et présenté proprement).

Le calcul détaillé par composant (déjà existant : CPU/RAM/stockage/GPU) reste affiché en complément, pas remplacé.

## Architecture

### Nouveau package `retailers/`

Un fichier par site, même interface partout :

```python
def search_prices(cpu_model, gpu_model) -> list[float]:
    ...
```

- `retailers/ldlc.py`
- `retailers/pccomponentes.py`
- `retailers/materiel_net.py`
- `retailers/topachat.py`
- `retailers/grosbill.py`
- `retailers/rueducommerce.py`
- `retailers/amazon.py`

Chaque module :
- Construit une requête de recherche à partir de `cpu_model` + `gpu_model` (config PC complète, pas un composant isolé)
- Fait une requête HTTP (`requests`, avec un `User-Agent` réaliste et un `timeout`)
- Parse le HTML avec `BeautifulSoup` (nouvelle dépendance : `beautifulsoup4`)
- Extrait les prix des résultats de recherche pertinents
- **Ne lève jamais d'exception vers l'appelant** : toute erreur (timeout, HTTP non-200, structure HTML changée, page de blocage/CAPTCHA, JSON/HTML invalide) est interceptée en interne et fait retourner `[]`

`retailers/__init__.py` expose une liste `ALL_SEARCH_FUNCTIONS` regroupant les 7 fonctions, pour un import unique côté orchestration (`cli.py` / `app.py`).

**Note d'implémentation :** pour chacun des 7 sites, la structure HTML réelle doit être inspectée en direct (recherche live) avant d'écrire le parseur — deviner les sélecteurs CSS sans vérification produirait un code qui ne fonctionne jamais en pratique. Amazon est un cas à part : sa protection anti-bot est nettement plus agressive (CAPTCHA quasi systématique) ; le module est construit comme les autres mais il est accepté qu'il ne retourne quasiment jamais de résultat en pratique — les autres sources compensent.

### `ebay_client.py` — nouvelle fonction

```python
def search_new_pc_prices(cpu_model, gpu_model) -> list[float]:
```

Même mécanique que `search_used_prices`, mais :
- Filtre condition = **neuf** (conditionId `1000`) au lieu d'occasion
- Requête combinant CPU + GPU (config complète), pas un composant isolé
- Retourne `[]` sur toute erreur (même philosophie que le reste du client eBay)

### `estimator.py` — nouvelles fonctions (logique pure, sans I/O)

```python
def estimate_new_pc_price(cpu_model, gpu_model, search_fns) -> {"value": float, "method": str} | None:
```
- `search_fns` : liste de callables `(cpu_model, gpu_model) -> list[float]` (eBay neuf + les 7 retailers), injectée par l'appelant — garde `estimator.py` testable sans mock réseau
- Appelle chaque fonction, fusionne tous les prix retournés dans une seule liste
- Si la liste fusionnée est non vide → médiane, `method` = ex. `"médiane sur N annonces neuves (eBay, LDLC, ...)"`
- Si vide (aucune source n'a rien trouvé) → `None`

```python
def estimate_buy_grid(new_pc_price, tiers) -> list[{"max_price": float, "emoji": str, "label": str, "is_last": bool}]:
```
- `tiers` : liste chargée depuis `data/buy_tiers.json`, chaque entrée `{"max_pct": float, "emoji": str, "label": str}`
- Calcule `max_price = new_pc_price * max_pct` pour chaque palier, dans l'ordre croissant
- `is_last` vaut `True` uniquement pour le dernier palier de la liste (❌ "Je passe" par défaut) : sa valeur `max_price` est calculée comme les autres (utile en interne) mais l'affichage (CLI/web) le présente comme une borne ouverte — "au-delà de X€" plutôt que "jusqu'à X€" — puisqu'il n'y a pas de plafond réel au-delà duquel on ne regarde plus le prix

```python
def estimate_resale_target(new_pc_price, resale_config) -> {"min": float, "max": float}:
```
- `resale_config` chargé depuis `data/resale_target.json` : `{"min_pct": float, "max_pct": float}`
- `min = new_pc_price * min_pct`, `max = new_pc_price * max_pct`

### Nouvelles données éditables

`data/buy_tiers.json` (valeurs par défaut dérivées de l'exemple fourni par l'utilisateur, ajustables) :
```json
[
  {"max_pct": 0.40, "emoji": "🔥", "label": "Très bonne affaire"},
  {"max_pct": 0.44, "emoji": "✅", "label": "Intéressant"},
  {"max_pct": 0.47, "emoji": "🟢", "label": "Correct"},
  {"max_pct": 0.51, "emoji": "🟠", "label": "Il faut bien négocier"},
  {"max_pct": 0.55, "emoji": "🔴", "label": "Marge faible"},
  {"max_pct": 1.00, "emoji": "❌", "label": "Je passe"}
]
```

`data/resale_target.json` :
```json
{"min_pct": 0.60, "max_pct": 0.68}
```

### Comportement si aucun prix neuf trouvé

Si `estimate_new_pc_price` retourne `None` (les 8 sources ont toutes échoué ou n'ont rien trouvé) : la grille d'achat et le prix de revente ne sont **pas affichés** — pas de valeur inventée. Le détail par composant (fonctionnalité existante) reste affiché normalement, avec un message indiquant que la grille n'a pas pu être calculée.

### Interface web (`app.py`) + déploiement Render

- Flask, une route affichant le formulaire (CPU, RAM+type, stockage+type, GPU), une route traitant la soumission
- La page de résultat affiche, dans cet ordre : **grille d'achat**, **prix de revente visé**, puis le détail par composant (existant) en complément
- `render.yaml` + `Procfile` pour déploiement Render ; `gunicorn` ajouté à `requirements.txt`
- Clés eBay via variables d'environnement Render (dashboard), pas de `.env` sur le serveur
- `cli.py` (existant) reste fonctionnel en parallèle, inchangé dans sa logique — bénéficie aussi de la grille/revente via les mêmes fonctions `estimator.py`

## Gestion des erreurs

- Chaque source de prix neuf (eBay + 7 retailers) est individuellement isolée : une erreur dans l'une n'empêche pas les autres de contribuer
- Aucune exception ne doit jamais remonter jusqu'à l'utilisateur final (web ou CLI) depuis une recherche de prix
- Le fait qu'une source ne retourne jamais rien (cas attendu pour Amazon) n'est pas un bug — c'est un comportement normal, absorbé silencieusement par l'agrégation

## Tests

- `estimator.py` : tests unitaires pour `estimate_new_pc_price` (agrégation multi-sources via des `search_fns` factices), `estimate_buy_grid`, `estimate_resale_target` — aucun mock réseau nécessaire, même principe que l'existant
- `retailers/*.py` : tests avec réponses HTTP mockées, à partir de fragments HTML réalistes capturés lors de la phase de recherche (pas de fixtures inventées)
- `ebay_client.search_new_pc_prices` : mocké comme `search_used_prices`
- `app.py` : tests d'intégration légers si pertinent (rendu du formulaire, route de résultat) — pas de test contre un vrai déploiement Render

## Hors périmètre

- Coefficient d'état du PC (esthétique, usure) — toujours écarté, comme dans le design initial
- Garantie de fonctionnement des scrapers dans le temps (les sites changent de structure ; maintenance manuelle occasionnelle à prévoir, en particulier pour Amazon)
- Authentification/compte sur les sites scrapés — recherche publique uniquement, aucune connexion
