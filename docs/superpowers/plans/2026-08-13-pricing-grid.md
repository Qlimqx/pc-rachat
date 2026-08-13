# Pricing Grid & Multi-Source New-PC Price Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Given a PC config, produce one buy/resell recommendation: a price-tier grid (🔥✅🟢🟠🔴❌) and a resale-price range, computed from a "new PC equivalent" price aggregated across eBay (new condition) + 7 retailer scrapers (LDLC, PcComponentes, Materiel.net, TopAchat, Grosbill, Rue du Commerce, Amazon). Expose this via a new Flask web app deployable on Render, and also surface it in the existing CLI.

**Architecture:** `estimator.py` gains three new pure functions (`estimate_new_pc_price`, `estimate_buy_grid`, `estimate_resale_target`) that take injected search functions/config, same DI pattern as the existing component estimation. `ebay_client.py` gains a "new condition" search path (refactored to share HTTP logic with the existing used-condition search). A new `retailers/` package holds one scraper module per site, each with an identical `search_prices(cpu_model, gpu_model) -> list[float]` interface and identical fail-silent error handling. A new `sourcing.py` wires eBay-new + all 7 retailers into one list of search functions, consumed by both `cli.py` and the new `app.py` (Flask).

**Tech Stack:** Python 3, `requests`, `beautifulsoup4` (new), `flask` (new), `gunicorn` (new, for Render), `pytest`, `unittest.mock`.

---

## File Structure

```
pc-rachat/
├── cli.py                       # MODIFIED: prints pricing grid + resale target (Task 17)
├── app.py                       # NEW: Flask web app (Tasks 14-15)
├── sourcing.py                  # NEW: wires eBay-new + retailers into one search_fns list (Task 13)
├── estimator.py                 # MODIFIED: +estimate_new_pc_price/buy_grid/resale_target (Tasks 2-4)
├── ebay_client.py                # MODIFIED: +search_new_prices/search_new_pc_prices (Task 5)
├── retailers/
│   ├── __init__.py               # NEW: empty in Task 1, filled with ALL_SEARCH_FUNCTIONS in Task 13
│   ├── ldlc.py                   # NEW (Task 6)
│   ├── pccomponentes.py          # NEW (Task 7)
│   ├── materiel_net.py           # NEW (Task 8)
│   ├── topachat.py               # NEW (Task 9)
│   ├── grosbill.py                # NEW (Task 10)
│   ├── rueducommerce.py           # NEW (Task 11)
│   └── amazon.py                  # NEW (Task 12)
├── templates/
│   └── index.html                # NEW: Flask form + results page (Task 14)
├── data/
│   ├── buy_tiers.json            # NEW (Task 1)
│   └── resale_target.json        # NEW (Task 1)
├── render.yaml                   # NEW (Task 16)
├── Procfile                      # NEW (Task 16)
├── requirements.txt              # MODIFIED: +beautifulsoup4, flask, gunicorn (Task 1)
├── README.md                     # MODIFIED: Render deployment section (Task 16)
└── tests/
    ├── test_estimator.py         # MODIFIED (Tasks 2-4)
    ├── test_ebay_client.py       # MODIFIED (Task 5)
    ├── test_retailers_ldlc.py    # NEW (Task 6)
    ├── test_retailers_pccomponentes.py  # NEW (Task 7)
    ├── test_retailers_materiel_net.py   # NEW (Task 8)
    ├── test_retailers_topachat.py       # NEW (Task 9)
    ├── test_retailers_grosbill.py       # NEW (Task 10)
    ├── test_retailers_rueducommerce.py  # NEW (Task 11)
    ├── test_retailers_amazon.py         # NEW (Task 12)
    ├── test_retailers_init.py    # NEW (Task 13)
    ├── test_sourcing.py          # NEW (Task 13)
    ├── test_app.py               # NEW (Tasks 14-15)
    ├── test_cli.py                # MODIFIED (Task 17)
    └── fixtures/                  # NEW: real captured HTML snippets, one per retailer (Tasks 6-12)
```

---

### Task 1: Shared plumbing — dependencies and pricing-tier data

**Files:**
- Modify: `requirements.txt`
- Create: `data/buy_tiers.json`
- Create: `data/resale_target.json`
- Create: `retailers/__init__.py` (empty for now)

- [ ] **Step 1: Add new dependencies to `requirements.txt`**

```
requests==2.31.0
python-dotenv==1.0.1
pytest==8.0.0
beautifulsoup4==4.12.3
flask==3.0.3
gunicorn==22.0.0
```

- [ ] **Step 2: Create `data/buy_tiers.json`**

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

- [ ] **Step 3: Create `data/resale_target.json`**

```json
{"min_pct": 0.60, "max_pct": 0.68}
```

- [ ] **Step 4: Create `retailers/__init__.py`** (empty file — populated in Task 13 once all 7 site modules exist)

Create an empty file at `retailers/__init__.py` (0 bytes is fine — its presence makes `retailers/` an importable package).

- [ ] **Step 5: Install dependencies**

Run: `pip install -r requirements.txt`
Expected: `beautifulsoup4`, `flask`, `gunicorn` install without errors, alongside the existing packages.

- [ ] **Step 6: Validate the new JSON files parse**

Run: `python -c "import json; json.load(open('data/buy_tiers.json', encoding='utf-8')); json.load(open('data/resale_target.json', encoding='utf-8')); print('ok')"`
Expected: `ok`

- [ ] **Step 7: Run the full existing test suite to confirm nothing broke**

Run: `pytest -v`
Expected: 34 passed (unchanged — this task adds no code, just config/data)

- [ ] **Step 8: Commit**

```bash
git add requirements.txt data/buy_tiers.json data/resale_target.json retailers/__init__.py
git commit -m "chore: add dependencies and pricing-tier data for buy-grid feature"
```

---

### Task 2: `estimator.py` — `estimate_new_pc_price()`

**Files:**
- Modify: `estimator.py`
- Test: `tests/test_estimator.py`

- [ ] **Step 1: Write the failing tests**

```python
# append to tests/test_estimator.py
from estimator import estimate_new_pc_price


def test_estimate_new_pc_price_aggregates_multiple_sources():
    def source_a(cpu_model, gpu_model):
        return [1400.0, 1420.0]

    def source_b(cpu_model, gpu_model):
        return [1380.0]

    def source_c_found_nothing(cpu_model, gpu_model):
        return []

    result = estimate_new_pc_price(
        "Ryzen 7 5700X", "RTX 4060", [source_a, source_b, source_c_found_nothing]
    )

    assert result == {"value": 1400.0, "method": "médiane sur 3 annonces neuves"}


def test_estimate_new_pc_price_returns_none_when_all_sources_empty():
    def empty_source(cpu_model, gpu_model):
        return []

    result = estimate_new_pc_price("unknown-cpu", "unknown-gpu", [empty_source, empty_source])

    assert result is None


def test_estimate_new_pc_price_works_with_a_single_source():
    def only_source(cpu_model, gpu_model):
        return [999.0]

    result = estimate_new_pc_price("cpu", "gpu", [only_source])

    assert result == {"value": 999.0, "method": "médiane sur 1 annonces neuves"}
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_estimator.py -v`
Expected: FAIL with `ImportError: cannot import name 'estimate_new_pc_price'`

- [ ] **Step 3: Write minimal implementation**

```python
# append to estimator.py

def estimate_new_pc_price(cpu_model, gpu_model, search_fns):
    all_prices = []
    for search_fn in search_fns:
        all_prices.extend(search_fn(cpu_model, gpu_model))

    if not all_prices:
        return None

    return {
        "value": median_price(all_prices),
        "method": f"médiane sur {len(all_prices)} annonces neuves",
    }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_estimator.py -v`
Expected: 20 passed (17 existing + 3 new)

- [ ] **Step 5: Commit**

```bash
git add estimator.py tests/test_estimator.py
git commit -m "feat: add estimate_new_pc_price to aggregate multi-source new-PC listings"
```

---

### Task 3: `estimator.py` — `estimate_buy_grid()`

**Files:**
- Modify: `estimator.py`
- Test: `tests/test_estimator.py`

- [ ] **Step 1: Write the failing tests**

