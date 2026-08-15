# pc-rachat — Prix CPU/GPU : neuf en priorité — Design

## Contexte et objectif

Aujourd'hui, l'estimation du prix du CPU et du GPU (`estimate_component`) repose uniquement sur une recherche eBay **occasion**, puis, en secours, une table de référence locale (`data/reference_prices.json`, 4 CPU + 4 GPU seulement). Ce flux a produit un résultat aberrant en pratique : pour un Ryzen 7 9800X3D + RTX 5070 Ti, eBay n'a renvoyé qu'1 annonce occasion pour le CPU (1094,28€) et 2 pour le GPU (1688,58€) — des échantillons bien trop petits, probablement pollués par des annonces mal filtrées (PC complet, bundle, mauvaise devise...). Résultat : le total du détail par composant (3602,76€) dépassait le prix neuf équivalent du PC entier (2199,95€), ce qui est logiquement impossible.

Cette évolution ajoute un étage de recherche **prix neuf** sur les 7 revendeurs déjà utilisés pour le "PC neuf équivalent" et la RAM/le stockage, **avant** la recherche eBay occasion existante. eBay reste réservé à l'occasion uniquement (pas de recherche eBay neuf pour CPU/GPU — décision explicite : un CPU/GPU encore vendu neuf a un prix neuf beaucoup plus fiable, avec plus d'échantillons, que quelques annonces eBay occasion éparses).

## Ordre de priorité

1. **Marché neuf** — médiane sur les 7 revendeurs (LDLC, PcComponentes, Materiel.net, TopAchat, Grosbill, Rue du Commerce, Amazon), recherche du composant seul (pas le PC complet).
2. **eBay occasion** — comportement actuel, inchangé (`ebay_search_fn`, médiane sur les annonces occasion trouvées).
3. **Table de référence locale** — comportement actuel, inchangé (`data/reference_prices.json`).

On ne passe à l'étage suivant que si l'étage précédent ne trouve strictement rien.

## Architecture

### `retailers/*.py` (les 7 modules existants)

Chaque module gagne deux nouvelles fonctions, en plus de `search_prices`/`search_ram_prices`/`search_storage_prices` (inchangées) :

```python
def search_cpu_prices(cpu_model) -> list[float]:
def search_gpu_prices(gpu_model) -> list[float]:
```

Même contrat que l'existant : ne lève jamais d'exception, retourne `[]` sur tout échec. La requête de recherche est validée en direct sur chaque site — un CPU/GPU seul se comporte probablement différemment de la recherche combinée "PC gamer {cpu} {gpu}" existante (ex: certains sites nécessiteront un préfixe comme "Processeur"/"Carte graphique" pour éviter la pollution par des PC complets ou d'autres catégories, à l'image de ce qui a été découvert pour la RAM/le stockage). Aucune requête n'est devinée sans vérification live.

`retailers/__init__.py` expose deux nouvelles listes agrégées, `ALL_CPU_SEARCH_FUNCTIONS` et `ALL_GPU_SEARCH_FUNCTIONS` (7 fonctions chacune), en plus des listes existantes.

### `sourcing.py`

Deux nouvelles fonctions — **sans paramètres `client_id`/`client_secret`**, contrairement à `make_ram_search_fn`/`make_storage_search_fn`, puisqu'aucune des 7 sources n'est eBay ici :

```python
def make_cpu_search_fn() -> list[callable]:
    return retailers.ALL_CPU_SEARCH_FUNCTIONS


def make_gpu_search_fn() -> list[callable]:
    return retailers.ALL_GPU_SEARCH_FUNCTIONS
```

### `estimator.py`

`_aggregate_market_prices(arg1, arg2, search_fns)` est généralisée en `_aggregate_market_prices(search_fns, *args)` pour accepter un nombre variable d'arguments à transmettre à chaque `search_fn` (1 seul pour CPU/GPU — le `model` — contre 2 pour RAM/stockage/PC neuf). `_run_search_fn_safely` suit le même changement. Les 3 call sites existants (`estimate_new_pc_price`, `estimate_ram`, `estimate_storage`) sont mis à jour pour le nouvel ordre de paramètres, sans changement de comportement.

`estimate_component(model, category, ebay_search_fn, reference_table, new_price_search_fns)` change de signature : elle reçoit un nouveau paramètre `new_price_search_fns` (liste de fonctions à un seul argument `model`, agrégées via `_aggregate_market_prices(new_price_search_fns, model)`).

Nouvelle logique de `estimate_component` :
1. Médiane marché neuf via `new_price_search_fns` (si résultats trouvés) → `{"value": ..., "method": f"médiane sur N annonces neuves"}`
2. Sinon, comportement actuel inchangé : médiane eBay occasion (`{"method": f"médiane sur N annonces eBay"}`) → sinon table de référence (`{"method": "table de référence"}`) → sinon `None`.

`estimate_pc` gagne `cpu_search_fns`/`gpu_search_fns` (kwargs, cohérent avec `ram_search_fns`/`storage_search_fns` déjà présents), passés à `estimate_component` pour les catégories `cpu`/`gpu` respectivement.

### `cli.py` / `app.py`

Appellent `sourcing.make_cpu_search_fn()`/`sourcing.make_gpu_search_fn()` (sans credentials) et les passent à `estimate_pc`.

## Distinction neuf/occasion à l'affichage

Le libellé de méthode retourné par `estimate_component` permet déjà de distinguer la source (`"médiane sur N annonces neuves"` vs `"médiane sur N annonces eBay"` vs `"table de référence"`), affiché tel quel dans le détail par composant (CLI et web) — aucun changement de template nécessaire, le libellé suffit à indiquer si le prix est neuf ou occasion.

## Comportement de repli

Si aucune des 7 sources neuf ne trouve de résultat (CPU/GPU discontinué, plus vendu neuf), l'estimation retombe sur eBay occasion, puis sur la table de référence, exactement comme avant l'introduction du marché neuf — comportement de secours inchangé.

## Tests

Même méthodologie que le chantier RAM/stockage : pour chaque site, recherche live → fixture réelle capturée → tests avec prix exacts attendus → tests de non-régression sur la requête construite, tâche par tâche (7 sites × 2 catégories), avec review spec + qualité à chaque tâche.

## Hors périmètre

- Pas de recherche eBay neuf pour CPU/GPU (eBay reste occasion uniquement, décision explicite de l'utilisateur)
- Pas de changement du comportement pour la RAM/le stockage (déjà en marché-neuf-en-priorité, inchangé)
- Pas de dépréciation appliquée au prix neuf trouvé (le prix neuf est utilisé tel quel comme valeur affichée dans le détail par composant ; la grille d'achat/revente au niveau du PC entier reste le mécanisme qui applique une décote pour l'occasion)
- Pas de garantie de fiabilité uniforme entre les 7 sources (comportement Amazon probablement peu fiable, comme pour le PC complet et la RAM/le stockage — accepté)
