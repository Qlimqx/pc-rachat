# RAM/Storage Market Pricing Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the flat €/Go formula as the primary RAM/storage price source with a real median-of-market-prices search across the same 8 sources already used for the "PC neuf équivalent" search (eBay new + 7 retailers), falling back to the existing formula only when no source finds anything.

**Architecture:** `estimator.py`'s concurrent multi-source aggregation logic (already built for `estimate_new_pc_price`) is generalized into a shared helper and reused by `estimate_ram`/`estimate_storage`, which now try the market median first and fall back to `_estimate_by_rate` only if empty. `ebay_client.py` and each of the 7 `retailers/*.py` modules gain two new search functions (`search_ram_prices`, `search_storage_prices`) that reuse the exact same HTTP/parsing/selector logic already proven for `search_prices`, just extracted into a shared internal helper and called with a different query. `sourcing.py` gains two new aggregator functions mirroring `make_new_pc_search_fn`. `cli.py`/`app.py` wire the new sourcing functions into `estimate_pc`.

**Tech Stack:** Python 3, `requests`, `beautifulsoup4`, `concurrent.futures.ThreadPoolExecutor` (already in use), `pytest`.

---

## File Structure

```
pc-rachat/
├── estimator.py               # MODIFIED: shared aggregation helper, estimate_ram/estimate_storage try market first (Tasks 1-2)
├── ebay_client.py              # MODIFIED: +search_ram_prices, +search_storage_prices (Task 3)
├── retailers/
│   ├── ldlc.py                 # MODIFIED: refactored + RAM/storage search (Task 4)
│   ├── pccomponentes.py        # MODIFIED: refactored + RAM/storage search (Task 5)
│   ├── materiel_net.py         # MODIFIED: refactored + RAM/storage search (Task 6)
│   ├── topachat.py             # MODIFIED: refactored + RAM/storage search (Task 7)
│   ├── grosbill.py             # MODIFIED: refactored + RAM/storage search (Task 8)
│   ├── rueducommerce.py        # MODIFIED: refactored + RAM/storage search (Task 9)
│   ├── amazon.py               # MODIFIED: refactored + RAM/storage search (Task 10)
│   └── __init__.py             # MODIFIED: +ALL_RAM_SEARCH_FUNCTIONS, +ALL_STORAGE_SEARCH_FUNCTIONS (Task 11)
├── sourcing.py                 # MODIFIED: +make_ram_search_fn, +make_storage_search_fn (Task 12)
├── cli.py                      # MODIFIED: wires new search functions into estimate_pc (Task 13)
├── app.py                      # MODIFIED: wires new search functions into estimate_pc (Task 14)
└── tests/                      # MODIFIED/NEW: throughout
```

---

### Task 1: `estimator.py` — generalize multi-source aggregation, RAM/storage try market first

**Files:**
- Modify: `estimator.py`
- Test: `tests/test_estimator.py`

## Context

`estimator.py` currently has `_run_search_fn_safely(search_fn, cpu_model, gpu_model)` and the aggregation loop inline inside `estimate_new_pc_price`. This task extracts that aggregation logic into a shared helper (`_aggregate_market_prices`) reusable by `estimate_ram`/`estimate_storage`, and changes those two functions' signatures to accept a `search_fns` parameter, trying the market median first and falling back to the existing formula (`_estimate_by_rate`) only when the market search finds nothing.

**This task changes existing function signatures** (`estimate_ram(size_go, ram_type, rates)` → `estimate_ram(size_go, ram_type, search_fns, rates)`, same for `estimate_storage`), so the 5 existing tests that call them (`test_estimate_ram_known_type`, `test_estimate_ram_unknown_type_returns_none`, `test_estimate_ram_type_is_case_insensitive`, `test_estimate_storage_known_type`, `test_estimate_storage_unknown_type_returns_none`) must be updated in this same task to pass `[]` as `search_fns` — passing an empty list means no market search happens, so the existing expected formula-based values are preserved unchanged.

- [ ] **Step 1: Update the 5 existing RAM/storage tests to the new signature, and add new market-based tests**

In `tests/test_estimator.py`, find these 5 existing tests and update each call to insert `[]` as the third positional argument (before `RATES`):

```python
def test_estimate_ram_known_type():
    result = estimate_ram(16, "ddr4", [], RATES)
    assert result == {"value": 32.0, "method": "formule €/Go"}


def test_estimate_ram_unknown_type_returns_none():
    assert estimate_ram(16, "ddr7", [], RATES) is None


def test_estimate_ram_type_is_case_insensitive():
    result = estimate_ram(8, "DDR4", [], RATES)
    assert result == {"value": 16.0, "method": "formule €/Go"}


def test_estimate_storage_known_type():
    result = estimate_storage(512, "ssd", [], RATES)
    assert result == {"value": 25.6, "method": "formule €/Go"}


def test_estimate_storage_unknown_type_returns_none():
    assert estimate_storage(512, "zip-disk", [], RATES) is None
```

Then append these new tests to the same file:

```python
def test_estimate_ram_uses_market_median_when_sources_find_prices():
    def source_a(size_go, ram_type):
        return [280.0, 300.0]

    def source_b(size_go, ram_type):
        return [320.0]

    result = estimate_ram(32, "ddr5", [source_a, source_b], RATES)

    assert result == {"value": 300.0, "method": "médiane sur 3 annonces neuves"}


def test_estimate_ram_falls_back_to_formula_when_no_market_results():
    def empty_source(size_go, ram_type):
        return []

    result = estimate_ram(16, "ddr4", [empty_source], RATES)

    assert result == {"value": 32.0, "method": "formule €/Go"}


def test_estimate_ram_falls_back_to_formula_when_no_search_fns():
    result = estimate_ram(16, "ddr4", [], RATES)

    assert result == {"value": 32.0, "method": "formule €/Go"}


def test_estimate_storage_uses_market_median_when_sources_find_prices():
    def source_a(size_go, storage_type):
        return [45.0, 50.0, 55.0]

    result = estimate_storage(512, "ssd", [source_a], RATES)

    assert result == {"value": 50.0, "method": "médiane sur 3 annonces neuves"}


def test_estimate_storage_falls_back_to_formula_when_no_market_results():
    def empty_source(size_go, storage_type):
        return []

    result = estimate_storage(512, "ssd", [empty_source], RATES)

    assert result == {"value": 25.6, "method": "formule €/Go"}


def test_estimate_ram_aggregates_sources_concurrently():
    import time

    def make_slow_source(price):
        def slow_source(size_go, ram_type):
            time.sleep(0.1)
            return [price]

        return slow_source

    slow_sources = [make_slow_source(280.0 + i) for i in range(5)]

    start = time.perf_counter()
    result = estimate_ram(32, "ddr5", slow_sources, RATES)
    elapsed = time.perf_counter() - start

    assert result is not None
    assert elapsed < 0.3, (
        f"expected concurrent execution (~0.1s), took {elapsed:.3f}s "
        "(sequential would take >=0.5s)"
    )
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_estimator.py -v`
Expected: FAIL — `estimate_ram()` still only accepts 3 positional args (`size_go, ram_type, rates`), so calls with 4 args raise `TypeError: estimate_ram() takes 3 positional arguments but 4 were given`

- [ ] **Step 3: Replace the aggregation section of `estimator.py`**

Find this exact block in `estimator.py`:

```python
def _run_search_fn_safely(search_fn, cpu_model, gpu_model):
    # search_fns aren't supposed to raise (each source is expected to fail
    # silently and return []), but a single misbehaving source shouldn't be
    # able to take down the whole aggregation, so we defend here too.
    try:
        return search_fn(cpu_model, gpu_model)
    except Exception:
        return []


def estimate_new_pc_price(cpu_model, gpu_model, search_fns):
    search_fns = list(search_fns)
    all_prices = []

    if search_fns:
        # Every search_fn does blocking network I/O (requests.get(...,
        # timeout=10)), so calling them sequentially means worst-case
        # wall-clock time is the SUM of all their timeouts. Threads give
        # real concurrency here because Python releases the GIL during
        # blocking I/O, so worst-case wall-clock time instead becomes the
        # slowest single source.
        with ThreadPoolExecutor(max_workers=len(search_fns)) as executor:
            futures = [
                executor.submit(_run_search_fn_safely, search_fn, cpu_model, gpu_model)
                for search_fn in search_fns
            ]
            for future in futures:
                all_prices.extend(future.result())

    if not all_prices:
        return None

    return {
        "value": median_price(all_prices),
        "method": f"médiane sur {len(all_prices)} annonces neuves",
    }
```

Replace it with:

```python
def _run_search_fn_safely(search_fn, arg1, arg2):
    # search_fns aren't supposed to raise (each source is expected to fail
    # silently and return []), but a single misbehaving source shouldn't be
    # able to take down the whole aggregation, so we defend here too. Shared
    # across every multi-source aggregation in this module (new-PC price,
    # RAM, storage) since every search_fn takes exactly two positional args.
    try:
        return search_fn(arg1, arg2)
    except Exception:
        return []


def _aggregate_market_prices(arg1, arg2, search_fns):
    # Shared by estimate_new_pc_price/estimate_ram/estimate_storage: run every
    # search_fn concurrently and merge whatever prices they find. Every
    # search_fn does blocking network I/O (requests.get(..., timeout=10)), so
    # calling them sequentially means worst-case wall-clock time is the SUM of
    # all their timeouts. Threads give real concurrency here because Python
    # releases the GIL during blocking I/O, so worst-case wall-clock time
    # instead becomes the slowest single source.
    search_fns = list(search_fns)
    all_prices = []

    if search_fns:
        with ThreadPoolExecutor(max_workers=len(search_fns)) as executor:
            futures = [
                executor.submit(_run_search_fn_safely, search_fn, arg1, arg2)
                for search_fn in search_fns
            ]
            for future in futures:
                all_prices.extend(future.result())

    return all_prices


def estimate_new_pc_price(cpu_model, gpu_model, search_fns):
    all_prices = _aggregate_market_prices(cpu_model, gpu_model, search_fns)

    if not all_prices:
        return None

    return {
        "value": median_price(all_prices),
        "method": f"médiane sur {len(all_prices)} annonces neuves",
    }
```

- [ ] **Step 4: Update `estimate_ram` and `estimate_storage` to try the market first**

Find this exact block:

```python
def estimate_ram(size_go, ram_type, rates):
    return _estimate_by_rate(size_go, ram_type, rates, "ram")


def estimate_storage(size_go, storage_type, rates):
    return _estimate_by_rate(size_go, storage_type, rates, "storage")
```

Replace it with:

```python
def estimate_ram(size_go, ram_type, search_fns, rates):
    all_prices = _aggregate_market_prices(size_go, ram_type, search_fns)
    if all_prices:
        return {
            "value": median_price(all_prices),
            "method": f"médiane sur {len(all_prices)} annonces neuves",
        }
    return _estimate_by_rate(size_go, ram_type, rates, "ram")


def estimate_storage(size_go, storage_type, search_fns, rates):
    all_prices = _aggregate_market_prices(size_go, storage_type, search_fns)
    if all_prices:
        return {
            "value": median_price(all_prices),
            "method": f"médiane sur {len(all_prices)} annonces neuves",
        }
    return _estimate_by_rate(size_go, storage_type, rates, "storage")
```

Note: `_run_search_fn_safely` and `_aggregate_market_prices` must be defined BEFORE `estimate_ram`/`estimate_storage` in the file (Python needs them defined before use at call time, though since they're only called inside function bodies, not at module load, definition order doesn't actually matter in Python — but keep the file readable by leaving `_run_search_fn_safely`/`_aggregate_market_prices` up near the top with the other shared helpers like `median_price`/`_estimate_by_rate`, matching the plan's File Structure intent of "small, focused, top-to-bottom-readable" files established in the original build).

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest tests/test_estimator.py -v`
Expected: all tests pass — this changes `estimate_ram`/`estimate_storage`'s tests (5 updated + 6 new = 11 RAM/storage-specific tests) plus all pre-existing `estimate_new_pc_price` tests must STILL pass unmodified (its observable behavior didn't change, only its internals were refactored)

- [ ] **Step 6: Run the full suite**

Run: `pytest -v`
Expected: FAIL at this point — `estimate_pc` (not yet updated) still calls `estimate_ram(ram_go, ram_type, component_rates)` with 3 args, which will now raise `TypeError` since `estimate_ram` requires 4. This is expected and fixed in Task 2. Confirm the failure is specifically in `test_estimate_pc_*` tests (in `tests/test_estimator.py`) and nothing else — if failures appear anywhere outside `test_estimate_pc_*`, investigate before proceeding.

- [ ] **Step 7: Commit**

```bash
git add estimator.py tests/test_estimator.py
git commit -m "feat: try market median before formula fallback for RAM/storage pricing"
```

---

### Task 2: `estimator.py` — wire market search into `estimate_pc`

**Files:**
- Modify: `estimator.py`
- Test: `tests/test_estimator.py`

## Context

Task 1 changed `estimate_ram`/`estimate_storage`'s signatures. `estimate_pc` still calls them with the old 3-argument form, which now raises `TypeError` — this task fixes that by adding two new parameters to `estimate_pc` itself (`ram_search_fns`, `storage_search_fns`) and threading them through.

- [ ] **Step 1: Update the 3 existing `estimate_pc` tests**

Find these 3 tests in `tests/test_estimator.py` and add `ram_search_fns=[]` and `storage_search_fns=[]` to each call (forces the formula fallback, preserving the existing expected values):

```python
def test_estimate_pc_full_breakdown_and_total():
    def fake_ebay_search(model, category):
        if category == "cpu":
            return [50.0, 55.0, 60.0]
        if category == "gpu":
            return [100.0, 110.0, 120.0]
        return []

    rates = {"ram": {"ddr4": 2.0}, "storage": {"ssd": 0.05}}
    result = estimate_pc(
        cpu_model="i5-10400",
        ram_go=16,
        ram_type="ddr4",
        storage_go=512,
        storage_type="ssd",
        gpu_model="gtx 1660",
        ebay_search_fn=fake_ebay_search,
        reference_prices={},
        component_rates=rates,
        ram_search_fns=[],
        storage_search_fns=[],
    )

    assert result["breakdown"]["cpu"]["value"] == 55.0
    assert result["breakdown"]["ram"]["value"] == 32.0
    assert result["breakdown"]["storage"]["value"] == 25.6
    assert result["breakdown"]["gpu"]["value"] == 110.0
    assert result["total"] == 55.0 + 32.0 + 25.6 + 110.0
    assert result["missing"] == []


def test_estimate_pc_without_gpu():
    def fake_ebay_search(model, category):
        return [50.0]

    rates = {"ram": {"ddr4": 2.0}, "storage": {"ssd": 0.05}}
    result = estimate_pc(
        cpu_model="i5-10400",
        ram_go=16,
        ram_type="ddr4",
        storage_go=512,
        storage_type="ssd",
        gpu_model="",
        ebay_search_fn=fake_ebay_search,
        reference_prices={},
        component_rates=rates,
        ram_search_fns=[],
        storage_search_fns=[],
    )

    assert result["breakdown"]["gpu"] is None
    assert "gpu" not in result["missing"]
    assert result["total"] == 50.0 + 32.0 + 25.6


def test_estimate_pc_flags_missing_components():
    def fake_ebay_search(model, category):
        return []

    rates = {"ram": {"ddr4": 2.0}, "storage": {"ssd": 0.05}}
    result = estimate_pc(
        cpu_model="unknown-cpu",
        ram_go=16,
        ram_type="ddr4",
        storage_go=512,
        storage_type="ssd",
        gpu_model="unknown-gpu",
        ebay_search_fn=fake_ebay_search,
        reference_prices={},
        component_rates=rates,
        ram_search_fns=[],
        storage_search_fns=[],
    )

    assert result["missing"] == ["cpu", "gpu"]
    assert result["breakdown"]["cpu"] is None
    assert result["total"] == 32.0 + 25.6
```

Then append one new test verifying `estimate_pc` actually uses market results when provided:

```python
def test_estimate_pc_uses_market_prices_for_ram_and_storage_when_available():
    def fake_ebay_search(model, category):
        return []

    def ram_source(size_go, ram_type):
        return [280.0, 300.0]

    def storage_source(size_go, storage_type):
        return [45.0, 50.0]

    rates = {"ram": {"ddr5": 9.5}, "storage": {"ssd": 0.05}}
    result = estimate_pc(
        cpu_model="unknown-cpu",
        ram_go=32,
        ram_type="ddr5",
        storage_go=512,
        storage_type="ssd",
        gpu_model="",
        ebay_search_fn=fake_ebay_search,
        reference_prices={},
        component_rates=rates,
        ram_search_fns=[ram_source],
        storage_search_fns=[storage_source],
    )

    assert result["breakdown"]["ram"] == {
        "value": 290.0,
        "method": "médiane sur 2 annonces neuves",
    }
    assert result["breakdown"]["storage"] == {
        "value": 47.5,
        "method": "médiane sur 2 annonces neuves",
    }
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_estimator.py -v -k estimate_pc`
Expected: FAIL — `estimate_pc()` doesn't accept `ram_search_fns`/`storage_search_fns` keyword arguments yet

- [ ] **Step 3: Update `estimate_pc`**

Find this exact block:

```python
def estimate_pc(
    cpu_model,
    ram_go,
    ram_type,
    storage_go,
    storage_type,
    gpu_model,
    ebay_search_fn,
    reference_prices,
    component_rates,
):
    breakdown = {}
    missing = []

    breakdown["cpu"] = estimate_component(cpu_model, "cpu", ebay_search_fn, reference_prices)
    if breakdown["cpu"] is None:
        missing.append("cpu")

    breakdown["ram"] = estimate_ram(ram_go, ram_type, component_rates)
    if breakdown["ram"] is None:
        missing.append("ram")

    breakdown["storage"] = estimate_storage(storage_go, storage_type, component_rates)
    if breakdown["storage"] is None:
        missing.append("storage")

    if gpu_model:
        breakdown["gpu"] = estimate_component(gpu_model, "gpu", ebay_search_fn, reference_prices)
        if breakdown["gpu"] is None:
            missing.append("gpu")
    else:
        breakdown["gpu"] = None

    total = sum(r["value"] for r in breakdown.values() if r is not None)

    return {"breakdown": breakdown, "total": round(total, 2), "missing": missing}
```

Replace it with:

```python
def estimate_pc(
    cpu_model,
    ram_go,
    ram_type,
    storage_go,
    storage_type,
    gpu_model,
    ebay_search_fn,
    reference_prices,
    component_rates,
    ram_search_fns,
    storage_search_fns,
):
    breakdown = {}
    missing = []

    breakdown["cpu"] = estimate_component(cpu_model, "cpu", ebay_search_fn, reference_prices)
    if breakdown["cpu"] is None:
        missing.append("cpu")

    breakdown["ram"] = estimate_ram(ram_go, ram_type, ram_search_fns, component_rates)
    if breakdown["ram"] is None:
        missing.append("ram")

    breakdown["storage"] = estimate_storage(
        storage_go, storage_type, storage_search_fns, component_rates
    )
    if breakdown["storage"] is None:
        missing.append("storage")

    if gpu_model:
        breakdown["gpu"] = estimate_component(gpu_model, "gpu", ebay_search_fn, reference_prices)
        if breakdown["gpu"] is None:
            missing.append("gpu")
    else:
        breakdown["gpu"] = None

    total = sum(r["value"] for r in breakdown.values() if r is not None)

    return {"breakdown": breakdown, "total": round(total, 2), "missing": missing}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_estimator.py -v`
Expected: all tests pass

- [ ] **Step 5: Run the full suite**

Run: `pytest -v`
Expected: FAIL — `cli.py`/`app.py` (not yet updated, Tasks 13-14) still call `estimator.estimate_pc(...)` without `ram_search_fns`/`storage_search_fns`, which now raises `TypeError`. Confirm the only failures are inside `tests/test_cli.py`/`tests/test_app.py` at the `estimate_pc`-calling tests — this is expected at this point in the plan and gets fixed in Tasks 13-14.

- [ ] **Step 6: Commit**

```bash
git add estimator.py tests/test_estimator.py
git commit -m "feat: wire ram_search_fns/storage_search_fns through estimate_pc"
```

---

### Task 3: `ebay_client.py` — RAM/storage new-condition search

**Files:**
- Modify: `ebay_client.py`
- Test: `tests/test_ebay_client.py`

- [ ] **Step 1: Write the failing tests**

```python
# append to tests/test_ebay_client.py
from ebay_client import search_ram_prices, search_storage_prices


@patch("ebay_client.search_new_prices")
@patch("ebay_client.get_access_token")
def test_search_ram_prices_returns_prices_on_success(mock_token, mock_search):
    mock_token.return_value = "tok"
    mock_search.return_value = [280.0, 300.0]

    result = search_ram_prices(32, "ddr5", "id", "secret")

    assert result == [280.0, 300.0]
    mock_search.assert_called_once_with("32Go ddr5 RAM", "tok")


@patch("ebay_client.get_access_token", side_effect=Exception("network error"))
def test_search_ram_prices_returns_empty_list_on_failure(mock_token):
    result = search_ram_prices(32, "ddr5", "id", "secret")
    assert result == []


@patch("ebay_client.search_new_prices")
@patch("ebay_client.get_access_token")
def test_search_storage_prices_returns_prices_on_success(mock_token, mock_search):
    mock_token.return_value = "tok"
    mock_search.return_value = [45.0, 50.0]

    result = search_storage_prices(512, "ssd", "id", "secret")

    assert result == [45.0, 50.0]
    mock_search.assert_called_once_with("512Go ssd", "tok")


@patch("ebay_client.get_access_token", side_effect=Exception("network error"))
def test_search_storage_prices_returns_empty_list_on_failure(mock_token):
    result = search_storage_prices(512, "ssd", "id", "secret")
    assert result == []
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_ebay_client.py -v`
Expected: FAIL with `ImportError: cannot import name 'search_ram_prices'`

- [ ] **Step 3: Add the two functions to `ebay_client.py`**

Append to `ebay_client.py` (after the existing `search_new_pc_prices` function):

```python
def search_ram_prices(ram_go, ram_type, client_id, client_secret):
    try:
        token = get_access_token(client_id, client_secret)
        return search_new_prices(f"{ram_go}Go {ram_type} RAM", token)
    except Exception:
        return []


def search_storage_prices(storage_go, storage_type, client_id, client_secret):
    try:
        token = get_access_token(client_id, client_secret)
        return search_new_prices(f"{storage_go}Go {storage_type}", token)
    except Exception:
        return []
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_ebay_client.py -v`
Expected: all tests pass (4 new tests added)

- [ ] **Step 5: Run the full suite**

Run: `pytest -v`
Expected: same expected failures as Task 2 Step 5 (cli.py/app.py not yet updated) — no NEW failures beyond those

- [ ] **Step 6: Commit**

```bash
git add ebay_client.py tests/test_ebay_client.py
git commit -m "feat: add eBay new-condition search for RAM and storage"
```

---

### Task 4: `retailers/ldlc.py` — refactor + RAM/storage search

**Files:**
- Modify: `retailers/ldlc.py`
- Create: `tests/fixtures/ldlc_ram_search.html`
- Create: `tests/fixtures/ldlc_storage_search.html`
- Test: `tests/test_retailers_ldlc.py`

## Context

`retailers/ldlc.py` currently has `search_prices(cpu_model, gpu_model)` containing the full HTTP-fetch + BeautifulSoup-parse logic inline. This task extracts that logic into a shared `_search(query)` helper (query-only, no behavior change), then adds `search_ram_prices(ram_go, ram_type)` and `search_storage_prices(storage_go, storage_type)` that call `_search(...)` with different queries.

**The refactor must not change `search_prices`'s observable behavior** — the existing tests (`test_search_prices_extracts_prices_from_real_fixture`, `test_search_prices_returns_empty_list_on_network_failure`, `test_search_prices_returns_empty_list_on_unparseable_html`, `test_search_prices_query_excludes_cpu_model`) must all still pass unmodified after the refactor.

**The RAM/storage query wording below is a starting guess, not proven.** You must validate it against the live site the same way LDLC's PC-search query was validated (documented in the file's existing comments) — try a query like `"16Go DDR4"` for RAM and `"512Go SSD"` for storage against `https://www.ldlc.com/recherche/{query}/`, and confirm it returns real, relevant RAM/storage listings (not zero results, not unrelated products). If the literal query below doesn't work well, adjust it based on what you find, and update the code comment to explain what you tried and why you picked your final query — following the same documentation style already used in this file for the PC-search query.

**The card/price selectors (`li.pdt-item`, `.price .price`) are very likely reusable as-is**, since they come from the same site's general search results template — but confirm this against your captured RAM/storage fixtures rather than assuming.

- [ ] **Step 1: Research the live site for RAM and storage queries**

Use your web browsing/fetch tools to search LDLC for RAM (try `"16Go DDR4"` first, adjust based on what you find) and separately for storage (try `"512Go SSD"` first, adjust based on what you find). For each, confirm the results are genuinely RAM/storage listings with real prices, record the query that worked, and save the raw HTML to `tests/fixtures/ldlc_ram_search.html` and `tests/fixtures/ldlc_storage_search.html` respectively.

- [ ] **Step 2: Write the failing tests**

```python
# append to tests/test_retailers_ldlc.py
from retailers.ldlc import search_ram_prices, search_storage_prices


@patch("retailers.ldlc.requests.get")
def test_search_ram_prices_extracts_prices_from_real_fixture(mock_get):
    with open("tests/fixtures/ldlc_ram_search.html", encoding="utf-8") as f:
        html = f.read()

    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.text = html
    mock_get.return_value = mock_response

    prices = search_ram_prices(16, "ddr4")

    assert isinstance(prices, list)
    assert all(isinstance(p, float) for p in prices)
    # tighten to the exact expected price list once you've inspected the fixture


@patch("retailers.ldlc.requests.get", side_effect=Exception("network error"))
def test_search_ram_prices_returns_empty_list_on_network_failure(mock_get):
    assert search_ram_prices(16, "ddr4") == []


@patch("retailers.ldlc.requests.get")
def test_search_storage_prices_extracts_prices_from_real_fixture(mock_get):
    with open("tests/fixtures/ldlc_storage_search.html", encoding="utf-8") as f:
        html = f.read()

    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.text = html
    mock_get.return_value = mock_response

    prices = search_storage_prices(512, "ssd")

    assert isinstance(prices, list)
    assert all(isinstance(p, float) for p in prices)
    # tighten to the exact expected price list once you've inspected the fixture


@patch("retailers.ldlc.requests.get", side_effect=Exception("network error"))
def test_search_storage_prices_returns_empty_list_on_network_failure(mock_get):
    assert search_storage_prices(512, "ssd") == []
```

Tighten both fixture-based tests' assertions to the exact expected price list once you've inspected your captured fixtures (don't leave a weak `len(prices) >= 0` check in the final version — assert the real values, following the same pattern used for `test_search_prices_extracts_prices_from_real_fixture` earlier in this file).

- [ ] **Step 3: Run tests to verify they fail**

Run: `pytest tests/test_retailers_ldlc.py -v`
Expected: FAIL with `ImportError: cannot import name 'search_ram_prices'`

- [ ] **Step 4: Refactor `retailers/ldlc.py`**

Replace the existing `search_prices` function:

```python
def search_prices(cpu_model, gpu_model):
    try:
        # LDLC's search does strict AND-matching; including both CPU and GPU model
        # returns almost nothing (verified during research), so we search by GPU
        # + a generic "PC gamer" term instead
        query = f"PC gamer {gpu_model}"
        url = SEARCH_URL.format(query=requests.utils.quote(query))
        response = requests.get(url, headers=HEADERS, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        prices = []
        for card in soup.select("li.pdt-item"):
            price_el = card.select_one(".price .price")
            if price_el is None:
                continue
            price = _extract_price(_price_text(price_el))
            if price is not None:
                prices.append(price)
        return prices
    except Exception:
        return []
```

With this (extracts the shared `_search(query)` helper, then adds the two new functions):

```python
def _search(query):
    try:
        url = SEARCH_URL.format(query=requests.utils.quote(query))
        response = requests.get(url, headers=HEADERS, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        prices = []
        for card in soup.select("li.pdt-item"):
            price_el = card.select_one(".price .price")
            if price_el is None:
                continue
            price = _extract_price(_price_text(price_el))
            if price is not None:
                prices.append(price)
        return prices
    except Exception:
        return []


def search_prices(cpu_model, gpu_model):
    # LDLC's search does strict AND-matching; including both CPU and GPU model
    # returns almost nothing (verified during research), so we search by GPU
    # + a generic "PC gamer" term instead
    return _search(f"PC gamer {gpu_model}")


def search_ram_prices(ram_go, ram_type):
    # ADJUST based on your live research in Step 1 if this exact wording
    # didn't work well
    return _search(f"{ram_go}Go {ram_type}")


def search_storage_prices(storage_go, storage_type):
    # ADJUST based on your live research in Step 1 if this exact wording
    # didn't work well
    return _search(f"{storage_go}Go {storage_type}")
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest tests/test_retailers_ldlc.py -v`
Expected: all tests pass, including all 5 pre-existing `search_prices` tests (unmodified, confirming the refactor didn't change behavior) plus the 4 new ones

- [ ] **Step 6: Run the full suite**

Run: `pytest -v`
Expected: no NEW failures beyond the already-expected `cli.py`/`app.py` ones from Task 2 Step 5

- [ ] **Step 7: Commit**

```bash
git add retailers/ldlc.py tests/test_retailers_ldlc.py tests/fixtures/ldlc_ram_search.html tests/fixtures/ldlc_storage_search.html
git commit -m "feat: add LDLC RAM/storage price search"
```

---

### Task 5: `retailers/pccomponentes.py` — refactor + RAM/storage search

**Files:**
- Modify: `retailers/pccomponentes.py`
- Create: `tests/fixtures/pccomponentes_ram_search.html`
- Create: `tests/fixtures/pccomponentes_storage_search.html`
- Test: `tests/test_retailers_pccomponentes.py`

## Context

Same refactor pattern as Task 4, applied to PcComponentes (which uses the `data-product-price` attribute directly — no `_extract_price`/`_price_text` helpers here). Research live RAM (try `"16Go DDR4"`) and storage (try `"512Go SSD"`) queries against `https://www.pccomponentes.fr/search?query={query}`, adjusting wording as needed, same validation discipline as Task 4.

- [ ] **Step 1: Research the live site for RAM and storage queries**

Same process as Task 4 Step 1, targeting PcComponentes. Save fixtures to `tests/fixtures/pccomponentes_ram_search.html` and `tests/fixtures/pccomponentes_storage_search.html`.

- [ ] **Step 2: Write the failing tests**

```python
# append to tests/test_retailers_pccomponentes.py
from retailers.pccomponentes import search_ram_prices, search_storage_prices


@patch("retailers.pccomponentes.requests.get")
def test_search_ram_prices_extracts_prices_from_real_fixture(mock_get):
    with open("tests/fixtures/pccomponentes_ram_search.html", encoding="utf-8") as f:
        html = f.read()

    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.text = html
    mock_get.return_value = mock_response

    prices = search_ram_prices(16, "ddr4")

    assert isinstance(prices, list)
    assert all(isinstance(p, float) for p in prices)


@patch("retailers.pccomponentes.requests.get", side_effect=Exception("network error"))
def test_search_ram_prices_returns_empty_list_on_network_failure(mock_get):
    assert search_ram_prices(16, "ddr4") == []


@patch("retailers.pccomponentes.requests.get")
def test_search_storage_prices_extracts_prices_from_real_fixture(mock_get):
    with open("tests/fixtures/pccomponentes_storage_search.html", encoding="utf-8") as f:
        html = f.read()

    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.text = html
    mock_get.return_value = mock_response

    prices = search_storage_prices(512, "ssd")

    assert isinstance(prices, list)
    assert all(isinstance(p, float) for p in prices)


@patch("retailers.pccomponentes.requests.get", side_effect=Exception("network error"))
def test_search_storage_prices_returns_empty_list_on_network_failure(mock_get):
    assert search_storage_prices(512, "ssd") == []
```

Tighten both fixture-based tests to exact expected price lists once fixtures are captured, as in Task 4.

- [ ] **Step 3: Run tests to verify they fail**

Run: `pytest tests/test_retailers_pccomponentes.py -v`
Expected: FAIL with `ImportError: cannot import name 'search_ram_prices'`

- [ ] **Step 4: Refactor `retailers/pccomponentes.py`**

Replace the existing `search_prices` function:

```python
def search_prices(cpu_model, gpu_model):
    try:
        query = f"{cpu_model} {gpu_model}"
        url = SEARCH_URL.format(query=requests.utils.quote(query))
        response = requests.get(url, headers=HEADERS, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        prices = []
        for card in soup.select("a[data-product-price]"):
            raw_price = card.get("data-product-price")
            if raw_price is None:
                continue
            try:
                price = float(raw_price)
            except ValueError:
                continue
            prices.append(price)
        return prices
    except Exception:
        return []
```

With this:

```python
def _search(query):
    try:
        url = SEARCH_URL.format(query=requests.utils.quote(query))
        response = requests.get(url, headers=HEADERS, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        prices = []
        for card in soup.select("a[data-product-price]"):
            raw_price = card.get("data-product-price")
            if raw_price is None:
                continue
            try:
                price = float(raw_price)
            except ValueError:
                continue
            prices.append(price)
        return prices
    except Exception:
        return []


def search_prices(cpu_model, gpu_model):
    return _search(f"{cpu_model} {gpu_model}")


def search_ram_prices(ram_go, ram_type):
    # ADJUST based on your live research in Step 1 if this exact wording
    # didn't work well
    return _search(f"{ram_go}Go {ram_type}")


def search_storage_prices(storage_go, storage_type):
    # ADJUST based on your live research in Step 1 if this exact wording
    # didn't work well
    return _search(f"{storage_go}Go {storage_type}")
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest tests/test_retailers_pccomponentes.py -v`
Expected: all tests pass, including all pre-existing `search_prices` tests unmodified

- [ ] **Step 6: Run the full suite**

Run: `pytest -v`
Expected: no new failures beyond the already-expected ones

- [ ] **Step 7: Commit**

```bash
git add retailers/pccomponentes.py tests/test_retailers_pccomponentes.py tests/fixtures/pccomponentes_ram_search.html tests/fixtures/pccomponentes_storage_search.html
git commit -m "feat: add PcComponentes RAM/storage price search"
```

---

### Task 6: `retailers/materiel_net.py` — refactor + RAM/storage search

**Files:**
- Modify: `retailers/materiel_net.py`
- Create: `tests/fixtures/materiel_net_ram_search.html`
- Create: `tests/fixtures/materiel_net_storage_search.html`
- Test: `tests/test_retailers_materiel_net.py`

## Context

Same refactor pattern as Task 4, applied to Materiel.net (same LDLC-group platform, same `_extract_price`/`_price_text` helpers, same `li.c-products-list__item` / `.o-product__price:not(.o-product__cut-price)` selectors). Research live RAM/storage queries against `https://www.materiel.net/recherche/{query}/`. Materiel.net's PC search needed `"PC gamer {gpu}"` due to strict AND-matching — a simpler RAM/storage query like `"16Go DDR4"` may or may not have the same problem; validate live rather than assuming either way.

- [ ] **Step 1: Research the live site for RAM and storage queries**

Same process as Task 4 Step 1, targeting Materiel.net. Save fixtures to `tests/fixtures/materiel_net_ram_search.html` and `tests/fixtures/materiel_net_storage_search.html`.

- [ ] **Step 2: Write the failing tests**

```python
# append to tests/test_retailers_materiel_net.py
from retailers.materiel_net import search_ram_prices, search_storage_prices


@patch("retailers.materiel_net.requests.get")
def test_search_ram_prices_extracts_prices_from_real_fixture(mock_get):
    with open("tests/fixtures/materiel_net_ram_search.html", encoding="utf-8") as f:
        html = f.read()

    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.text = html
    mock_get.return_value = mock_response

    prices = search_ram_prices(16, "ddr4")

    assert isinstance(prices, list)
    assert all(isinstance(p, float) for p in prices)


@patch("retailers.materiel_net.requests.get", side_effect=Exception("network error"))
def test_search_ram_prices_returns_empty_list_on_network_failure(mock_get):
    assert search_ram_prices(16, "ddr4") == []


@patch("retailers.materiel_net.requests.get")
def test_search_storage_prices_extracts_prices_from_real_fixture(mock_get):
    with open("tests/fixtures/materiel_net_storage_search.html", encoding="utf-8") as f:
        html = f.read()

    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.text = html
    mock_get.return_value = mock_response

    prices = search_storage_prices(512, "ssd")

    assert isinstance(prices, list)
    assert all(isinstance(p, float) for p in prices)


@patch("retailers.materiel_net.requests.get", side_effect=Exception("network error"))
def test_search_storage_prices_returns_empty_list_on_network_failure(mock_get):
    assert search_storage_prices(512, "ssd") == []
```

Tighten both fixture-based tests to exact expected price lists once fixtures are captured.

- [ ] **Step 3: Run tests to verify they fail**

Run: `pytest tests/test_retailers_materiel_net.py -v`
Expected: FAIL with `ImportError: cannot import name 'search_ram_prices'`

- [ ] **Step 4: Refactor `retailers/materiel_net.py`**

Replace the existing `search_prices` function:

```python
def search_prices(cpu_model, gpu_model):
    try:
        # Verified live: Materiel.net's search does strict AND-matching, just
        # like LDLC (both are part of the LDLC Group and share the same
        # search platform). Combining the CPU and GPU model returns almost
        # nothing ("Ryzen 7 5700X RTX 4060" -> 3 unrelated products: an
        # adapter cable and a motherboard). Searching by GPU model alone is
        # too narrow too (only 2 exact-match products). "PC gamer {gpu}"
        # returns a full page of complete gaming-PC listings (208 results),
        # mirroring the query shape already validated for LDLC, so we reuse
        # it here and never leak the CPU model into the query.
        query = f"PC gamer {gpu_model}"
        url = SEARCH_URL.format(query=requests.utils.quote(query))
        response = requests.get(url, headers=HEADERS, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        prices = []
        for card in soup.select("li.c-products-list__item"):
            # No structured price attribute or JSON-LD block exists on this
            # page (verified live via DOM inspection), so we fall back to
            # parsing the display text. Promo items render two price spans
            # inside .c-product__prices: the struck-through original price
            # (class o-product__cut-price) and the current discounted price
            # (class o-product__price--promo). Non-promo items render just
            # one plain .o-product__price span. Excluding .o-product__cut-price
            # picks the right one in both cases with a single selector.
            price_el = card.select_one(".o-product__price:not(.o-product__cut-price)")
            if price_el is None:
                continue
            price = _extract_price(_price_text(price_el))
            if price is not None:
                prices.append(price)
        return prices
    except Exception:
        return []
```

With this:

```python
def _search(query):
    try:
        url = SEARCH_URL.format(query=requests.utils.quote(query))
        response = requests.get(url, headers=HEADERS, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        prices = []
        for card in soup.select("li.c-products-list__item"):
            price_el = card.select_one(".o-product__price:not(.o-product__cut-price)")
            if price_el is None:
                continue
            price = _extract_price(_price_text(price_el))
            if price is not None:
                prices.append(price)
        return prices
    except Exception:
        return []


def search_prices(cpu_model, gpu_model):
    # Verified live: Materiel.net's search does strict AND-matching, just
    # like LDLC (both are part of the LDLC Group and share the same
    # search platform). "PC gamer {gpu}" returns a full page of complete
    # gaming-PC listings, mirroring the query shape validated for LDLC.
    return _search(f"PC gamer {gpu_model}")


def search_ram_prices(ram_go, ram_type):
    # ADJUST based on your live research in Step 1 if this exact wording
    # didn't work well
    return _search(f"{ram_go}Go {ram_type}")


def search_storage_prices(storage_go, storage_type):
    # ADJUST based on your live research in Step 1 if this exact wording
    # didn't work well
    return _search(f"{storage_go}Go {storage_type}")
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest tests/test_retailers_materiel_net.py -v`
Expected: all tests pass, including all pre-existing `search_prices` tests unmodified

- [ ] **Step 6: Run the full suite**

Run: `pytest -v`
Expected: no new failures beyond the already-expected ones

- [ ] **Step 7: Commit**

```bash
git add retailers/materiel_net.py tests/test_retailers_materiel_net.py tests/fixtures/materiel_net_ram_search.html tests/fixtures/materiel_net_storage_search.html
git commit -m "feat: add Materiel.net RAM/storage price search"
```

---

### Task 7: `retailers/topachat.py` — refactor + RAM/storage search

**Files:**
- Modify: `retailers/topachat.py`
- Create: `tests/fixtures/topachat_ram_search.html`
- Create: `tests/fixtures/topachat_storage_search.html`
- Test: `tests/test_retailers_topachat.py`

## Context

TopAchat is the JSON-API-backed retailer (no HTML scraping). The existing `search_prices` hardcodes `PC_CATEGORY_LABEL = "PC Gamer"` to filter the API's category-grouped results. **RAM and storage will almost certainly live under different category labels** (e.g. something like "Mémoire" for RAM, "Disque dur / SSD" for storage — these are guesses, not confirmed). This task's research step must inspect a real API response for a RAM query and a storage query to find the actual category label(s) to filter on — don't guess, read the real JSON.

- [ ] **Step 1: Research the live API for RAM and storage category labels**

Query `https://www.topachat.com/api/search/search.main.php` with `params={"terms": "16Go DDR4"}` (adjust wording if needed) and inspect the JSON response's `result.document.categories` list — find the `label_category` value(s) that correspond to actual RAM product listings (not motherboards, not prebuilt PCs that happen to mention RAM). Do the same for storage with a query like `"512Go SSD"`. Save each raw JSON response to `tests/fixtures/topachat_ram_search.html` and `tests/fixtures/topachat_storage_search.html` (keeping the `.html` extension for consistency with the plan's file list, even though the content is JSON — same convention already used for `tests/fixtures/topachat_search.html`).

- [ ] **Step 2: Write the failing tests**

```python
# append to tests/test_retailers_topachat.py
import json

from retailers.topachat import search_ram_prices, search_storage_prices


@patch("retailers.topachat.requests.get")
def test_search_ram_prices_extracts_prices_from_real_fixture(mock_get):
    with open("tests/fixtures/topachat_ram_search.html", encoding="utf-8") as f:
        fixture_json = json.load(f)

    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = fixture_json
    mock_get.return_value = mock_response

    prices = search_ram_prices(16, "ddr4")

    assert isinstance(prices, list)
    assert all(isinstance(p, float) for p in prices)


@patch("retailers.topachat.requests.get", side_effect=Exception("network error"))
def test_search_ram_prices_returns_empty_list_on_network_failure(mock_get):
    assert search_ram_prices(16, "ddr4") == []


@patch("retailers.topachat.requests.get")
def test_search_storage_prices_extracts_prices_from_real_fixture(mock_get):
    with open("tests/fixtures/topachat_storage_search.html", encoding="utf-8") as f:
        fixture_json = json.load(f)

    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = fixture_json
    mock_get.return_value = mock_response

    prices = search_storage_prices(512, "ssd")

    assert isinstance(prices, list)
    assert all(isinstance(p, float) for p in prices)


@patch("retailers.topachat.requests.get", side_effect=Exception("network error"))
def test_search_storage_prices_returns_empty_list_on_network_failure(mock_get):
    assert search_storage_prices(512, "ssd") == []
```

Tighten both fixture-based tests to exact expected price lists once you've inspected your captured JSON fixtures.

- [ ] **Step 3: Run tests to verify they fail**

Run: `pytest tests/test_retailers_topachat.py -v`
Expected: FAIL with `ImportError: cannot import name 'search_ram_prices'`

- [ ] **Step 4: Refactor `retailers/topachat.py`**

Replace the existing `search_prices` function and `PC_CATEGORY_LABEL` constant:

```python
# The only category that contains complete desktop PC builds. The same
# search also returns "PC DIY (kit à monter)", "Kit d'évolution", loose
# "Processeur" listings, and laptop categories ("PC Portable Gamer",
# "PC Portable"), which are not complete-PC prices and would skew the
# result, so they're filtered out.
PC_CATEGORY_LABEL = "PC Gamer"


def search_prices(cpu_model, gpu_model):
    try:
        # Unlike LDLC (strict AND-matching, chokes on combined CPU+GPU
        # queries), TopAchat's search handles a combined query well: verified
        # live that "Ryzen 7 5700X RTX 4060" returned a "PC Gamer" category
        # where 13 of the first 15 sampled builds actually contain a Ryzen 7
        # 5700X, versus a GPU-only "PC gamer RTX 4060" query which mixed in
        # many unrelated CPUs (Ryzen 5 5500, Ryzen 7 7800X3D, Ryzen 7 9800X3D,
        # etc.). So, like PcComponentes, we keep both models in the query.
        query = f"{cpu_model} {gpu_model}"
        response = requests.get(
            SEARCH_URL, params={"terms": query}, headers=HEADERS, timeout=10
        )
        response.raise_for_status()
        data = response.json()

        prices = []
        categories = data["result"]["document"]["categories"]
        for category in categories:
            if category.get("label_category") != PC_CATEGORY_LABEL:
                continue
            for product in category.get("product", []):
                offer = product.get("offer")
                if not offer or "price_final" not in offer:
                    continue
                # price_final is an integer number of cents (e.g. 144999 for
                # 1449.99 €).
                prices.append(round(offer["price_final"] / 100, 2))
        return prices
    except Exception:
        return []
```

With this:

```python
# The only category that contains complete desktop PC builds. The same
# search also returns "PC DIY (kit à monter)", "Kit d'évolution", loose
# "Processeur" listings, and laptop categories ("PC Portable Gamer",
# "PC Portable"), which are not complete-PC prices and would skew the
# result, so they're filtered out.
PC_CATEGORY_LABEL = "PC Gamer"

# ADJUST both of these based on your live research in Step 1 -- read a real
# API response for a RAM/storage query and use the actual label_category
# value(s) that correspond to real RAM/storage listings.
RAM_CATEGORY_LABEL = "Mémoire"
STORAGE_CATEGORY_LABEL = "Disque dur / SSD"


def _search(query, category_label):
    try:
        response = requests.get(
            SEARCH_URL, params={"terms": query}, headers=HEADERS, timeout=10
        )
        response.raise_for_status()
        data = response.json()

        prices = []
        categories = data["result"]["document"]["categories"]
        for category in categories:
            if category.get("label_category") != category_label:
                continue
            for product in category.get("product", []):
                offer = product.get("offer")
                if not offer or "price_final" not in offer:
                    continue
                # price_final is an integer number of cents (e.g. 144999 for
                # 1449.99 €).
                prices.append(round(offer["price_final"] / 100, 2))
        return prices
    except Exception:
        return []


def search_prices(cpu_model, gpu_model):
    # Unlike LDLC (strict AND-matching, chokes on combined CPU+GPU queries),
    # TopAchat's search handles a combined query well (verified live). So,
    # like PcComponentes, we keep both models in the query.
    query = f"{cpu_model} {gpu_model}"
    return _search(query, PC_CATEGORY_LABEL)


def search_ram_prices(ram_go, ram_type):
    query = f"{ram_go}Go {ram_type}"
    return _search(query, RAM_CATEGORY_LABEL)


def search_storage_prices(storage_go, storage_type):
    query = f"{storage_go}Go {storage_type}"
    return _search(query, STORAGE_CATEGORY_LABEL)
```

**Note:** if your Step 1 research finds that RAM or storage listings are actually spread across MORE THAN ONE category label (e.g. separate labels for "RAM de bureau" vs "RAM portable"), adjust `_search`/`RAM_CATEGORY_LABEL` to accept and check against a tuple of labels instead of a single string — but only make this change if your real research shows it's actually needed, don't guess preemptively.

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest tests/test_retailers_topachat.py -v`
Expected: all tests pass, including all pre-existing `search_prices` tests unmodified

- [ ] **Step 6: Run the full suite**

Run: `pytest -v`
Expected: no new failures beyond the already-expected ones

- [ ] **Step 7: Commit**

```bash
git add retailers/topachat.py tests/test_retailers_topachat.py tests/fixtures/topachat_ram_search.html tests/fixtures/topachat_storage_search.html
git commit -m "feat: add TopAchat RAM/storage price search"
```

---

### Task 8: `retailers/grosbill.py` — refactor + RAM/storage search

**Files:**
- Modify: `retailers/grosbill.py`
- Create: `tests/fixtures/grosbill_ram_search.html`
- Create: `tests/fixtures/grosbill_storage_search.html`
- Test: `tests/test_retailers_grosbill.py`

## Context

Same refactor pattern as Task 4, applied to Grosbill. Grosbill's PC search needed `"PC gamer {cpu}"` due to strict AND-matching and a catalog-mismatch on GPU. A RAM/storage query is a different, simpler product category — validate live whether it needs a similar "PC gamer"-style prefix (unlikely, since RAM/storage aren't "PC gamer" category items) or works fine as a bare `"16Go DDR4"`-style query against `https://www.grosbill.com/produit.aspx`.

- [ ] **Step 1: Research the live site for RAM and storage queries**

Same process as Task 4 Step 1, targeting Grosbill. Save fixtures to `tests/fixtures/grosbill_ram_search.html` and `tests/fixtures/grosbill_storage_search.html`.

- [ ] **Step 2: Write the failing tests**

```python
# append to tests/test_retailers_grosbill.py
from retailers.grosbill import search_ram_prices, search_storage_prices


@patch("retailers.grosbill.requests.get")
def test_search_ram_prices_extracts_prices_from_real_fixture(mock_get):
    with open("tests/fixtures/grosbill_ram_search.html", encoding="utf-8") as f:
        html = f.read()

    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.text = html
    mock_get.return_value = mock_response

    prices = search_ram_prices(16, "ddr4")

    assert isinstance(prices, list)
    assert all(isinstance(p, float) for p in prices)


@patch("retailers.grosbill.requests.get", side_effect=Exception("network error"))
def test_search_ram_prices_returns_empty_list_on_network_failure(mock_get):
    assert search_ram_prices(16, "ddr4") == []


@patch("retailers.grosbill.requests.get")
def test_search_storage_prices_extracts_prices_from_real_fixture(mock_get):
    with open("tests/fixtures/grosbill_storage_search.html", encoding="utf-8") as f:
        html = f.read()

    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.text = html
    mock_get.return_value = mock_response

    prices = search_storage_prices(512, "ssd")

    assert isinstance(prices, list)
    assert all(isinstance(p, float) for p in prices)


@patch("retailers.grosbill.requests.get", side_effect=Exception("network error"))
def test_search_storage_prices_returns_empty_list_on_network_failure(mock_get):
    assert search_storage_prices(512, "ssd") == []
```

Tighten both fixture-based tests to exact expected price lists once fixtures are captured.

- [ ] **Step 3: Run tests to verify they fail**

Run: `pytest tests/test_retailers_grosbill.py -v`
Expected: FAIL with `ImportError: cannot import name 'search_ram_prices'`

- [ ] **Step 4: Refactor `retailers/grosbill.py`**

Replace the existing `search_prices` function:

```python
def search_prices(cpu_model, gpu_model):
    try:
        # Grosbill's search does strict AND-matching, just like LDLC and
        # Materiel.net (verified live: "Ryzen 7 5700X RTX 4060" returns
        # "aucun produit ne correspond"). Grosbill's current build lineup
        # pairs this CPU with newer GPUs (RTX 5060/5070), not the requested
        # RTX 4060, so keeping the GPU term in the query would zero out
        # results entirely. A bare CPU-model search ("Ryzen 7 5700X") does
        # return matches, but mixes in standalone CPU component listings
        # alongside the complete builds. Prefixing with "PC gamer" (verified
        # live) filters the result set down to only the "PC Gamer" complete-
        # build category -- 5 matching builds, all containing the CPU model,
        # with no components mixed in. So, like ldlc.py, we drop the GPU
        # model from the query -- but unlike ldlc.py (which drops the CPU
        # and keeps the GPU), here it's the GPU that's dropped and the CPU
        # that's kept, because that's what this catalog actually has stock
        # of for this CPU.
        query = f"PC gamer {cpu_model}"
        response = requests.get(
            SEARCH_URL, params={"q": query}, headers=HEADERS, timeout=10
        )
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        prices = []
        # No JSON API (the search is a classic server-rendered .aspx page,
        # no XHR/JSON calls involved -- verified live via network inspection),
        # no data-price attribute, no itemprop="price", and no product-level
        # JSON-LD block (only a BreadcrumbList schema exists) -- verified
        # against the fixture. The closest thing to structured price data is
        # a dedicated reference/price span rendered per product card,
        # holding the price as plain "<euros>,<cents>" text (e.g. "1649,99")
        # with no currency symbol or markup to strip, unlike the
        # €<sup>cents</sup> pattern LDLC/Materiel.net require picking apart.
        for card in soup.select("div.grb__liste-produit__liste__produit"):
            price_el = card.select_one(
                "span.grb__liste-produit__liste__produit__reference-container"
                "__content_prix_produit"
            )
            if price_el is None:
                continue
            raw_price = price_el.get_text(strip=True).replace(",", ".")
            try:
                price = float(raw_price)
            except ValueError:
                continue
            prices.append(price)
        return prices
    except Exception:
        return []
```

With this:

```python
def _search(query):
    try:
        response = requests.get(
            SEARCH_URL, params={"q": query}, headers=HEADERS, timeout=10
        )
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        prices = []
        for card in soup.select("div.grb__liste-produit__liste__produit"):
            price_el = card.select_one(
                "span.grb__liste-produit__liste__produit__reference-container"
                "__content_prix_produit"
            )
            if price_el is None:
                continue
            raw_price = price_el.get_text(strip=True).replace(",", ".")
            try:
                price = float(raw_price)
            except ValueError:
                continue
            prices.append(price)
        return prices
    except Exception:
        return []


def search_prices(cpu_model, gpu_model):
    # Grosbill's search does strict AND-matching (verified live). Grosbill's
    # current build lineup pairs this CPU with newer GPUs, so we drop the
    # GPU term and keep the CPU, prefixed with "PC gamer" to filter down to
    # the complete-build category.
    return _search(f"PC gamer {cpu_model}")


def search_ram_prices(ram_go, ram_type):
    # ADJUST based on your live research in Step 1 if this exact wording
    # didn't work well
    return _search(f"{ram_go}Go {ram_type}")


def search_storage_prices(storage_go, storage_type):
    # ADJUST based on your live research in Step 1 if this exact wording
    # didn't work well
    return _search(f"{storage_go}Go {storage_type}")
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest tests/test_retailers_grosbill.py -v`
Expected: all tests pass, including all pre-existing `search_prices` tests unmodified

- [ ] **Step 6: Run the full suite**

Run: `pytest -v`
Expected: no new failures beyond the already-expected ones

- [ ] **Step 7: Commit**

```bash
git add retailers/grosbill.py tests/test_retailers_grosbill.py tests/fixtures/grosbill_ram_search.html tests/fixtures/grosbill_storage_search.html
git commit -m "feat: add Grosbill RAM/storage price search"
```

---

### Task 9: `retailers/rueducommerce.py` — refactor + RAM/storage search

**Files:**
- Modify: `retailers/rueducommerce.py`
- Create: `tests/fixtures/rueducommerce_ram_search.html`
- Create: `tests/fixtures/rueducommerce_storage_search.html`
- Test: `tests/test_retailers_rueducommerce.py`

## Context

Rue du Commerce's `search_prices` combines a title-relevance filter (`_title_matches_model`, checking that a card's title mentions both `cpu_model` and `gpu_model`) with price extraction. This task extracts the HTTP-fetch and price-extraction pieces into shared helpers (`_fetch_soup(query)`, `_extract_card_price(card)`), but does **not** apply title-filtering to the new RAM/storage functions by default, since there's no natural CPU/GPU-style "model" to filter by for a RAM/storage search. **If your live research in Step 1 shows the RAM/storage search results are noisy** (e.g. mixing in unrelated products, wrong sizes/types) the same way the PC search was, add a similar relevance check — `_title_matches_model` already does generic substring-with-boundary matching, so it can be reused as-is against a size string like `"16Go"` or a type string like `"DDR4"` if needed. Only add this if your research shows it's actually necessary — check first, don't assume.

- [ ] **Step 1: Research the live site for RAM and storage queries**

Same process as Task 4 Step 1, targeting Rue du Commerce (`https://www.rueducommerce.fr/recherche/{query}/`). Check whether the results are clean enough to use without title-filtering, or whether noise requires adding it (see Context above). Save fixtures to `tests/fixtures/rueducommerce_ram_search.html` and `tests/fixtures/rueducommerce_storage_search.html`.

- [ ] **Step 2: Write the failing tests**

```python
# append to tests/test_retailers_rueducommerce.py
from retailers.rueducommerce import search_ram_prices, search_storage_prices


@patch("retailers.rueducommerce.requests.get")
def test_search_ram_prices_extracts_prices_from_real_fixture(mock_get):
    with open("tests/fixtures/rueducommerce_ram_search.html", encoding="utf-8") as f:
        html = f.read()

    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.text = html
    mock_get.return_value = mock_response

    prices = search_ram_prices(16, "ddr4")

    assert isinstance(prices, list)
    assert all(isinstance(p, float) for p in prices)


@patch("retailers.rueducommerce.requests.get", side_effect=Exception("network error"))
def test_search_ram_prices_returns_empty_list_on_network_failure(mock_get):
    assert search_ram_prices(16, "ddr4") == []


@patch("retailers.rueducommerce.requests.get")
def test_search_storage_prices_extracts_prices_from_real_fixture(mock_get):
    with open("tests/fixtures/rueducommerce_storage_search.html", encoding="utf-8") as f:
        html = f.read()

    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.text = html
    mock_get.return_value = mock_response

    prices = search_storage_prices(512, "ssd")

    assert isinstance(prices, list)
    assert all(isinstance(p, float) for p in prices)


@patch("retailers.rueducommerce.requests.get", side_effect=Exception("network error"))
def test_search_storage_prices_returns_empty_list_on_network_failure(mock_get):
    assert search_storage_prices(512, "ssd") == []
```

Tighten both fixture-based tests to exact expected price lists once fixtures are captured (or, if you added title-filtering per the Context note, make sure the fixture-based test reflects the actual filtered result, not the raw unfiltered count).

- [ ] **Step 3: Run tests to verify they fail**

Run: `pytest tests/test_retailers_rueducommerce.py -v`
Expected: FAIL with `ImportError: cannot import name 'search_ram_prices'`

- [ ] **Step 4: Refactor `retailers/rueducommerce.py`**

Replace the existing `search_prices` function (keep `_title_matches_model`/`_SUFFIX_QUALIFIERS` exactly as they are, unchanged):

```python
def search_prices(cpu_model, gpu_model):
    try:
        # Unlike LDLC/Materiel.net/Grosbill (strict AND-matching, choke on
        # combined CPU+GPU queries), Rue du Commerce's search handles a
        # combined query well: verified live that "Ryzen 7 5700X RTX 4060"
        # returned 48 listings in the "PC" category. Verified against the
        # real fixture: only 33/48 titles actually contain "5700X" (15 are
        # Ryzen 7 9700X or 7700X builds -- a different CPU generation, not a
        # near-miss), and only 22/48 contain exact "4060" (43/48 contain
        # "4060" as part of a family match, but the rest of those are 4060
        # Ti, which is a different, more expensive card). Both models are
        # kept together in the query since RdC's combined search still
        # returns useful results overall, similar to TopAchat/PcComponentes
        # -- but see the title-relevance filter below, which is what keeps
        # the wrong-generation/wrong-card noise out of the returned prices.
        query = f"{cpu_model} {gpu_model}"
        url = SEARCH_URL.format(query=requests.utils.quote(query))
        response = requests.get(url, headers=HEADERS, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        prices = []
        # No JSON API, no data-price attribute, no itemprop="price", and no
        # product-level JSON-LD block -- verified against the fixture (only
        # plain-text prices inside "div.price" containers). Each result is a
        # "li.pdt-item" card. A discounted product renders
        # <div class="price"><div class="old-price">...</div>
        # <div class="new-price">...</div></div> (old-price is the
        # struck-through original, new-price is the current price to use);
        # a non-discounted product just renders a plain nested
        # <div class="price"><div class="price">1&nbsp;299,00€</div></div>.
        # Both variants also carry a "sr-only" label span ("Nouveau prix :")
        # that must be stripped before reading the text, and the price text
        # itself uses a non-breaking space as the thousands separator and a
        # comma as the decimal separator (e.g. "1 639,90€").
        for card in soup.select("li.pdt-item"):
            # Skip cards whose title doesn't actually reference both the
            # requested CPU and GPU -- the combined query returns plenty of
            # wrong-generation CPUs and wrong-tier GPUs (see comment above),
            # and including their prices measurably skews the result (the
            # wrong-CPU-generation subset has a median ~45% higher than the
            # correctly matched subset). Titles live in "h3.title-3".
            title_el = card.select_one("h3.title-3")
            title = title_el.get_text(strip=True) if title_el else ""
            if not (
                _title_matches_model(title, cpu_model)
                and _title_matches_model(title, gpu_model)
            ):
                continue
            price_container = card.select_one("div.price")
            if price_container is None:
                continue
            target = (
                price_container.select_one("div.new-price")
                or price_container.select_one("div.price")
                or price_container
            )
            for sr_only in target.select(".sr-only"):
                sr_only.decompose()
            raw_price = target.get_text(strip=True)
            raw_price = (
                raw_price.replace("\xa0", "")
                .replace(" ", "")
                .replace("€", "")
                .replace(",", ".")
                .strip()
            )
            try:
                price = float(raw_price)
            except ValueError:
                continue
            prices.append(price)
        return prices
    except Exception:
        return []
```

With this (extracts `_fetch_soup`/`_extract_card_price`, keeps title-filtering inside `search_prices` only):

```python
def _fetch_soup(query):
    url = SEARCH_URL.format(query=requests.utils.quote(query))
    response = requests.get(url, headers=HEADERS, timeout=10)
    response.raise_for_status()
    return BeautifulSoup(response.text, "html.parser")


def _extract_card_price(card):
    price_container = card.select_one("div.price")
    if price_container is None:
        return None
    target = (
        price_container.select_one("div.new-price")
        or price_container.select_one("div.price")
        or price_container
    )
    for sr_only in target.select(".sr-only"):
        sr_only.decompose()
    raw_price = target.get_text(strip=True)
    raw_price = (
        raw_price.replace("\xa0", "")
        .replace(" ", "")
        .replace("€", "")
        .replace(",", ".")
        .strip()
    )
    try:
        return float(raw_price)
    except ValueError:
        return None


def search_prices(cpu_model, gpu_model):
    try:
        # Unlike LDLC/Materiel.net/Grosbill (strict AND-matching, choke on
        # combined CPU+GPU queries), Rue du Commerce's search handles a
        # combined query well (verified live). Both models are kept in the
        # query; see the title-relevance filter below, which is what keeps
        # wrong-generation/wrong-card noise out of the returned prices.
        query = f"{cpu_model} {gpu_model}"
        soup = _fetch_soup(query)

        prices = []
        for card in soup.select("li.pdt-item"):
            title_el = card.select_one("h3.title-3")
            title = title_el.get_text(strip=True) if title_el else ""
            if not (
                _title_matches_model(title, cpu_model)
                and _title_matches_model(title, gpu_model)
            ):
                continue
            price = _extract_card_price(card)
            if price is not None:
                prices.append(price)
        return prices
    except Exception:
        return []


def search_ram_prices(ram_go, ram_type):
    try:
        # ADJUST based on your live research in Step 1. If results are noisy,
        # add a title-relevance filter here the same way search_prices does,
        # reusing _title_matches_model against e.g. f"{ram_go}Go" and
        # ram_type as the two terms to check for.
        query = f"{ram_go}Go {ram_type}"
        soup = _fetch_soup(query)

        prices = []
        for card in soup.select("li.pdt-item"):
            price = _extract_card_price(card)
            if price is not None:
                prices.append(price)
        return prices
    except Exception:
        return []


def search_storage_prices(storage_go, storage_type):
    try:
        # ADJUST based on your live research in Step 1. If results are noisy,
        # add a title-relevance filter here the same way search_prices does.
        query = f"{storage_go}Go {storage_type}"
        soup = _fetch_soup(query)

        prices = []
        for card in soup.select("li.pdt-item"):
            price = _extract_card_price(card)
            if price is not None:
                prices.append(price)
        return prices
    except Exception:
        return []
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest tests/test_retailers_rueducommerce.py -v`
Expected: all tests pass, including all pre-existing `search_prices` tests unmodified

- [ ] **Step 6: Run the full suite**

Run: `pytest -v`
Expected: no new failures beyond the already-expected ones

- [ ] **Step 7: Commit**

```bash
git add retailers/rueducommerce.py tests/test_retailers_rueducommerce.py tests/fixtures/rueducommerce_ram_search.html tests/fixtures/rueducommerce_storage_search.html
git commit -m "feat: add Rue du Commerce RAM/storage price search"
```

---

### Task 10: `retailers/amazon.py` — refactor + RAM/storage search

**Files:**
- Modify: `retailers/amazon.py`
- Create: `tests/fixtures/amazon_ram_search.html`
- Create: `tests/fixtures/amazon_storage_search.html`
- Test: `tests/test_retailers_amazon.py`

## Context

Same refactor pattern as Task 9, applied to Amazon (which has the same `_title_matches_model` relevance-filter pattern, but is expected to be blocked by anti-bot protection most of the time — that's still the accepted outcome here, unchanged from the original design).

- [ ] **Step 1: Research the live site for RAM and storage queries**

Same process as Task 4 Step 1, targeting `https://www.amazon.fr/s`. As with the original PC-search research, if you get blocked/CAPTCHA'd, save whatever you actually received as the fixture (an honest "this site blocked us" fixture is a valid, expected outcome) rather than forcing a workaround. Save to `tests/fixtures/amazon_ram_search.html` and `tests/fixtures/amazon_storage_search.html`.

- [ ] **Step 2: Write the failing tests**

```python
# append to tests/test_retailers_amazon.py
from retailers.amazon import search_ram_prices, search_storage_prices


@patch("retailers.amazon.requests.get")
def test_search_ram_prices_handles_the_real_fixture_without_crashing(mock_get):
    with open("tests/fixtures/amazon_ram_search.html", encoding="utf-8") as f:
        html = f.read()

    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.text = html
    mock_get.return_value = mock_response

    prices = search_ram_prices(16, "ddr4")

    assert isinstance(prices, list)
    assert all(isinstance(p, float) for p in prices)
    # if Step 1 got real results, tighten to exact expected values;
    # if blocked/CAPTCHA'd, assert prices == [] instead -- either is valid


@patch("retailers.amazon.requests.get", side_effect=Exception("network error"))
def test_search_ram_prices_returns_empty_list_on_network_failure(mock_get):
    assert search_ram_prices(16, "ddr4") == []


@patch("retailers.amazon.requests.get")
def test_search_storage_prices_handles_the_real_fixture_without_crashing(mock_get):
    with open("tests/fixtures/amazon_storage_search.html", encoding="utf-8") as f:
        html = f.read()

    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.text = html
    mock_get.return_value = mock_response

    prices = search_storage_prices(512, "ssd")

    assert isinstance(prices, list)
    assert all(isinstance(p, float) for p in prices)


@patch("retailers.amazon.requests.get", side_effect=Exception("network error"))
def test_search_storage_prices_returns_empty_list_on_network_failure(mock_get):
    assert search_storage_prices(512, "ssd") == []
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `pytest tests/test_retailers_amazon.py -v`
Expected: FAIL with `ImportError: cannot import name 'search_ram_prices'`

- [ ] **Step 4: Refactor `retailers/amazon.py`**

Replace the existing `search_prices` function (keep `_title_matches_model`/`_SUFFIX_QUALIFIERS` and the module-level comment block exactly as they are, unchanged):

```python
def search_prices(cpu_model, gpu_model):
    try:
        # Kept both models in the query, same as PcComponentes/TopAchat/Rue
        # du Commerce -- Amazon's search doesn't reject the combined query
        # (unlike LDLC/Materiel.net/Grosbill's strict AND-matching, which
        # returns zero results for a combined CPU+GPU search). It just ranks
        # loosely, hence the title-relevance filter below.
        query = f"{cpu_model} {gpu_model}"
        response = requests.get(
            SEARCH_URL, params={"k": query}, headers=HEADERS, timeout=10
        )
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        prices = []
        for card in soup.select('div[data-component-type="s-search-result"]'):
            title_el = card.select_one("h2 span")
            title = title_el.get_text(strip=True) if title_el else ""
            if not (
                _title_matches_model(title, cpu_model)
                and _title_matches_model(title, gpu_model)
            ):
                continue
            price_el = card.select_one(".a-price .a-offscreen")
            if price_el is None:
                continue
            raw_price = (
                price_el.get_text(strip=True)
                .replace("\xa0", "")
                .replace(" ", "")
                .replace("€", "")
                .replace(",", ".")
                .strip()
            )
            try:
                price = float(raw_price)
            except ValueError:
                continue
            prices.append(price)
        return prices
    except Exception:
        return []
```

With this:

```python
def _fetch_soup(query):
    response = requests.get(
        SEARCH_URL, params={"k": query}, headers=HEADERS, timeout=10
    )
    response.raise_for_status()
    return BeautifulSoup(response.text, "html.parser")


def _extract_card_price(card):
    price_el = card.select_one(".a-price .a-offscreen")
    if price_el is None:
        return None
    raw_price = (
        price_el.get_text(strip=True)
        .replace("\xa0", "")
        .replace(" ", "")
        .replace("€", "")
        .replace(",", ".")
        .strip()
    )
    try:
        return float(raw_price)
    except ValueError:
        return None


def search_prices(cpu_model, gpu_model):
    try:
        # Kept both models in the query, same as PcComponentes/TopAchat/Rue
        # du Commerce. Amazon's search doesn't reject the combined query; it
        # just ranks loosely, hence the title-relevance filter below.
        query = f"{cpu_model} {gpu_model}"
        soup = _fetch_soup(query)

        prices = []
        for card in soup.select('div[data-component-type="s-search-result"]'):
            title_el = card.select_one("h2 span")
            title = title_el.get_text(strip=True) if title_el else ""
            if not (
                _title_matches_model(title, cpu_model)
                and _title_matches_model(title, gpu_model)
            ):
                continue
            price = _extract_card_price(card)
            if price is not None:
                prices.append(price)
        return prices
    except Exception:
        return []


def search_ram_prices(ram_go, ram_type):
    try:
        # ADJUST based on your live research in Step 1. If results are noisy,
        # add a title-relevance filter here the same way search_prices does.
        query = f"{ram_go}Go {ram_type}"
        soup = _fetch_soup(query)

        prices = []
        for card in soup.select('div[data-component-type="s-search-result"]'):
            price = _extract_card_price(card)
            if price is not None:
                prices.append(price)
        return prices
    except Exception:
        return []


def search_storage_prices(storage_go, storage_type):
    try:
        # ADJUST based on your live research in Step 1. If results are noisy,
        # add a title-relevance filter here the same way search_prices does.
        query = f"{storage_go}Go {storage_type}"
        soup = _fetch_soup(query)

        prices = []
        for card in soup.select('div[data-component-type="s-search-result"]'):
            price = _extract_card_price(card)
            if price is not None:
                prices.append(price)
        return prices
    except Exception:
        return []
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest tests/test_retailers_amazon.py -v`
Expected: all tests pass, including all pre-existing `search_prices` tests unmodified

- [ ] **Step 6: Run the full suite**

Run: `pytest -v`
Expected: no new failures beyond the already-expected ones

- [ ] **Step 7: Commit**

```bash
git add retailers/amazon.py tests/test_retailers_amazon.py tests/fixtures/amazon_ram_search.html tests/fixtures/amazon_storage_search.html
git commit -m "feat: add Amazon RAM/storage price search (best-effort, expected low yield)"
```

---

### Task 11: `retailers/__init__.py` — aggregate RAM/storage search functions

**Files:**
- Modify: `retailers/__init__.py`
- Test: `tests/test_retailers_init.py`

- [ ] **Step 1: Write the failing tests**

```python
# append to tests/test_retailers_init.py
from retailers import ALL_RAM_SEARCH_FUNCTIONS, ALL_STORAGE_SEARCH_FUNCTIONS


def test_all_ram_search_functions_lists_seven_callables():
    assert len(ALL_RAM_SEARCH_FUNCTIONS) == 7
    assert all(callable(fn) for fn in ALL_RAM_SEARCH_FUNCTIONS)


def test_all_storage_search_functions_lists_seven_callables():
    assert len(ALL_STORAGE_SEARCH_FUNCTIONS) == 7
    assert all(callable(fn) for fn in ALL_STORAGE_SEARCH_FUNCTIONS)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_retailers_init.py -v`
Expected: FAIL with `ImportError: cannot import name 'ALL_RAM_SEARCH_FUNCTIONS' from 'retailers'`

- [ ] **Step 3: Update `retailers/__init__.py`**

Replace the whole file:

```python
from retailers.ldlc import search_prices as ldlc_search
from retailers.ldlc import search_ram_prices as ldlc_ram_search
from retailers.ldlc import search_storage_prices as ldlc_storage_search
from retailers.pccomponentes import search_prices as pccomponentes_search
from retailers.pccomponentes import search_ram_prices as pccomponentes_ram_search
from retailers.pccomponentes import search_storage_prices as pccomponentes_storage_search
from retailers.materiel_net import search_prices as materiel_net_search
from retailers.materiel_net import search_ram_prices as materiel_net_ram_search
from retailers.materiel_net import search_storage_prices as materiel_net_storage_search
from retailers.topachat import search_prices as topachat_search
from retailers.topachat import search_ram_prices as topachat_ram_search
from retailers.topachat import search_storage_prices as topachat_storage_search
from retailers.grosbill import search_prices as grosbill_search
from retailers.grosbill import search_ram_prices as grosbill_ram_search
from retailers.grosbill import search_storage_prices as grosbill_storage_search
from retailers.rueducommerce import search_prices as rueducommerce_search
from retailers.rueducommerce import search_ram_prices as rueducommerce_ram_search
from retailers.rueducommerce import search_storage_prices as rueducommerce_storage_search
from retailers.amazon import search_prices as amazon_search
from retailers.amazon import search_ram_prices as amazon_ram_search
from retailers.amazon import search_storage_prices as amazon_storage_search

ALL_SEARCH_FUNCTIONS = [
    ldlc_search,
    pccomponentes_search,
    materiel_net_search,
    topachat_search,
    grosbill_search,
    rueducommerce_search,
    amazon_search,
]

ALL_RAM_SEARCH_FUNCTIONS = [
    ldlc_ram_search,
    pccomponentes_ram_search,
    materiel_net_ram_search,
    topachat_ram_search,
    grosbill_ram_search,
    rueducommerce_ram_search,
    amazon_ram_search,
]

ALL_STORAGE_SEARCH_FUNCTIONS = [
    ldlc_storage_search,
    pccomponentes_storage_search,
    materiel_net_storage_search,
    topachat_storage_search,
    grosbill_storage_search,
    rueducommerce_storage_search,
    amazon_storage_search,
]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_retailers_init.py -v`
Expected: all tests pass, including the pre-existing `test_all_search_functions_lists_seven_callables`

- [ ] **Step 5: Run the full suite**

Run: `pytest -v`
Expected: no new failures beyond the already-expected ones (cli.py/app.py still pending)

- [ ] **Step 6: Commit**

```bash
git add retailers/__init__.py tests/test_retailers_init.py
git commit -m "feat: aggregate RAM/storage search functions across all 7 retailers"
```

---

### Task 12: `sourcing.py` — RAM/storage search function builders

**Files:**
- Modify: `sourcing.py`
- Test: `tests/test_sourcing.py`

- [ ] **Step 1: Write the failing tests**

```python
# append to tests/test_sourcing.py
from sourcing import make_ram_search_fn, make_storage_search_fn


def test_make_ram_search_fn_returns_eight_functions():
    fns = make_ram_search_fn("myid", "mysecret")
    assert len(fns) == 8
    assert all(callable(fn) for fn in fns)


@patch("sourcing.ebay_client.search_ram_prices")
def test_ram_first_function_wraps_ebay_with_credentials(mock_search):
    mock_search.return_value = [280.0]

    fns = make_ram_search_fn("myid", "mysecret")
    result = fns[0](16, "ddr4")

    assert result == [280.0]
    mock_search.assert_called_once_with(16, "ddr4", "myid", "mysecret")


def test_make_storage_search_fn_returns_eight_functions():
    fns = make_storage_search_fn("myid", "mysecret")
    assert len(fns) == 8
    assert all(callable(fn) for fn in fns)


@patch("sourcing.ebay_client.search_storage_prices")
def test_storage_first_function_wraps_ebay_with_credentials(mock_search):
    mock_search.return_value = [45.0]

    fns = make_storage_search_fn("myid", "mysecret")
    result = fns[0](512, "ssd")

    assert result == [45.0]
    mock_search.assert_called_once_with(512, "ssd", "myid", "mysecret")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_sourcing.py -v`
Expected: FAIL with `ImportError: cannot import name 'make_ram_search_fn'`

- [ ] **Step 3: Update `sourcing.py`**

Replace the whole file:

```python
import ebay_client
import retailers


def make_new_pc_search_fn(client_id, client_secret):
    def ebay_new_search(cpu_model, gpu_model):
        return ebay_client.search_new_pc_prices(cpu_model, gpu_model, client_id, client_secret)

    return [ebay_new_search] + retailers.ALL_SEARCH_FUNCTIONS


def make_ram_search_fn(client_id, client_secret):
    def ebay_ram_search(ram_go, ram_type):
        return ebay_client.search_ram_prices(ram_go, ram_type, client_id, client_secret)

    return [ebay_ram_search] + retailers.ALL_RAM_SEARCH_FUNCTIONS


def make_storage_search_fn(client_id, client_secret):
    def ebay_storage_search(storage_go, storage_type):
        return ebay_client.search_storage_prices(storage_go, storage_type, client_id, client_secret)

    return [ebay_storage_search] + retailers.ALL_STORAGE_SEARCH_FUNCTIONS
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_sourcing.py -v`
Expected: all tests pass, including the pre-existing `make_new_pc_search_fn` tests

- [ ] **Step 5: Run the full suite**

Run: `pytest -v`
Expected: no new failures beyond the already-expected ones (cli.py/app.py still pending)

- [ ] **Step 6: Commit**

```bash
git add sourcing.py tests/test_sourcing.py
git commit -m "feat: wire eBay + retailers into RAM/storage search function builders"
```

---

### Task 13: `cli.py` — wire RAM/storage search into `main()`

**Files:**
- Modify: `cli.py`
- Test: `tests/test_cli.py`

## Context

`cli.py`'s `main()` currently calls `estimator.estimate_pc(...)` without `ram_search_fns`/`storage_search_fns` — after Task 2, this now raises `TypeError`. This task fixes that by building the two new search-function lists via `sourcing.make_ram_search_fn`/`make_storage_search_fn` and passing them through.

- [ ] **Step 1: Update `main()` in `cli.py`**

Find this exact block:

```python
    reference_prices = load_json(DATA_DIR / "reference_prices.json")
    component_rates = load_json(DATA_DIR / "component_rates.json")
    buy_tiers = load_json(DATA_DIR / "buy_tiers.json")
    resale_config = load_json(DATA_DIR / "resale_target.json")
    ebay_search_fn = make_ebay_search_fn(client_id, client_secret)
    new_pc_search_fns = sourcing.make_new_pc_search_fn(client_id, client_secret)
```

Replace it with:

```python
    reference_prices = load_json(DATA_DIR / "reference_prices.json")
    component_rates = load_json(DATA_DIR / "component_rates.json")
    buy_tiers = load_json(DATA_DIR / "buy_tiers.json")
    resale_config = load_json(DATA_DIR / "resale_target.json")
    ebay_search_fn = make_ebay_search_fn(client_id, client_secret)
    new_pc_search_fns = sourcing.make_new_pc_search_fn(client_id, client_secret)
    ram_search_fns = sourcing.make_ram_search_fn(client_id, client_secret)
    storage_search_fns = sourcing.make_storage_search_fn(client_id, client_secret)
```

Then find this exact block:

```python
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
```

Replace it with:

```python
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
        ram_search_fns=ram_search_fns,
        storage_search_fns=storage_search_fns,
    )
```

- [ ] **Step 2: Run the full test suite**

Run: `pytest -v`
Expected: all previously-failing `test_cli.py` tests (from Task 2 Step 5's expected failure) now pass. Confirm 0 failures across the entire suite except possibly still `tests/test_app.py` (fixed in Task 14).

- [ ] **Step 3: Commit**

```bash
git add cli.py
git commit -m "feat: wire RAM/storage market search into the CLI"
```

---

### Task 14: `app.py` — wire RAM/storage search into the web form

**Files:**
- Modify: `app.py`
- Test: `tests/test_app.py`

## Context

Same fix as Task 13, applied to `app.py`'s `index()` route.

- [ ] **Step 1: Update `index()` in `app.py`**

Find this exact block:

```python
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
```

Replace it with:

```python
            reference_prices = cli_helpers.load_json(DATA_DIR / "reference_prices.json")
            component_rates = cli_helpers.load_json(DATA_DIR / "component_rates.json")
            buy_tiers = cli_helpers.load_json(DATA_DIR / "buy_tiers.json")
            resale_config = cli_helpers.load_json(DATA_DIR / "resale_target.json")

            used_search_fn = cli_helpers.make_ebay_search_fn(client_id, client_secret)
            new_pc_search_fns = sourcing.make_new_pc_search_fn(client_id, client_secret)
            ram_search_fns = sourcing.make_ram_search_fn(client_id, client_secret)
            storage_search_fns = sourcing.make_storage_search_fn(client_id, client_secret)

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
                ram_search_fns=ram_search_fns,
                storage_search_fns=storage_search_fns,
            )