```python
# append to tests/test_estimator.py
from estimator import estimate_buy_grid


def test_estimate_buy_grid_computes_price_per_tier():
    tiers = [
        {"max_pct": 0.40, "emoji": "🔥", "label": "Très bonne affaire"},
        {"max_pct": 0.44, "emoji": "✅", "label": "Intéressant"},
        {"max_pct": 1.00, "emoji": "❌", "label": "Je passe"},
    ]

    result = estimate_buy_grid(1000.0, tiers)

    assert result == [
        {"max_price": 400.0, "emoji": "🔥", "label": "Très bonne affaire", "is_last": False},
        {"max_price": 440.0, "emoji": "✅", "label": "Intéressant", "is_last": False},
        {"max_price": 1000.0, "emoji": "❌", "label": "Je passe", "is_last": True},
    ]


def test_estimate_buy_grid_rounds_to_two_decimals():
    tiers = [{"max_pct": 0.415, "emoji": "🔥", "label": "Très bonne affaire"}]

    result = estimate_buy_grid(999.0, tiers)

    assert result == [
        {"max_price": 414.59, "emoji": "🔥", "label": "Très bonne affaire", "is_last": True}
    ]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_estimator.py -v`
Expected: FAIL with `ImportError: cannot import name 'estimate_buy_grid'`

- [ ] **Step 3: Write minimal implementation**

```python
# append to estimator.py

def estimate_buy_grid(new_pc_price, tiers):
    grid = []
    for index, tier in enumerate(tiers):
        grid.append({
            "max_price": round(new_pc_price * tier["max_pct"], 2),
            "emoji": tier["emoji"],
            "label": tier["label"],
            "is_last": index == len(tiers) - 1,
        })
    return grid
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_estimator.py -v`
Expected: 22 passed (20 existing + 2 new)

- [ ] **Step 5: Commit**

```bash
git add estimator.py tests/test_estimator.py
git commit -m "feat: add estimate_buy_grid to compute per-tier purchase price thresholds"
```

---

### Task 4: `estimator.py` — `estimate_resale_target()`

**Files:**
- Modify: `estimator.py`
- Test: `tests/test_estimator.py`

- [ ] **Step 1: Write the failing tests**

```python
# append to tests/test_estimator.py
from estimator import estimate_resale_target


def test_estimate_resale_target_computes_min_and_max():
    result = estimate_resale_target(1000.0, {"min_pct": 0.60, "max_pct": 0.68})
    assert result == {"min": 600.0, "max": 680.0}


def test_estimate_resale_target_rounds_to_two_decimals():
    result = estimate_resale_target(999.0, {"min_pct": 0.601, "max_pct": 0.677})
    assert result == {"min": 600.4, "max": 676.32}
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_estimator.py -v`
Expected: FAIL with `ImportError: cannot import name 'estimate_resale_target'`

- [ ] **Step 3: Write minimal implementation**

```python
# append to estimator.py

def estimate_resale_target(new_pc_price, resale_config):
    return {
        "min": round(new_pc_price * resale_config["min_pct"], 2),
        "max": round(new_pc_price * resale_config["max_pct"], 2),
    }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_estimator.py -v`
Expected: 24 passed (22 existing + 2 new)

- [ ] **Step 5: Commit**

```bash
git add estimator.py tests/test_estimator.py
git commit -m "feat: add estimate_resale_target to compute resale price range"
```

---

### Task 5: `ebay_client.py` — new-condition search (`search_new_prices`, `search_new_pc_prices`)

**Files:**
- Modify: `ebay_client.py`
- Test: `tests/test_ebay_client.py`

- [ ] **Step 1: Write the failing tests**

```python
# append to tests/test_ebay_client.py
from ebay_client import search_new_prices, search_new_pc_prices


@patch("ebay_client.requests.get")
def test_search_new_prices_uses_new_condition_filter(mock_get):
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "itemSummaries": [{"price": {"value": "1400.00", "currency": "EUR"}}]
    }
    mock_get.return_value = mock_response

    prices = search_new_prices("Ryzen 7 5700X RTX 4060 PC", "token123")

    assert prices == [1400.00]
    _, kwargs = mock_get.call_args
    assert "1000" in kwargs["params"]["filter"]


@patch("ebay_client.search_new_prices")
@patch("ebay_client.get_access_token")
def test_search_new_pc_prices_returns_prices_on_success(mock_token, mock_search):
    mock_token.return_value = "tok"
    mock_search.return_value = [1400.0, 1420.0]

    result = search_new_pc_prices("Ryzen 7 5700X", "RTX 4060", "id", "secret")

    assert result == [1400.0, 1420.0]
    mock_search.assert_called_once_with("Ryzen 7 5700X RTX 4060 PC", "tok")


@patch("ebay_client.get_access_token", side_effect=Exception("network error"))
def test_search_new_pc_prices_returns_empty_list_on_token_failure(mock_token):
    result = search_new_pc_prices("Ryzen 7 5700X", "RTX 4060", "id", "secret")
    assert result == []


@patch("ebay_client.search_new_prices", side_effect=Exception("timeout"))
@patch("ebay_client.get_access_token")
def test_search_new_pc_prices_returns_empty_list_on_search_failure(mock_token, mock_search):
    mock_token.return_value = "tok"
    result = search_new_pc_prices("Ryzen 7 5700X", "RTX 4060", "id", "secret")
    assert result == []
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_ebay_client.py -v`
Expected: FAIL with `ImportError: cannot import name 'search_new_prices'`

- [ ] **Step 3: Refactor `search_used_prices` to share logic, then add the new functions**

