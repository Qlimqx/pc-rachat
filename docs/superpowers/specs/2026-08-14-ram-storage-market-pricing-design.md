# pc-rachat — Prix RAM/stockage basés sur le marché — Design

## Contexte et objectif

Aujourd'hui, l'estimation du prix de la RAM et du stockage repose uniquement sur une formule fixe (`taille × taux €/Go` dans `data/component_rates.json`). Ces taux se sont révélés trop bas par rapport aux prix réels du marché (ex: 32Go DDR5 estimé à 96€ alors que le prix réel est plutôt autour de 300€).

Cette évolution remplace la formule comme source principale par une **recherche de prix réels**, sur les mêmes 8 sources déjà utilisées pour le "PC neuf équivalent" (eBay neuf + LDLC, PcComponentes, Materiel.net, TopAchat, Grosbill, Rue du Commerce, Amazon), à la fois pour la RAM et pour le stockage. La formule €/Go actuelle devient un **filet de sécurité** : elle n'est utilisée que si aucune des 8 sources ne trouve de résultat pour la taille/type demandé.

## Principe de réutilisation

Les sélecteurs HTML des 7 sites marchands ont déjà été identifiés lors de la mise en place du "PC neuf équivalent" (`retailers/*.py`). Cette évolution ne redécouvre pas ces sélecteurs — elle réutilise la même logique d'extraction HTTP/HTML, avec une requête de recherche différente (RAM ou stockage au lieu d'un PC complet). Concrètement, chaque module `retailers/*.py` voit sa logique de requête HTTP + parsing extraite dans une fonction interne partagée (même principe que le refactor `_search_by_condition` déjà fait dans `ebay_client.py`), réutilisée par les nouvelles fonctions de recherche RAM/stockage.

## Architecture

### `retailers/*.py` (les 7 modules existants)

Chaque module gagne deux nouvelles fonctions, en plus de `search_prices` (inchangée) :

```python
def search_ram_prices(ram_go, ram_type) -> list[float]:
def search_storage_prices(storage_go, storage_type) -> list[float]:
```

Même contrat que `search_prices` : ne lève jamais d'exception, retourne `[]` sur tout échec. La construction de la requête (ex: `"16Go DDR4"` vs `"RAM 16Go DDR4"`) est validée en direct sur chaque site, comme pour la recherche PC complet — certains sites peuvent nécessiter une formulation différente de la requête (leçon retenue : LDLC/Materiel.net avaient besoin d'une requête différente de PcComponentes/TopAchat).

`retailers/__init__.py` expose deux nouvelles listes agrégées, `ALL_RAM_SEARCH_FUNCTIONS` et `ALL_STORAGE_SEARCH_FUNCTIONS`, en plus de `ALL_SEARCH_FUNCTIONS` existant.

### `ebay_client.py`

Deux nouvelles fonctions, réutilisant le `_search_by_condition` déjà présent (condition neuf) :

```python
def search_ram_prices(ram_go, ram_type, client_id, client_secret) -> list[float]:
def search_storage_prices(storage_go, storage_type, client_id, client_secret) -> list[float]:
```

### `sourcing.py`

Deux nouvelles fonctions, même principe que `make_new_pc_search_fn` (eBay + les 7 sites, 8 sources au total) :

```python
def make_ram_search_fn(client_id, client_secret) -> list[callable]:
def make_storage_search_fn(client_id, client_secret) -> list[callable]:
```

### `estimator.py`

`estimate_ram(ram_go, ram_type, search_fns, rates)` et `estimate_storage(storage_go, storage_type, search_fns, rates)` changent de signature : elles reçoivent désormais une liste de fonctions de recherche (comme `estimate_new_pc_price`), agrègent les résultats en **parallèle** (`ThreadPoolExecutor`, même pattern que `estimate_new_pc_price` — leçon retenue du ~90s d'attente séquentielle découvert lors de la première mise en place), calculent la médiane si des résultats existent, sinon retombent sur la formule €/Go actuelle (`_estimate_by_rate`, inchangée). Le `method` retourné indique la source réelle (`"médiane sur N annonces neuves"` ou `"formule €/Go"`), pour rester cohérent avec l'affichage existant.

`estimate_pc` (qui appelle `estimate_ram`/`estimate_storage`) est mis à jour pour leur passer les nouvelles listes de fonctions de recherche.

### `cli.py` / `app.py`

Chargent `sourcing.make_ram_search_fn(...)` et `sourcing.make_storage_search_fn(...)` et les passent à `estimate_pc`, en plus des fonctions déjà utilisées pour CPU/GPU et le PC complet.

## Comportement de repli

Si les 8 sources ne trouvent rien pour une taille/type de RAM ou de stockage donné, l'estimation retombe silencieusement sur la formule €/Go (`data/component_rates.json`) — jamais de "prix inconnu" pour la RAM/le stockage, comportement identique à aujourd'hui dans ce cas de figure.

## Hors périmètre

- Pas de redécouverte des sélecteurs CSS des 7 sites (réutilisation de l'existant)
- Pas de changement du comportement pour le CPU/GPU (recherche eBay + table de référence, inchangé)
- Pas de garantie de fiabilité uniforme entre les 8 sources (Amazon restera probablement peu fiable, comme pour le PC complet — accepté)