```

- [ ] **Step 2: Run the full test suite**

Run: `pytest -v`
Expected: 0 failures across the entire suite

- [ ] **Step 3: Commit**

```bash
git add app.py
git commit -m "feat: wire RAM/storage market search into the web app"
```

---

### Task 15: Manual end-to-end smoke test (CLI + web)

**Files:** none (manual verification only)

- [ ] **Step 1: Run the full automated test suite**

Run: `pytest -v`
Expected: 0 failures

- [ ] **Step 2: Run the CLI end-to-end**

Run: `python cli.py`
Input: CPU `Ryzen 7 5700X`, RAM `32`, RAM type `ddr5`, Storage `512`, Storage type `nvme`, GPU `RTX 4060`
Expected: no crash. The RAM line in the component breakdown should show either `médiane sur N annonces neuves` (if any of the 8 sources found real DDR5 32Go prices) or `formule €/Go` (if none did) — both are valid outcomes; the point is confirming the new code path runs without exception either way, and that a market-based RAM price (if found) looks like a plausible real price (roughly in the hundreds of euros for 32Go DDR5, not the old formula's ~96€).

- [ ] **Step 3: Run the web app end-to-end**

Run: `python app.py`, then submit the same config via curl:
```bash
curl -s -X POST http://127.0.0.1:5000/ -d "cpu_model=Ryzen 7 5700X&ram_go=32&ram_type=ddr5&storage_go=512&storage_type=nvme&gpu_model=RTX 4060"
```
Expected: HTTP 200, no server error, response contains `Total estimé`.

- [ ] **Step 4: Stop the server**

Make sure no `python app.py` process is left running.

- [ ] **Step 5: Commit any fixes discovered**

```bash
git add -A
git commit -m "fix: address issues found during manual RAM/storage pricing verification"
```

(Skip this commit if no fixes were needed.)