Replace the existing `search_used_prices` function in `ebay_client.py` with this (the refactor extracts a shared `_search_by_condition` helper; `search_used_prices`'s own behavior and signature are unchanged, so the 5 existing tests for it must still pass unmodified):

```python
# in ebay_client.py, replace the existing search_used_prices function with:

NEW_CONDITION_IDS = "1000"


def _search_by_condition(query, token, condition_ids, limit=20):
    response = requests.get(
        BROWSE_SEARCH_URL,
        headers={
            "Authorization": f"Bearer {token}",
            "X-EBAY-C-MARKETPLACE-ID": "EBAY_FR",
        },
        params={
            "q": query,
            "filter": f"conditionIds:{{{condition_ids}}}",
            "limit": limit,
        },
        timeout=10,
    )
    response.raise_for_status()
    data = response.json()
    return [float(item["price"]["value"]) for item in data.get("itemSummaries", [])]


def search_used_prices(query, token, limit=20):
    return _search_by_condition(query, token, USED_CONDITION_IDS, limit)


def search_new_prices(query, token, limit=20):
    return _search_by_condition(query, token, NEW_CONDITION_IDS, limit)


def search_new_pc_prices(cpu_model, gpu_model, client_id, client_secret):
    try:
        token = get_access_token(client_id, client_secret)
        return search_new_prices(f"{cpu_model} {gpu_model} PC", token)
    except Exception:
        return []
```

## Context

`USED_CONDITION_IDS` and `BROWSE_SEARCH_URL` already exist in `ebay_client.py` from the original implementation — don't redefine them, just add `NEW_CONDITION_IDS` and the functions above. `search_new_pc_prices` mirrors the existing `search_component_price` shape exactly (fetch token, search, catch everything, return `[]`/empty on any failure) but is scoped to full-PC search strings and the new-condition filter.

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_ebay_client.py -v`
Expected: 12 passed (8 existing + 4 new). Also run the existing 5 `search_used_prices` tests specifically to confirm the refactor didn't change behavior:

Run: `pytest tests/test_ebay_client.py -k search_used_prices -v`
Expected: 3 passed, all still green (the refactor must not change `search_used_prices`'s observable behavior)

- [ ] **Step 5: Run the full suite**

Run: `pytest -v`
Expected: 45 passed (24 estimator + 12 ebay_client + 9 cli; if a number here doesn't match, investigate before proceeding, don't just adjust the expectation)

- [ ] **Step 6: Commit**

```bash
git add ebay_client.py tests/test_ebay_client.py
git commit -m "feat: add eBay new-condition search for full-PC listings"
```

---

### Task 6: `retailers/ldlc.py` — LDLC scraper

**Files:**
- Create: `retailers/ldlc.py`
- Create: `tests/fixtures/ldlc_search.html`
- Test: `tests/test_retailers_ldlc.py`

## Context

This is a discovery-driven task: LDLC's real search-results HTML structure isn't knowable in advance, so this task starts with live research, not with pre-written code. Do not guess CSS selectors — inspect the real page.

**Full error-handling contract (applies to every retailer module in this plan, not just this one):** `search_prices(cpu_model, gpu_model)` must NEVER raise. Any failure — network error, timeout, non-200 response, HTML structure that doesn't match what was researched, a CAPTCHA/block page, anything — is caught and the function returns `[]`. This matches the fail-silent philosophy already used throughout `ebay_client.py`.

- [ ] **Step 1: Research the live site**

Use a browser/fetch tool to visit LDLC's search functionality (try `https://www.ldlc.com/recherche/Ryzen+7+5700X/` first; if that 404s or the site's search works differently now, find the real search URL by using the site's own search box and observing where it navigates). Search for a PC build query like `PC gamer Ryzen 7 5700X RTX 4060` (a broad build query, not a single component, since this is meant to find complete-PC listings) and record:
- The real, working search URL pattern
- The CSS selector for each product result "card" in the results list
- Within a card, the selector for the product title/name text
- Within a card, the selector for the price text
- One real example: a product title string and its price as they actually appear in the HTML, so you can sanity-check your parsing logic against real data

Save the raw HTML of the search-results page you fetched to `tests/fixtures/ldlc_search.html` (the whole page, or at minimum the container with several product cards — enough for a realistic test fixture).

- [ ] **Step 2: Write the failing test using the captured real fixture**

```python
# tests/test_retailers_ldlc.py
from unittest.mock import patch, Mock

from retailers.ldlc import search_prices


@patch("retailers.ldlc.requests.get")
def test_search_prices_extracts_prices_from_real_fixture(mock_get):
    with open("tests/fixtures/ldlc_search.html", encoding="utf-8") as f:
        html = f.read()

    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.text = html
    mock_get.return_value = mock_response

    prices = search_prices("Ryzen 7 5700X", "RTX 4060")

    assert isinstance(prices, list)
    assert all(isinstance(p, float) for p in prices)
    assert len(prices) > 0  # fill in the exact expected values/count once you've inspected the fixture


@patch("retailers.ldlc.requests.get", side_effect=Exception("network error"))
def test_search_prices_returns_empty_list_on_network_failure(mock_get):
    assert search_prices("Ryzen 7 5700X", "RTX 4060") == []


@patch("retailers.ldlc.requests.get")
def test_search_prices_returns_empty_list_on_unparseable_html(mock_get):
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.text = "<html><body>not a product listing page</body></html>"
    mock_get.return_value = mock_response

    assert search_prices("Ryzen 7 5700X", "RTX 4060") == []
```

Once you've inspected the real fixture in Step 1, tighten `test_search_prices_extracts_prices_from_real_fixture`'s assertion from `len(prices) > 0` to the exact expected price list (or an exact count) you can read directly off the captured HTML — don't leave it as a weak `> 0` check in the final version.

- [ ] **Step 3: Run tests to verify they fail**

Run: `pytest tests/test_retailers_ldlc.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'retailers.ldlc'`

- [ ] **Step 4: Implement `retailers/ldlc.py`**

```python
# retailers/ldlc.py
import re

import requests
from bs4 import BeautifulSoup

SEARCH_URL = "https://www.ldlc.com/recherche/{query}/"  # confirm/adjust based on Step 1 research
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
}


def _extract_price(text):
    match = re.search(r"[\d]+(?:[.,]\d+)?", text.replace("\xa0", "").replace(" ", ""))
    if not match:
        return None
    return float(match.group().replace(",", "."))


def search_prices(cpu_model, gpu_model):
    try:
        query = f"{cpu_model} {gpu_model}"
        url = SEARCH_URL.format(query=requests.utils.quote(query))
        response = requests.get(url, headers=HEADERS, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        prices = []
        for card in soup.select("REPLACE_WITH_REAL_CARD_SELECTOR"):  # from Step 1 research
            price_el = card.select_one("REPLACE_WITH_REAL_PRICE_SELECTOR")
            if price_el is None:
                continue
            price = _extract_price(price_el.get_text(strip=True))
            if price is not None:
                prices.append(price)
        return prices
    except Exception:
        return []
```

Replace `SEARCH_URL`, `"REPLACE_WITH_REAL_CARD_SELECTOR"`, and `"REPLACE_WITH_REAL_PRICE_SELECTOR"` with the real values found in Step 1 — these three placeholders are the only unresolved pieces in this task, and they get resolved by what you actually observed on the live site, not guessed. Everything else in this function (the try/except shape, the price-regex extraction, the header, the timeout) is final as written.

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest tests/test_retailers_ldlc.py -v`
Expected: 3 passed

- [ ] **Step 6: Commit**

```bash
git add retailers/ldlc.py tests/test_retailers_ldlc.py tests/fixtures/ldlc_search.html
git commit -m "feat: add LDLC scraper for new-PC price search"
```

---

### Task 7: `retailers/pccomponentes.py` — PcComponentes scraper

**Files:**
- Create: `retailers/pccomponentes.py`
- Create: `tests/fixtures/pccomponentes_search.html`
- Test: `tests/test_retailers_pccomponentes.py`

## Context

Same discovery-driven approach and same error-handling contract as Task 6 (LDLC) — every retailer module must never raise, always degrading to `[]` on any failure.

- [ ] **Step 1: Research the live site**

Use a browser/fetch tool to find PcComponentes' French search functionality (try `https://www.pccomponentes.fr/buscar/Ryzen+7+5700X` first; adjust if the real search URL differs). Search for a complete-PC build query like `PC gamer Ryzen 7 5700X RTX 4060` and record: the real search URL pattern, the product-card selector, the price selector within a card, and one real title+price example. Save the raw search-results HTML to `tests/fixtures/pccomponentes_search.html`.

- [ ] **Step 2: Write the failing test using the captured real fixture**

```python
# tests/test_retailers_pccomponentes.py
from unittest.mock import patch, Mock

from retailers.pccomponentes import search_prices


@patch("retailers.pccomponentes.requests.get")
def test_search_prices_extracts_prices_from_real_fixture(mock_get):
    with open("tests/fixtures/pccomponentes_search.html", encoding="utf-8") as f:
        html = f.read()

    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.text = html
    mock_get.return_value = mock_response

    prices = search_prices("Ryzen 7 5700X", "RTX 4060")

    assert isinstance(prices, list)
    assert all(isinstance(p, float) for p in prices)
    assert len(prices) > 0  # tighten to the exact expected values once you've inspected the fixture


@patch("retailers.pccomponentes.requests.get", side_effect=Exception("network error"))
def test_search_prices_returns_empty_list_on_network_failure(mock_get):
    assert search_prices("Ryzen 7 5700X", "RTX 4060") == []


@patch("retailers.pccomponentes.requests.get")
def test_search_prices_returns_empty_list_on_unparseable_html(mock_get):
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.text = "<html><body>not a product listing page</body></html>"
    mock_get.return_value = mock_response

    assert search_prices("Ryzen 7 5700X", "RTX 4060") == []
```

Tighten the first test's assertion to exact expected values once the real fixture is captured, same as Task 6.

- [ ] **Step 3: Run tests to verify they fail**

Run: `pytest tests/test_retailers_pccomponentes.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'retailers.pccomponentes'`

- [ ] **Step 4: Implement `retailers/pccomponentes.py`**

```python
# retailers/pccomponentes.py
import re

import requests
from bs4 import BeautifulSoup

SEARCH_URL = "https://www.pccomponentes.fr/buscar/{query}"  # confirm/adjust based on Step 1 research
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
}


def _extract_price(text):
    match = re.search(r"[\d]+(?:[.,]\d+)?", text.replace("\xa0", "").replace(" ", ""))
    if not match:
        return None
    return float(match.group().replace(",", "."))


def search_prices(cpu_model, gpu_model):
    try:
        query = f"{cpu_model} {gpu_model}"
        url = SEARCH_URL.format(query=requests.utils.quote(query))
        response = requests.get(url, headers=HEADERS, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        prices = []
        for card in soup.select("REPLACE_WITH_REAL_CARD_SELECTOR"):  # from Step 1 research
            price_el = card.select_one("REPLACE_WITH_REAL_PRICE_SELECTOR")
            if price_el is None:
                continue
            price = _extract_price(price_el.get_text(strip=True))
            if price is not None:
                prices.append(price)
        return prices
    except Exception:
        return []
```

Replace the URL and the two selector placeholders with what Step 1 found.

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest tests/test_retailers_pccomponentes.py -v`
Expected: 3 passed

- [ ] **Step 6: Commit**

```bash
git add retailers/pccomponentes.py tests/test_retailers_pccomponentes.py tests/fixtures/pccomponentes_search.html
git commit -m "feat: add PcComponentes scraper for new-PC price search"
```

---

### Task 8: `retailers/materiel_net.py` — Materiel.net scraper

**Files:**
- Create: `retailers/materiel_net.py`
- Create: `tests/fixtures/materiel_net_search.html`
- Test: `tests/test_retailers_materiel_net.py`

## Context

Same discovery-driven approach and same error-handling contract as Task 6.

- [ ] **Step 1: Research the live site**

Use a browser/fetch tool to find Materiel.net's search functionality (try `https://www.materiel.net/recherche/Ryzen+7+5700X/` first; adjust if the real pattern differs). Search for `PC gamer Ryzen 7 5700X RTX 4060` and record: the real search URL pattern, the product-card selector, the price selector, and one real title+price example. Save the raw search-results HTML to `tests/fixtures/materiel_net_search.html`.

- [ ] **Step 2: Write the failing test using the captured real fixture**

```python
# tests/test_retailers_materiel_net.py
from unittest.mock import patch, Mock

from retailers.materiel_net import search_prices


@patch("retailers.materiel_net.requests.get")
def test_search_prices_extracts_prices_from_real_fixture(mock_get):
    with open("tests/fixtures/materiel_net_search.html", encoding="utf-8") as f:
        html = f.read()

    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.text = html
    mock_get.return_value = mock_response

    prices = search_prices("Ryzen 7 5700X", "RTX 4060")

    assert isinstance(prices, list)
    assert all(isinstance(p, float) for p in prices)
    assert len(prices) > 0  # tighten to exact expected values once the fixture is inspected


@patch("retailers.materiel_net.requests.get", side_effect=Exception("network error"))
def test_search_prices_returns_empty_list_on_network_failure(mock_get):
    assert search_prices("Ryzen 7 5700X", "RTX 4060") == []


@patch("retailers.materiel_net.requests.get")
def test_search_prices_returns_empty_list_on_unparseable_html(mock_get):
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.text = "<html><body>not a product listing page</body></html>"
    mock_get.return_value = mock_response

    assert search_prices("Ryzen 7 5700X", "RTX 4060") == []
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `pytest tests/test_retailers_materiel_net.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'retailers.materiel_net'`

- [ ] **Step 4: Implement `retailers/materiel_net.py`**

```python
# retailers/materiel_net.py
import re

import requests
from bs4 import BeautifulSoup

SEARCH_URL = "https://www.materiel.net/recherche/{query}/"  # confirm/adjust based on Step 1 research
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
}


def _extract_price(text):
    match = re.search(r"[\d]+(?:[.,]\d+)?", text.replace("\xa0", "").replace(" ", ""))
    if not match:
        return None
    return float(match.group().replace(",", "."))


def search_prices(cpu_model, gpu_model):
    try:
        query = f"{cpu_model} {gpu_model}"
        url = SEARCH_URL.format(query=requests.utils.quote(query))
        response = requests.get(url, headers=HEADERS, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        prices = []
        for card in soup.select("REPLACE_WITH_REAL_CARD_SELECTOR"):  # from Step 1 research
            price_el = card.select_one("REPLACE_WITH_REAL_PRICE_SELECTOR")
            if price_el is None:
                continue
            price = _extract_price(price_el.get_text(strip=True))
            if price is not None:
                prices.append(price)
        return prices
    except Exception:
        return []
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest tests/test_retailers_materiel_net.py -v`
Expected: 3 passed

- [ ] **Step 6: Commit**

```bash
git add retailers/materiel_net.py tests/test_retailers_materiel_net.py tests/fixtures/materiel_net_search.html
git commit -m "feat: add Materiel.net scraper for new-PC price search"
```

---

### Task 9: `retailers/topachat.py` — TopAchat scraper

**Files:**
- Create: `retailers/topachat.py`
- Create: `tests/fixtures/topachat_search.html`
- Test: `tests/test_retailers_topachat.py`

## Context

Same discovery-driven approach and same error-handling contract as Task 6.

- [ ] **Step 1: Research the live site**

Use a browser/fetch tool to find TopAchat's search functionality (try `https://www.topachat.com/pages/recherche.php?f_recherche=Ryzen+7+5700X` first; adjust based on what actually works). Search for `PC gamer Ryzen 7 5700X RTX 4060` and record: the real search URL pattern, the product-card selector, the price selector, and one real title+price example. Save the raw search-results HTML to `tests/fixtures/topachat_search.html`.

- [ ] **Step 2: Write the failing test using the captured real fixture**

```python
# tests/test_retailers_topachat.py
from unittest.mock import patch, Mock

from retailers.topachat import search_prices


@patch("retailers.topachat.requests.get")
def test_search_prices_extracts_prices_from_real_fixture(mock_get):
    with open("tests/fixtures/topachat_search.html", encoding="utf-8") as f:
        html = f.read()

    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.text = html
    mock_get.return_value = mock_response

    prices = search_prices("Ryzen 7 5700X", "RTX 4060")

    assert isinstance(prices, list)
    assert all(isinstance(p, float) for p in prices)
    assert len(prices) > 0  # tighten to exact expected values once the fixture is inspected


@patch("retailers.topachat.requests.get", side_effect=Exception("network error"))
def test_search_prices_returns_empty_list_on_network_failure(mock_get):
    assert search_prices("Ryzen 7 5700X", "RTX 4060") == []


@patch("retailers.topachat.requests.get")
def test_search_prices_returns_empty_list_on_unparseable_html(mock_get):
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.text = "<html><body>not a product listing page</body></html>"
    mock_get.return_value = mock_response

    assert search_prices("Ryzen 7 5700X", "RTX 4060") == []
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `pytest tests/test_retailers_topachat.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'retailers.topachat'`

- [ ] **Step 4: Implement `retailers/topachat.py`**

```python
# retailers/topachat.py
import re

import requests
from bs4 import BeautifulSoup

SEARCH_URL = "https://www.topachat.com/pages/recherche.php"  # confirm/adjust based on Step 1 research
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
}


def _extract_price(text):
    match = re.search(r"[\d]+(?:[.,]\d+)?", text.replace("\xa0", "").replace(" ", ""))
    if not match:
        return None
    return float(match.group().replace(",", "."))


def search_prices(cpu_model, gpu_model):
    try:
        query = f"{cpu_model} {gpu_model}"
        response = requests.get(
            SEARCH_URL, params={"f_recherche": query}, headers=HEADERS, timeout=10
        )
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        prices = []
        for card in soup.select("REPLACE_WITH_REAL_CARD_SELECTOR"):  # from Step 1 research
            price_el = card.select_one("REPLACE_WITH_REAL_PRICE_SELECTOR")
            if price_el is None:
                continue
            price = _extract_price(price_el.get_text(strip=True))
            if price is not None:
                prices.append(price)
        return prices
    except Exception:
        return []
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest tests/test_retailers_topachat.py -v`
Expected: 3 passed

- [ ] **Step 6: Commit**

```bash
git add retailers/topachat.py tests/test_retailers_topachat.py tests/fixtures/topachat_search.html
git commit -m "feat: add TopAchat scraper for new-PC price search"
```

---

### Task 10: `retailers/grosbill.py` — Grosbill scraper

**Files:**
- Create: `retailers/grosbill.py`
- Create: `tests/fixtures/grosbill_search.html`
- Test: `tests/test_retailers_grosbill.py`

## Context

Same discovery-driven approach and same error-handling contract as Task 6.

- [ ] **Step 1: Research the live site**

Use a browser/fetch tool to find Grosbill's search functionality (try `https://www.grosbill.com/search?keywords=Ryzen+7+5700X` first; adjust based on what actually works). Search for `PC gamer Ryzen 7 5700X RTX 4060` and record: the real search URL pattern, the product-card selector, the price selector, and one real title+price example. Save the raw search-results HTML to `tests/fixtures/grosbill_search.html`.

- [ ] **Step 2: Write the failing test using the captured real fixture**

```python
# tests/test_retailers_grosbill.py
from unittest.mock import patch, Mock

from retailers.grosbill import search_prices


@patch("retailers.grosbill.requests.get")
def test_search_prices_extracts_prices_from_real_fixture(mock_get):
    with open("tests/fixtures/grosbill_search.html", encoding="utf-8") as f:
        html = f.read()

    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.text = html
    mock_get.return_value = mock_response

    prices = search_prices("Ryzen 7 5700X", "RTX 4060")

    assert isinstance(prices, list)
    assert all(isinstance(p, float) for p in prices)
    assert len(prices) > 0  # tighten to exact expected values once the fixture is inspected


@patch("retailers.grosbill.requests.get", side_effect=Exception("network error"))
def test_search_prices_returns_empty_list_on_network_failure(mock_get):
    assert search_prices("Ryzen 7 5700X", "RTX 4060") == []


@patch("retailers.grosbill.requests.get")
def test_search_prices_returns_empty_list_on_unparseable_html(mock_get):
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.text = "<html><body>not a product listing page</body></html>"
    mock_get.return_value = mock_response

    assert search_prices("Ryzen 7 5700X", "RTX 4060") == []
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `pytest tests/test_retailers_grosbill.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'retailers.grosbill'`

- [ ] **Step 4: Implement `retailers/grosbill.py`**

```python
# retailers/grosbill.py
import re

import requests
from bs4 import BeautifulSoup

SEARCH_URL = "https://www.grosbill.com/search"  # confirm/adjust based on Step 1 research
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
}


def _extract_price(text):
    match = re.search(r"[\d]+(?:[.,]\d+)?", text.replace("\xa0", "").replace(" ", ""))
    if not match:
        return None
    return float(match.group().replace(",", "."))


def search_prices(cpu_model, gpu_model):
    try:
        query = f"{cpu_model} {gpu_model}"
        response = requests.get(
            SEARCH_URL, params={"keywords": query}, headers=HEADERS, timeout=10
        )
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        prices = []
        for card in soup.select("REPLACE_WITH_REAL_CARD_SELECTOR"):  # from Step 1 research
            price_el = card.select_one("REPLACE_WITH_REAL_PRICE_SELECTOR")
            if price_el is None:
                continue
            price = _extract_price(price_el.get_text(strip=True))
            if price is not None:
                prices.append(price)
        return prices
    except Exception:
        return []
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest tests/test_retailers_grosbill.py -v`
Expected: 3 passed

- [ ] **Step 6: Commit**

```bash
git add retailers/grosbill.py tests/test_retailers_grosbill.py tests/fixtures/grosbill_search.html
git commit -m "feat: add Grosbill scraper for new-PC price search"
```

---

### Task 11: `retailers/rueducommerce.py` — Rue du Commerce scraper

**Files:**
- Create: `retailers/rueducommerce.py`
- Create: `tests/fixtures/rueducommerce_search.html`
- Test: `tests/test_retailers_rueducommerce.py`

## Context

Same discovery-driven approach and same error-handling contract as Task 6.

- [ ] **Step 1: Research the live site**

Use a browser/fetch tool to find Rue du Commerce's search functionality (try `https://www.rueducommerce.fr/search?q=Ryzen+7+5700X` first; adjust based on what actually works). Search for `PC gamer Ryzen 7 5700X RTX 4060` and record: the real search URL pattern, the product-card selector, the price selector, and one real title+price example. Save the raw search-results HTML to `tests/fixtures/rueducommerce_search.html`.

- [ ] **Step 2: Write the failing test using the captured real fixture**

```python
# tests/test_retailers_rueducommerce.py
from unittest.mock import patch, Mock

from retailers.rueducommerce import search_prices


@patch("retailers.rueducommerce.requests.get")
def test_search_prices_extracts_prices_from_real_fixture(mock_get):
    with open("tests/fixtures/rueducommerce_search.html", encoding="utf-8") as f:
        html = f.read()

    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.text = html
    mock_get.return_value = mock_response

    prices = search_prices("Ryzen 7 5700X", "RTX 4060")

    assert isinstance(prices, list)
    assert all(isinstance(p, float) for p in prices)
    assert len(prices) > 0  # tighten to exact expected values once the fixture is inspected


@patch("retailers.rueducommerce.requests.get", side_effect=Exception("network error"))
def test_search_prices_returns_empty_list_on_network_failure(mock_get):
    assert search_prices("Ryzen 7 5700X", "RTX 4060") == []


@patch("retailers.rueducommerce.requests.get")
def test_search_prices_returns_empty_list_on_unparseable_html(mock_get):
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.text = "<html><body>not a product listing page</body></html>"
    mock_get.return_value = mock_response

    assert search_prices("Ryzen 7 5700X", "RTX 4060") == []
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `pytest tests/test_retailers_rueducommerce.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'retailers.rueducommerce'`

- [ ] **Step 4: Implement `retailers/rueducommerce.py`**

```python
# retailers/rueducommerce.py
import re

import requests
from bs4 import BeautifulSoup

SEARCH_URL = "https://www.rueducommerce.fr/search"  # confirm/adjust based on Step 1 research
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
}


def _extract_price(text):
    match = re.search(r"[\d]+(?:[.,]\d+)?", text.replace("\xa0", "").replace(" ", ""))
    if not match:
        return None
    return float(match.group().replace(",", "."))


def search_prices(cpu_model, gpu_model):
    try:
        query = f"{cpu_model} {gpu_model}"
        response = requests.get(SEARCH_URL, params={"q": query}, headers=HEADERS, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        prices = []
        for card in soup.select("REPLACE_WITH_REAL_CARD_SELECTOR"):  # from Step 1 research
            price_el = card.select_one("REPLACE_WITH_REAL_PRICE_SELECTOR")
            if price_el is None:
                continue
            price = _extract_price(price_el.get_text(strip=True))
            if price is not None:
                prices.append(price)
        return prices
    except Exception:
        return []
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest tests/test_retailers_rueducommerce.py -v`
Expected: 3 passed

- [ ] **Step 6: Commit**

```bash
git add retailers/rueducommerce.py tests/test_retailers_rueducommerce.py tests/fixtures/rueducommerce_search.html
git commit -m "feat: add Rue du Commerce scraper for new-PC price search"
```

---

### Task 12: `retailers/amazon.py` — Amazon scraper (expected low/no yield)

**Files:**
- Create: `retailers/amazon.py`
- Create: `tests/fixtures/amazon_search.html`
- Test: `tests/test_retailers_amazon.py`

## Context

Same discovery-driven approach and same error-handling contract as Task 6. **Difference from the other 6 retailer tasks:** Amazon's anti-bot protection is expected to block or CAPTCHA-gate this scraper most of the time in production. That's an accepted outcome per the design spec, not a bug to work around here — build it identically to the other retailers (same interface, same fail-silent contract) and don't add special-case CAPTCHA-solving or bot-evasion logic (out of scope, and CAPTCHA-bypass is not something to build regardless of source).

- [ ] **Step 1: Research the live site**

Use a browser/fetch tool to attempt Amazon France search (try `https://www.amazon.fr/s?k=Ryzen+7+5700X+RTX+4060` first). If you get a normal results page, record: the product-card selector, the price selector, and one real title+price example, then save that HTML to `tests/fixtures/amazon_search.html`. **If you get blocked, redirected to a CAPTCHA, or served an unusual/empty page:** that itself is useful information — save whatever HTML you actually received (even a CAPTCHA page) to `tests/fixtures/amazon_search.html` as a realistic "this site blocked us" fixture, and write the parser to treat that page the same as any other unparseable page (extracts nothing, returns `[]`, no crash). Don't spend excessive time trying to work around a block — one honest attempt is enough.

- [ ] **Step 2: Write the failing test using the captured real fixture**

```python
# tests/test_retailers_amazon.py
from unittest.mock import patch, Mock

from retailers.amazon import search_prices


@patch("retailers.amazon.requests.get")
def test_search_prices_handles_the_real_fixture_without_crashing(mock_get):
    with open("tests/fixtures/amazon_search.html", encoding="utf-8") as f:
        html = f.read()

    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.text = html
    mock_get.return_value = mock_response

    prices = search_prices("Ryzen 7 5700X", "RTX 4060")

    assert isinstance(prices, list)
    assert all(isinstance(p, float) for p in prices)
    # if Step 1 got real results, tighten this to the exact expected values;
    # if Step 1 got blocked/CAPTCHA'd, assert prices == [] instead — either is a valid, honest outcome


@patch("retailers.amazon.requests.get", side_effect=Exception("network error"))
def test_search_prices_returns_empty_list_on_network_failure(mock_get):
    assert search_prices("Ryzen 7 5700X", "RTX 4060") == []


@patch("retailers.amazon.requests.get")
def test_search_prices_returns_empty_list_on_unparseable_html(mock_get):
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.text = "<html><body>not a product listing page</body></html>"
    mock_get.return_value = mock_response

    assert search_prices("Ryzen 7 5700X", "RTX 4060") == []
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `pytest tests/test_retailers_amazon.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'retailers.amazon'`

- [ ] **Step 4: Implement `retailers/amazon.py`**

```python
# retailers/amazon.py
import re

import requests
from bs4 import BeautifulSoup

SEARCH_URL = "https://www.amazon.fr/s"  # confirm/adjust based on Step 1 research
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
}


def _extract_price(text):
    match = re.search(r"[\d]+(?:[.,]\d+)?", text.replace("\xa0", "").replace(" ", ""))
    if not match:
        return None
    return float(match.group().replace(",", "."))


def search_prices(cpu_model, gpu_model):
    try:
        query = f"{cpu_model} {gpu_model}"
        response = requests.get(SEARCH_URL, params={"k": query}, headers=HEADERS, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        prices = []
        for card in soup.select("REPLACE_WITH_REAL_CARD_SELECTOR"):  # from Step 1 research
            price_el = card.select_one("REPLACE_WITH_REAL_PRICE_SELECTOR")
            if price_el is None:
                continue
            price = _extract_price(price_el.get_text(strip=True))
            if price is not None:
                prices.append(price)
        return prices
    except Exception:
        return []
```

If Step 1 found only a block/CAPTCHA page, the selectors simply won't match anything on real Amazon responses — that's fine, the function will legitimately return `[]` in production, matching the accepted design outcome.

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest tests/test_retailers_amazon.py -v`
Expected: 3 passed

- [ ] **Step 6: Commit**

```bash
git add retailers/amazon.py tests/test_retailers_amazon.py tests/fixtures/amazon_search.html
git commit -m "feat: add Amazon scraper for new-PC price search (best-effort, expected low yield)"
```

---

### Task 13: `retailers/__init__.py` aggregation + `sourcing.py`

**Files:**
- Modify: `retailers/__init__.py`
- Create: `sourcing.py`
- Test: `tests/test_retailers_init.py`
- Test: `tests/test_sourcing.py`

- [ ] **Step 1: Write the failing test for `retailers/__init__.py`**

```python
# tests/test_retailers_init.py
from retailers import ALL_SEARCH_FUNCTIONS


def test_all_search_functions_lists_seven_callables():
    assert len(ALL_SEARCH_FUNCTIONS) == 7
    assert all(callable(fn) for fn in ALL_SEARCH_FUNCTIONS)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_retailers_init.py -v`
Expected: FAIL with `ImportError: cannot import name 'ALL_SEARCH_FUNCTIONS' from 'retailers'`

- [ ] **Step 3: Fill in `retailers/__init__.py`**

```python
# retailers/__init__.py
from retailers.ldlc import search_prices as ldlc_search
from retailers.pccomponentes import search_prices as pccomponentes_search
from retailers.materiel_net import search_prices as materiel_net_search
from retailers.topachat import search_prices as topachat_search
from retailers.grosbill import search_prices as grosbill_search
from retailers.rueducommerce import search_prices as rueducommerce_search
from retailers.amazon import search_prices as amazon_search

ALL_SEARCH_FUNCTIONS = [
    ldlc_search,
    pccomponentes_search,
    materiel_net_search,
    topachat_search,
    grosbill_search,
    rueducommerce_search,
    amazon_search,
]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_retailers_init.py -v`
Expected: 1 passed

- [ ] **Step 5: Write the failing tests for `sourcing.py`**

```python
# tests/test_sourcing.py
from unittest.mock import patch

from sourcing import make_new_pc_search_fn


def test_make_new_pc_search_fn_returns_eight_functions():
    fns = make_new_pc_search_fn("myid", "mysecret")
    assert len(fns) == 8
    assert all(callable(fn) for fn in fns)


@patch("sourcing.ebay_client.search_new_pc_prices")
def test_first_function_wraps_ebay_with_credentials(mock_search):
    mock_search.return_value = [100.0]

    fns = make_new_pc_search_fn("myid", "mysecret")
    result = fns[0]("cpu", "gpu")

    assert result == [100.0]
    mock_search.assert_called_once_with("cpu", "gpu", "myid", "mysecret")
```

- [ ] **Step 6: Run tests to verify they fail**

Run: `pytest tests/test_sourcing.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'sourcing'`

- [ ] **Step 7: Write `sourcing.py`**

```python
# sourcing.py
import ebay_client
import retailers


def make_new_pc_search_fn(client_id, client_secret):
    def ebay_new_search(cpu_model, gpu_model):
        return ebay_client.search_new_pc_prices(cpu_model, gpu_model, client_id, client_secret)

    return [ebay_new_search] + retailers.ALL_SEARCH_FUNCTIONS
```

- [ ] **Step 8: Run tests to verify they pass**

Run: `pytest tests/test_sourcing.py -v`
Expected: 2 passed

- [ ] **Step 9: Run the full suite**

Run: `pytest -v`
Expected: all tests pass — running total is the Task 5 count (45) + 3 tests per retailer × 7 retailers (21) + 1 (`test_retailers_init`) + 2 (`test_sourcing`) = 69 passed. If this doesn't match, investigate before proceeding.

- [ ] **Step 10: Commit**

```bash
git add retailers/__init__.py sourcing.py tests/test_retailers_init.py tests/test_sourcing.py
git commit -m "feat: aggregate retailer scrapers and wire eBay-new + retailers into one search list"
```

---

### Task 14: `app.py` — Flask form + result route

**Files:**
- Create: `app.py`
- Create: `templates/index.html`
- Test: `tests/test_app.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_app.py
from unittest.mock import patch

import app as flask_app_module


def test_index_get_shows_the_form():
    client = flask_app_module.app.test_client()

    response = client.get("/")

    assert response.status_code == 200
    assert "Modèle CPU".encode("utf-8") in response.data


@patch("app.sourcing.make_new_pc_search_fn")
@patch("app.cli_helpers.make_ebay_search_fn")
def test_index_post_shows_component_breakdown(mock_used_search_fn, mock_new_search_fns):
    mock_used_search_fn.return_value = lambda model, category: []
    mock_new_search_fns.return_value = [lambda cpu, gpu: []]

    client = flask_app_module.app.test_client()
    response = client.post(
        "/",
        data={
            "cpu_model": "i5-10400",
            "ram_go": "16",
            "ram_type": "ddr4",
            "storage_go": "512",
            "storage_type": "ssd",
            "gpu_model": "gtx 1660",
        },
    )

    assert response.status_code == 200
    assert "Total estimé".encode("utf-8") in response.data


@patch("app.sourcing.make_new_pc_search_fn")
@patch("app.cli_helpers.make_ebay_search_fn")
def test_index_post_shows_buy_grid_when_new_pc_price_found(mock_used_search_fn, mock_new_search_fns):
    mock_used_search_fn.return_value = lambda model, category: []
    mock_new_search_fns.return_value = [lambda cpu, gpu: [1400.0]]

    client = flask_app_module.app.test_client()
    response = client.post(
        "/",
        data={
            "cpu_model": "Ryzen 7 5700X",
            "ram_go": "16",
            "ram_type": "ddr4",
            "storage_go": "1000",
            "storage_type": "nvme",
            "gpu_model": "RTX 4060",
        },
    )

    assert response.status_code == 200
    assert "Grille d".encode("utf-8") in response.data
    assert "Prix de revente".encode("utf-8") in response.data


def test_index_post_with_invalid_number_reshows_form_with_error():
    client = flask_app_module.app.test_client()

    response = client.post(
        "/",
        data={
            "cpu_model": "i5-10400",
            "ram_go": "pas-un-nombre",
            "ram_type": "ddr4",
            "storage_go": "512",
            "storage_type": "ssd",
            "gpu_model": "",
        },
    )

    assert response.status_code == 200
    assert "Modèle CPU".encode("utf-8") in response.data
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_app.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app'`

- [ ] **Step 3: Write `templates/index.html`**

```html
<!doctype html>
<html lang="fr">
<head>
  <meta charset="utf-8">
  <title>pc-rachat</title>
</head>
<body>
  <h1>Estimation de rachat PC</h1>

  {% if error %}
    <p style="color: red;">{{ error }}</p>
  {% endif %}

  <form method="post">
    <label>Modèle CPU (ex: i5-10400)
      <input type="text" name="cpu_model" value="{{ form_values.cpu_model if form_values else '' }}">
    </label><br>

    <label>RAM (Go)
      <input type="text" name="ram_go" value="{{ form_values.ram_go if form_values else '' }}">
    </label>
    <label>Type RAM
      <select name="ram_type">
        <option value="ddr3">DDR3</option>
        <option value="ddr4">DDR4</option>
        <option value="ddr5">DDR5</option>
      </select>
    </label><br>

    <label>Stockage (Go)
      <input type="text" name="storage_go" value="{{ form_values.storage_go if form_values else '' }}">
    </label>
    <label>Type stockage
      <select name="storage_type">
        <option value="hdd">HDD</option>
        <option value="ssd">SSD</option>
        <option value="nvme">NVMe</option>
      </select>
    </label><br>

    <label>Modèle GPU (laisser vide si intégré)
      <input type="text" name="gpu_model" value="{{ form_values.gpu_model if form_values else '' }}">
    </label><br>

    <button type="submit">Estimer</button>
  </form>

  {% if new_pc_price is not none %}
    <h2>Grille d'achat</h2>
    <p>Prix neuf équivalent estimé : {{ "%.2f"|format(new_pc_price) }}€</p>
    <ul>
      {% for tier in buy_grid %}
        <li>
          {% if tier.is_last %}
            au-delà de {{ "%.2f"|format(tier.max_price) }}€ {{ tier.emoji }} {{ tier.label }}
          {% else %}
            jusqu'à {{ "%.2f"|format(tier.max_price) }}€ {{ tier.emoji }} {{ tier.label }}
          {% endif %}
        </li>
      {% endfor %}
    </ul>

    <h2>Prix de revente visé</h2>
    <p>{{ "%.2f"|format(resale_target.min) }}€ – {{ "%.2f"|format(resale_target.max) }}€</p>
  {% elif result %}
    <p>Grille d'achat non disponible — aucun PC neuf comparable trouvé.</p>
  {% endif %}

  {% if result %}
    <h2>Détail par composant</h2>
    <ul>
      {% for key, label in [("cpu", "CPU"), ("ram", "RAM"), ("storage", "Stockage"), ("gpu", "GPU")] %}
        <li>
          {% if result.breakdown[key] %}
            {{ label }} : {{ "%.2f"|format(result.breakdown[key].value) }}€ ({{ result.breakdown[key].method }})
          {% elif key == "gpu" and key not in result.missing %}
            {{ label }} : non renseigné
          {% else %}
            {{ label }} : prix inconnu ⚠
          {% endif %}
        </li>
      {% endfor %}
    </ul>
    <p>Total estimé : {{ "%.2f"|format(result.total) }}€</p>
    {% if result.missing %}
      <p>⚠ estimation incomplète — composants inconnus : {{ result.missing|join(", ") }}</p>
    {% endif %}
  {% endif %}
</body>
</html>
```

- [ ] **Step 4: Write `app.py`**

```python
# app.py
import os
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, render_template, request

import cli as cli_helpers
import estimator
import sourcing

load_dotenv()

app = Flask(__name__)
DATA_DIR = Path(__file__).parent / "data"


@app.route("/", methods=["GET", "POST"])
def index():
    result = None
    buy_grid = None
    resale_target = None
    new_pc_price = None
    error = None
    form_values = None

    if request.method == "POST":
        form_values = request.form
        try:
            cpu_model = request.form.get("cpu_model", "").strip()
            ram_go = float(request.form.get("ram_go", "").replace(",", "."))
            ram_type = request.form.get("ram_type", "").strip().lower()
            storage_go = float(request.form.get("storage_go", "").replace(",", "."))
            storage_type = request.form.get("storage_type", "").strip().lower()
            gpu_model = request.form.get("gpu_model", "").strip()
        except ValueError:
            error = "Merci d'entrer des nombres valides pour la RAM et le stockage."
        else:
            client_id = os.environ.get("EBAY_CLIENT_ID")
            client_secret = os.environ.get("EBAY_CLIENT_SECRET")

            reference_prices = cli_helpers.load_json(DATA_DIR / "reference_prices.json")
            component_rates = cli_helpers.load_json(DATA_DIR / "component_rates.json")
            buy_tiers = cli_helpers.load_json(DATA_DIR / "buy_tiers.json")
            resale_config = cli_helpers.load_json(DATA_DIR / "resale_target.json")

            used_search_fn = cli_helpers.make_ebay_search_fn(client_id, client_secret)
            new_pc_search_fns = sourcing.make_new_pc_search_fn(client_id, client_secret)

            result = estimator.estimate_pc(
                cpu_model=cpu_model,
                ram_go=ram_go,
                ram_type=ram_type,
                storage_go=storage_go,
                storage_type=storage_type,
                gpu_model=gpu_model,
                ebay_search_fn=used_search_fn,
                reference_prices=reference_prices,
                component_rates=component_rates,
            )

            new_pc_result = estimator.estimate_new_pc_price(cpu_model, gpu_model, new_pc_search_fns)
            if new_pc_result is not None:
                new_pc_price = new_pc_result["value"]
                buy_grid = estimator.estimate_buy_grid(new_pc_price, buy_tiers)
                resale_target = estimator.estimate_resale_target(new_pc_price, resale_config)

    return render_template(
        "index.html",
        result=result,
        buy_grid=buy_grid,
        resale_target=resale_target,
        new_pc_price=new_pc_price,
        error=error,
        form_values=form_values,
    )


if __name__ == "__main__":
    app.run(debug=True)
```

## Context

`cli.load_json` and `cli.make_ebay_search_fn` already exist (Task 12 of the original plan) and are reused here rather than duplicated — importing `cli` as a module is safe because its interactive code only runs inside `main()`, guarded by `if __name__ == "__main__":`. `sourcing.make_new_pc_search_fn` was just built in Task 13.

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest tests/test_app.py -v`
Expected: 4 passed

- [ ] **Step 6: Run the full suite**

Run: `pytest -v`
Expected: 69 (from Task 13) + 4 = 73 passed

- [ ] **Step 7: Commit**

```bash
git add app.py templates/index.html tests/test_app.py
git commit -m "feat: add Flask web app with form and pricing-grid result page"
```

---

### Task 15: Manual verification of the web app locally

**Files:** none (manual verification only)

- [ ] **Step 1: Run the app locally**

Run: `python app.py`
Expected: Flask dev server starts, printing a local URL (default `http://127.0.0.1:5000`)

- [ ] **Step 2: Open the URL in a browser and submit the form**

Enter: CPU `i5-10400`, RAM `16`, RAM type `ddr4`, Storage `512`, Storage type `ssd`, GPU `gtx 1660`. Submit.
Expected: page reloads showing the component breakdown (CPU/RAM/Stockage/GPU + total). Since no real eBay credentials are configured in this environment, and the retailer scrapers query for `i5-10400 gtx 1660` (not a full PC-build query most retailers will have exact matches for), it's expected and fine if the buy grid / resale target don't appear (message "Grille d'achat non disponible" instead) — that's the designed fallback, not a bug.

- [ ] **Step 3: Stop the server**

Press Ctrl+C in the terminal running `python app.py`.

- [ ] **Step 4: Commit any fixes discovered**

```bash
git add -A
git commit -m "fix: address issues found during manual web app verification"
```

(Skip this commit if no fixes were needed.)

---

### Task 16: Render deployment config

**Files:**
- Create: `render.yaml`
- Create: `Procfile`
- Modify: `README.md`

- [ ] **Step 1: Create `render.yaml`**

```yaml
services:
  - type: web
    name: pc-rachat
    env: python
    buildCommand: pip install -r requirements.txt
    startCommand: gunicorn app:app
    envVars:
      - key: EBAY_CLIENT_ID
        sync: false
      - key: EBAY_CLIENT_SECRET
        sync: false
```

- [ ] **Step 2: Create `Procfile`**

```
web: gunicorn app:app
```

- [ ] **Step 3: Add a deployment section to `README.md`**

Add this new section after the existing "Utilisation" section (keep everything else in the current README unchanged):

```markdown
## Déploiement sur Render

L'appli web (`app.py`) est prête à être déployée sur [Render](https://render.com/) :

1. Connecte ton compte Render à GitHub et sélectionne ce repo.
2. Render détecte automatiquement `render.yaml` (Blueprint) — sinon, configure manuellement :
   - Build command : `pip install -r requirements.txt`
   - Start command : `gunicorn app:app`
3. Dans les paramètres du service Render, ajoute tes variables d'environnement : `EBAY_CLIENT_ID` et `EBAY_CLIENT_SECRET` (les mêmes valeurs que dans ton `.env` local — voir la section eBay ci-dessus).
4. Déploie. Render te donne une URL publique (`https://<nom-du-service>.onrender.com`).

Sans ces variables configurées sur Render, l'appli fonctionne quand même pour le détail par composant (table de référence locale), mais la recherche eBay est désactivée jusqu'à ce que les clés soient ajoutées.
```

- [ ] **Step 4: Commit**

```bash
git add render.yaml Procfile README.md
git commit -m "docs: add Render deployment config and instructions"
```

---

### Task 17: `cli.py` — surface the buy grid and resale target in the CLI too

**Files:**
- Modify: `cli.py`
- Test: `tests/test_cli.py`

- [ ] **Step 1: Write the failing test**

```python
# append to tests/test_cli.py
from cli import format_pricing_grid


def test_format_pricing_grid_renders_tiers_and_resale_range():
    buy_grid = [
        {"max_price": 400.0, "emoji": "🔥", "label": "Très bonne affaire", "is_last": False},
        {"max_price": 1000.0, "emoji": "❌", "label": "Je passe", "is_last": True},
    ]
    resale_target = {"min": 600.0, "max": 680.0}

    output = format_pricing_grid(1000.0, buy_grid, resale_target)

    assert "Prix neuf équivalent estimé : 1000.00€" in output
    assert "jusqu'à 400.00€ 🔥 Très bonne affaire" in output
    assert "au-delà de 1000.00€ ❌ Je passe" in output
    assert "Prix de revente visé : 600.00€ – 680.00€" in output
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_cli.py -v`
Expected: FAIL with `ImportError: cannot import name 'format_pricing_grid'`

- [ ] **Step 3: Add `format_pricing_grid` to `cli.py`**

```python
# append to cli.py, before main()

def format_pricing_grid(new_pc_price, buy_grid, resale_target):
    lines = [f"Prix neuf équivalent estimé : {new_pc_price:.2f}€", "", "Grille d'achat :"]
    for tier in buy_grid:
        if tier["is_last"]:
            lines.append(f"  au-delà de {tier['max_price']:.2f}€ {tier['emoji']} {tier['label']}")
        else:
            lines.append(f"  jusqu'à {tier['max_price']:.2f}€ {tier['emoji']} {tier['label']}")
    lines.append("")
    lines.append(
        f"Prix de revente visé : {resale_target['min']:.2f}€ – {resale_target['max']:.2f}€"
    )
    return "\n".join(lines)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_cli.py -v`
Expected: all `test_cli.py` tests pass (previous count + 1)

- [ ] **Step 5: Wire it into `main()`**

In `cli.py`, modify `main()`: after loading `reference_prices` and `component_rates` (and before the `estimate_pc` call), also load the two new data files and build the new-PC search functions; after printing the existing `format_result(result)` output, also compute and print the pricing grid if available. Replace the existing `main()` body with:

```python
def main():
    load_dotenv()
    client_id = os.environ.get("EBAY_CLIENT_ID")
    client_secret = os.environ.get("EBAY_CLIENT_SECRET")

    if not client_id or not client_secret:
        print("(clé API eBay non configurée — utilisation de la table de référence uniquement)\n")

    reference_prices = load_json(DATA_DIR / "reference_prices.json")
    component_rates = load_json(DATA_DIR / "component_rates.json")
    buy_tiers = load_json(DATA_DIR / "buy_tiers.json")
    resale_config = load_json(DATA_DIR / "resale_target.json")
    ebay_search_fn = make_ebay_search_fn(client_id, client_secret)
    new_pc_search_fns = sourcing.make_new_pc_search_fn(client_id, client_secret)

    print("=== Estimation de rachat PC ===\n")
    cpu_model = input("Modèle CPU (ex: i5-10400) : ").strip()
    ram_go = prompt_float("RAM (Go) : ")
    ram_type = prompt_choice("Type RAM (ddr3/ddr4/ddr5) : ", ["ddr3", "ddr4", "ddr5"])
    storage_go = prompt_float("Stockage (Go) : ")
    storage_type = prompt_choice("Type stockage (hdd/ssd/nvme) : ", ["hdd", "ssd", "nvme"])
    gpu_model = input("Modèle GPU (laisser vide si carte intégrée) : ").strip()

    result = estimator.estimate_pc(
        cpu_model=cpu_model,
        ram_go=ram_go,
        ram_type=ram_type,
        storage_go=storage_go,
        storage_type=storage_type,
        gpu_model=gpu_model,
        ebay_search_fn=ebay_search_fn,
        reference_prices=reference_prices,
        component_rates=component_rates,
    )

    new_pc_result = estimator.estimate_new_pc_price(cpu_model, gpu_model, new_pc_search_fns)
    print()
    if new_pc_result is not None:
        buy_grid = estimator.estimate_buy_grid(new_pc_result["value"], buy_tiers)
        resale_target = estimator.estimate_resale_target(new_pc_result["value"], resale_config)
        print(format_pricing_grid(new_pc_result["value"], buy_grid, resale_target))
    else:
        print("Grille d'achat non disponible — aucun PC neuf comparable trouvé.")

    print("\n" + format_result(result))


if __name__ == "__main__":
    main()
```

Also add `import sourcing` to the top of `cli.py` alongside the existing `import ebay_client` / `import estimator` lines.

- [ ] **Step 6: Run the full suite**

Run: `pytest -v`
Expected: 73 (from Task 14) + 1 (`test_format_pricing_grid_renders_tiers_and_resale_range`) = 74 passed

- [ ] **Step 7: Commit**

```bash
git add cli.py tests/test_cli.py
git commit -m "feat: surface buy grid and resale target in the CLI output"
```

---

### Task 18: Manual end-to-end smoke test (CLI + web)

**Files:** none (manual verification only)

- [ ] **Step 1: Run the full automated test suite**

Run: `pytest -v`
Expected: 74 passed, 0 failed

- [ ] **Step 2: Run the CLI end-to-end**

Run: `python cli.py`
Input: CPU `Ryzen 7 5700X`, RAM `16`, RAM type `ddr4`, Storage `1000`, Storage type `nvme`, GPU `RTX 4060`
Expected: no crash; either a full buy-grid + resale-target section followed by the component breakdown (if any of the 8 sources found something for this real, common config), or the "Grille d'achat non disponible" message followed by the component breakdown (if none did, which is plausible without real eBay credentials configured in this environment) — both are valid outcomes, the point is confirming no exception is raised either way.

- [ ] **Step 3: Run the web app end-to-end**

Run: `python app.py`, open the printed local URL, submit the same config as Step 2.
Expected: same two possible outcomes as Step 2, rendered as HTML, no server error (no Flask 500 page).

- [ ] **Step 4: Verify the Render deployment files are self-consistent**

Run: `cat render.yaml Procfile` (or open them) and confirm the start command in both matches (`gunicorn app:app`), and that `gunicorn` is listed in `requirements.txt`.

- [ ] **Step 5: Commit any final fixes discovered**

```bash
git add -A
git commit -m "fix: address issues found during full-system smoke testing"
```

(Skip this commit if no fixes were needed.)
