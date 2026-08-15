# CPU/GPU — prix neuf en priorité — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix the CPU/GPU price estimate (`détail par composant`) so it tries a market **new-price** search across the 7 revendeurs first, falling back to the existing eBay occasion search, then the local reference table — instead of relying solely on 1-2 noisy eBay occasion listings, which produced a component-breakdown total higher than the whole new PC's estimated price.

**Architecture:** Mirrors the RAM/stockage market-pricing architecture already in production. `estimator.py`'s shared `_aggregate_market_prices` helper is generalized to accept a variable number of trailing arguments (1 for CPU/GPU, 2 for RAM/stockage/PC neuf), then reused inside `estimate_component` for a new "market neuf" step ahead of the existing eBay occasion path. Each of the 7 `retailers/*.py` modules gains `search_cpu_prices(cpu_model)`/`search_gpu_prices(gpu_model)`, aggregated via `retailers/__init__.py` and exposed via `sourcing.py` — without eBay, which stays occasion-only per explicit design decision.

**Tech Stack:** Python, `requests` + `BeautifulSoup` (retailer scraping), `ThreadPoolExecutor` (concurrent multi-source aggregation), `pytest` + `unittest.mock`.

---

## Reference: current file state before this plan

```
estimator.py                    # _aggregate_market_prices(arg1, arg2, search_fns), estimate_component(model, category, ebay_search_fn, reference_table)
retailers/ldlc.py               # search_prices, search_ram_prices, search_storage_prices (via shared _search(query))
retailers/pccomponentes.py      # same shape as ldlc.py
retailers/materiel_net.py       # same shape as ldlc.py
retailers/topachat.py           # search_prices, search_ram_prices, search_storage_prices (via shared _search(query, category_label))
retailers/grosbill.py           # same shape as ldlc.py
retailers/rueducommerce.py      # search_prices, search_ram_prices, search_storage_prices (via shared _fetch_soup(query) + _extract_card_price(card), _title_matches_model available)
retailers/amazon.py             # same shape as rueducommerce.py
retailers/__init__.py           # ALL_SEARCH_FUNCTIONS, ALL_RAM_SEARCH_FUNCTIONS, ALL_STORAGE_SEARCH_FUNCTIONS
sourcing.py                     # make_new_pc_search_fn, make_ram_search_fn, make_storage_search_fn (all take client_id, client_secret)
cli.py / app.py                 # wire ram_search_fns/storage_search_fns into estimate_pc
```

## Files touched by this plan

```
estimator.py                    # MODIFIED: generalized aggregation + estimate_component + estimate_pc (Tasks 1-3)
retailers/ldlc.py               # MODIFIED: +search_cpu_prices, +search_gpu_prices (Task 4)
retailers/pccomponentes.py      # MODIFIED (Task 5)
retailers/materiel_net.py       # MODIFIED (Task 6)
retailers/topachat.py           # MODIFIED (Task 7)
retailers/grosbill.py           # MODIFIED (Task 8)
retailers/rueducommerce.py      # MODIFIED (Task 9)
retailers/amazon.py             # MODIFIED (Task 10)
retailers/__init__.py           # MODIFIED: +ALL_CPU_SEARCH_FUNCTIONS, +ALL_GPU_SEARCH_FUNCTIONS (Task 11)
sourcing.py                     # MODIFIED: +make_cpu_search_fn, +make_gpu_search_fn (no credentials) (Task 12)
cli.py                          # MODIFIED: wires new search functions into estimate_pc (Task 13)
app.py                          # MODIFIED: wires new search functions into estimate_pc (Task 14)
tests/                          # MODIFIED/NEW throughout
```

---

### Task 1: `estimator.py` — generalize `_aggregate_market_prices` to variable-arity args

**Files:**
- Modify: `estimator.py`

## Context

`_aggregate_market_prices(arg1, arg2, search_fns)` and `_run_search_fn_safely(search_fn, arg1, arg2)` currently hardcode exactly two positional arguments per `search_fn` (size+type for RAM/stockage, cpu_model+gpu_model for PC neuf). CPU/GPU search functions take only **one** argument (the model), so both helpers are generalized to `*args` before they're reused for CPU/GPU in Task 2. This is a pure refactor — no behavior change for any existing caller.

- [ ] **Step 1: Generalize both helpers**

Find this exact block in `estimator.py`:

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
```

Replace it with:

```python
def _run_search_fn_safely(search_fn, *args):
    # search_fns aren't supposed to raise (each source is expected to fail
    # silently and return []), but a single misbehaving source shouldn't be
    # able to take down the whole aggregation, so we defend here too. Shared
    # across every multi-source aggregation in this module (new-PC price,
    # RAM, storage, CPU, GPU) -- *args lets this work whether the search_fn
    # takes one positional arg (a component model) or two (size + type,
    # cpu_model + gpu_model).
    try:
        return search_fn(*args)
    except Exception:
        return []


def _aggregate_market_prices(search_fns, *args):
    # Shared by estimate_new_pc_price/estimate_ram/estimate_storage/
    # estimate_component: run every search_fn concurrently and merge
    # whatever prices they find. Every search_fn does blocking network I/O
    # (requests.get(..., timeout=10)), so calling them sequentially means
    # worst-case wall-clock time is the SUM of all their timeouts. Threads
    # give real concurrency here because Python releases the GIL during
    # blocking I/O, so worst-case wall-clock time instead becomes the
    # slowest single source. search_fns comes first (not last) so *args can
    # capture a variable number of trailing arguments cleanly.
    search_fns = list(search_fns)
    all_prices = []

    if search_fns:
        with ThreadPoolExecutor(max_workers=len(search_fns)) as executor:
            futures = [
                executor.submit(_run_search_fn_safely, search_fn, *args)
                for search_fn in search_fns
            ]
            for future in futures:
                all_prices.extend(future.result())

    return all_prices
```

- [ ] **Step 2: Update the 3 existing call sites to the new argument order**

Find in `estimate_ram`:

```python
def estimate_ram(size_go, ram_type, search_fns, rates):
    all_prices = _aggregate_market_prices(size_go, ram_type, search_fns)
```

Replace with:

```python
def estimate_ram(size_go, ram_type, search_fns, rates):
    all_prices = _aggregate_market_prices(search_fns, size_go, ram_type)
```

Find in `estimate_storage`:

```python
def estimate_storage(size_go, storage_type, search_fns, rates):
    all_prices = _aggregate_market_prices(size_go, storage_type, search_fns)
```

Replace with:

```python
def estimate_storage(size_go, storage_type, search_fns, rates):
    all_prices = _aggregate_market_prices(search_fns, size_go, storage_type)
```

Find in `estimate_new_pc_price`:

```python
def estimate_new_pc_price(cpu_model, gpu_model, search_fns):
    all_prices = _aggregate_market_prices(cpu_model, gpu_model, search_fns)
```

Replace with:

```python
def estimate_new_pc_price(cpu_model, gpu_model, search_fns):
    all_prices = _aggregate_market_prices(search_fns, cpu_model, gpu_model)
```

- [ ] **Step 3: Run the full test suite to confirm this pure refactor breaks nothing**

Run: `pytest -v`
Expected: identical to the pre-existing baseline (154 passed, 0 failed) — this step changes zero observable behavior, only internal argument order.

- [ ] **Step 4: Commit**

```bash
git add estimator.py
git commit -m "refactor: generalize _aggregate_market_prices to variable-arity args"
```

---

### Task 2: `estimator.py` — `estimate_component` tries market neuf before eBay occasion

**Files:**
- Modify: `estimator.py`
- Test: `tests/test_estimator.py`

## Context

`estimate_component(model, category, ebay_search_fn, reference_table)` currently searches eBay occasion first, then the reference table. This task adds a `new_price_search_fns` parameter and makes it the **first** thing tried, using `_aggregate_market_prices` (generalized in Task 1). eBay occasion and the reference table remain exactly as they are today, now demoted to steps 2 and 3.

- [ ] **Step 1: Update the 4 existing tests and add 4 new ones**

Find this exact block in `tests/test_estimator.py`:

```python
def test_estimate_component_uses_ebay_median_when_available():
    def fake_ebay_search(model, category):
        return [50.0, 55.0, 60.0]

    result = estimate_component("i5-10400", "cpu", fake_ebay_search, REFERENCE)
    assert result == {"value": 55.0, "method": "médiane sur 3 annonces eBay"}


def test_estimate_component_falls_back_to_reference_table_when_ebay_empty():
    def fake_ebay_search(model, category):
        return []

    result = estimate_component("i5-10400", "cpu", fake_ebay_search, REFERENCE)
    assert result == {"value": 55, "method": "table de référence"}


def test_estimate_component_reference_lookup_is_normalized():
    def fake_ebay_search(model, category):
        return []

    result = estimate_component("  I5-10400  ", "cpu", fake_ebay_search, REFERENCE)
    assert result == {"value": 55, "method": "table de référence"}


def test_estimate_component_returns_none_when_unknown_everywhere():
    def fake_ebay_search(model, category):
        return []

    result = estimate_component("unknown-cpu-9999", "cpu", fake_ebay_search, REFERENCE)
    assert result is None
```

Replace it with:

```python
def test_estimate_component_uses_ebay_median_when_available():
    def fake_ebay_search(model, category):
        return [50.0, 55.0, 60.0]

    result = estimate_component("i5-10400", "cpu", fake_ebay_search, REFERENCE, [])
    assert result == {"value": 55.0, "method": "médiane sur 3 annonces eBay"}


def test_estimate_component_falls_back_to_reference_table_when_ebay_empty():
    def fake_ebay_search(model, category):
        return []

    result = estimate_component("i5-10400", "cpu", fake_ebay_search, REFERENCE, [])
    assert result == {"value": 55, "method": "table de référence"}


def test_estimate_component_reference_lookup_is_normalized():
    def fake_ebay_search(model, category):
        return []

    result = estimate_component("  I5-10400  ", "cpu", fake_ebay_search, REFERENCE, [])
    assert result == {"value": 55, "method": "table de référence"}


def test_estimate_component_returns_none_when_unknown_everywhere():
    def fake_ebay_search(model, category):
        return []

    result = estimate_component("unknown-cpu-9999", "cpu", fake_ebay_search, REFERENCE, [])
    assert result is None


def test_estimate_component_uses_new_price_median_when_sources_find_prices():
    def fake_ebay_search(model, category):
        return [1094.28]

    def new_price_source(model):
        return [450.0, 480.0]

    result = estimate_component(
        "i5-10400", "cpu", fake_ebay_search, REFERENCE, [new_price_source]
    )
    assert result == {"value": 465.0, "method": "médiane sur 2 annonces neuves"}


def test_estimate_component_new_price_takes_priority_over_ebay():
    def fake_ebay_search(model, category):
        raise AssertionError("eBay must not be called when a new price is found")

    def new_price_source(model):
        return [480.0]

    result = estimate_component(
        "i5-10400", "cpu", fake_ebay_search, REFERENCE, [new_price_source]
    )
    assert result == {"value": 480.0, "method": "médiane sur 1 annonces neuves"}


def test_estimate_component_falls_back_to_ebay_when_no_new_price_found():
    def fake_ebay_search(model, category):
        return [55.0]

    def empty_new_price_source(model):
        return []

    result = estimate_component(
        "i5-10400", "cpu", fake_ebay_search, REFERENCE, [empty_new_price_source]
    )
    assert result == {"value": 55.0, "method": "médiane sur 1 annonces eBay"}


def test_estimate_component_falls_back_to_reference_table_when_new_price_and_ebay_both_empty():
    def fake_ebay_search(model, category):
        return []

    def empty_new_price_source(model):
        return []

    result = estimate_component(
        "i5-10400", "cpu", fake_ebay_search, REFERENCE, [empty_new_price_source]
    )
    assert result == {"value": 55, "method": "table de référence"}
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_estimator.py -v -k estimate_component`
Expected: FAIL — `TypeError: estimate_component() missing 1 required positional argument: 'new_price_search_fns'`

- [ ] **Step 3: Implement**

Find this exact block in `estimator.py`:

```python
def estimate_component(model, category, ebay_search_fn, reference_table):
    prices = ebay_search_fn(model, category)
    if prices:
        value = median_price(prices)
        return {"value": value, "method": f"médiane sur {len(prices)} annonces eBay"}

    normalized_input = normalize_model(model)
    for known_model, value in reference_table.get(category, {}).items():
        if normalize_model(known_model) == normalized_input:
            return {"value": value, "method": "table de référence"}

    return None
```

Replace it with:

```python
def estimate_component(model, category, ebay_search_fn, reference_table, new_price_search_fns):
    new_prices = _aggregate_market_prices(new_price_search_fns, model)
    if new_prices:
        return {
            "value": median_price(new_prices),
            "method": f"médiane sur {len(new_prices)} annonces neuves",
        }

    prices = ebay_search_fn(model, category)
    if prices:
        value = median_price(prices)
        return {"value": value, "method": f"médiane sur {len(prices)} annonces eBay"}

    normalized_input = normalize_model(model)
    for known_model, value in reference_table.get(category, {}).items():
        if normalize_model(known_model) == normalized_input:
            return {"value": value, "method": "table de référence"}

    return None
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_estimator.py -v -k estimate_component`
Expected: all pass (8 tests).

- [ ] **Step 5: Commit**

```bash
git add estimator.py tests/test_estimator.py
git commit -m "feat: try market new-price search before eBay for CPU/GPU pricing"
```

---

### Task 3: `estimator.py` — wire `estimate_pc` with `cpu_search_fns`/`gpu_search_fns`

**Files:**
- Modify: `estimator.py`
- Test: `tests/test_estimator.py`

## Context

`estimate_pc` currently calls `estimate_component` for CPU/GPU without a `new_price_search_fns` argument — after Task 2 this now raises `TypeError`. This task adds `cpu_search_fns`/`gpu_search_fns` keyword-only params to `estimate_pc` and threads them through, mirroring `ram_search_fns`/`storage_search_fns`.

- [ ] **Step 1: Update the 4 existing `estimate_pc` tests**

Find this exact block in `tests/test_estimator.py`:

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

Replace it with (each call gains `cpu_search_fns=[], gpu_search_fns=[]`):

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
        cpu_search_fns=[],
        gpu_search_fns=[],
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
        cpu_search_fns=[],
        gpu_search_fns=[],
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
        cpu_search_fns=[],
        gpu_search_fns=[],
    )

    assert result["missing"] == ["cpu", "gpu"]
    assert result["breakdown"]["cpu"] is None
    assert result["total"] == 32.0 + 25.6


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
        cpu_search_fns=[],
        gpu_search_fns=[],
    )

    assert result["breakdown"]["ram"] == {
        "value": 290.0,
        "method": "médiane sur 2 annonces neuves",
    }
    assert result["breakdown"]["storage"] == {
        "value": 47.5,
        "method": "médiane sur 2 annonces neuves",
    }


def test_estimate_pc_uses_new_price_for_cpu_and_gpu_when_available():
    def fake_ebay_search(model, category):
        return [1094.28]

    def cpu_source(model):
        return [450.0, 480.0]

    def gpu_source(model):
        return [900.0]

    rates = {"ram": {"ddr5": 9.5}, "storage": {"nvme": 0.07}}
    result = estimate_pc(
        cpu_model="ryzen 7 9800x3d",
        ram_go=32,
        ram_type="ddr5",
        storage_go=1000,
        storage_type="nvme",
        gpu_model="rtx 5070 ti",
        ebay_search_fn=fake_ebay_search,
        reference_prices={},
        component_rates=rates,
        ram_search_fns=[],
        storage_search_fns=[],
        cpu_search_fns=[cpu_source],
        gpu_search_fns=[gpu_source],
    )

    assert result["breakdown"]["cpu"] == {
        "value": 465.0,
        "method": "médiane sur 2 annonces neuves",
    }
    assert result["breakdown"]["gpu"] == {
        "value": 900.0,
        "method": "médiane sur 1 annonces neuves",
    }
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_estimator.py -v -k estimate_pc`
Expected: FAIL — `TypeError: estimate_pc() missing 2 required keyword-only arguments: 'cpu_search_fns' and 'gpu_search_fns'`

- [ ] **Step 3: Implement**

Find this exact block in `estimator.py`:

```python
def estimate_pc(
    *,
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

Replace it with:

```python
def estimate_pc(
    *,
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
    cpu_search_fns,
    gpu_search_fns,
):
    breakdown = {}
    missing = []

    breakdown["cpu"] = estimate_component(
        cpu_model, "cpu", ebay_search_fn, reference_prices, cpu_search_fns
    )
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
        breakdown["gpu"] = estimate_component(
            gpu_model, "gpu", ebay_search_fn, reference_prices, gpu_search_fns
        )
        if breakdown["gpu"] is None:
            missing.append("gpu")
    else:
        breakdown["gpu"] = None

    total = sum(r["value"] for r in breakdown.values() if r is not None)

    return {"breakdown": breakdown, "total": round(total, 2), "missing": missing}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest -v`
Expected: all `test_estimator.py` tests pass. `tests/test_app.py` (3 tests) and `tests/test_cli.py` will now fail with `TypeError: estimate_pc() missing 2 required keyword-only arguments: 'cpu_search_fns' and 'gpu_search_fns'` — this is the same expected/benign fallout pattern seen in the RAM/stockage project (fixed by Tasks 13-14 later in this plan).

- [ ] **Step 5: Commit**

```bash
git add estimator.py tests/test_estimator.py
git commit -m "feat: wire cpu_search_fns/gpu_search_fns into estimate_pc"
```

---

### Task 4: `retailers/ldlc.py` — add `search_cpu_prices`/`search_gpu_prices`

**Files:**
- Modify: `retailers/ldlc.py`
- Create: `tests/fixtures/ldlc_cpu_search.html`
- Create: `tests/fixtures/ldlc_gpu_search.html`
- Test: `tests/test_retailers_ldlc.py`

## Context

`retailers/ldlc.py` already has a shared `_search(query)` helper (used by `search_prices`/`search_ram_prices`/`search_storage_prices`) — no refactor needed this time, just two new functions that call it with a new query. `search_prices` currently searches `"PC gamer {gpu_model}"` (LDLC's search does strict AND-matching, so combined CPU+GPU queries return almost nothing). A standalone CPU or GPU search is a different, simpler product category.

**The queries below are starting guesses, not proven.** Validate live against `https://www.ldlc.com/recherche/{query}/` the same way every prior query in this file was validated — try `f"Processeur {cpu_model}"` for CPU and `f"Carte graphique {gpu_model}"` for GPU first (RAM/stockage both needed a category-anchor word — `"RAM"`, `"Disque"` — to avoid whole-machine pollution, so CPU/GPU likely need one too, but confirm rather than assume). If a literal guess doesn't work well, adjust it and update the code comment to explain what you tried and why, following the documentation style already used in this file.

- [ ] **Step 1: Research the live site for CPU and GPU queries**

Search LDLC for a CPU (try `"Processeur Ryzen 7 9800X3D"` first, adjust based on what you find) and separately for a GPU (try `"Carte graphique RTX 5070 Ti"` first, adjust based on what you find). For each, confirm the results are genuinely standalone CPU/GPU listings with real prices (not laptops, not prebuilt PCs, not accessories), record the query that worked, and save the raw HTML to `tests/fixtures/ldlc_cpu_search.html` and `tests/fixtures/ldlc_gpu_search.html` respectively.

- [ ] **Step 2: Write the failing tests**

```python
# append to tests/test_retailers_ldlc.py
from retailers.ldlc import search_cpu_prices, search_gpu_prices


@patch("retailers.ldlc.requests.get")
def test_search_cpu_prices_extracts_prices_from_real_fixture(mock_get):
    with open("tests/fixtures/ldlc_cpu_search.html", encoding="utf-8") as f:
        html = f.read()

    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.text = html
    mock_get.return_value = mock_response

    prices = search_cpu_prices("Ryzen 7 9800X3D")

    assert isinstance(prices, list)
    assert all(isinstance(p, float) for p in prices)
    # tighten to the exact expected price list once you've inspected the fixture


@patch("retailers.ldlc.requests.get", side_effect=Exception("network error"))
def test_search_cpu_prices_returns_empty_list_on_network_failure(mock_get):
    assert search_cpu_prices("Ryzen 7 9800X3D") == []


@patch("retailers.ldlc.requests.get")
def test_search_gpu_prices_extracts_prices_from_real_fixture(mock_get):
    with open("tests/fixtures/ldlc_gpu_search.html", encoding="utf-8") as f:
        html = f.read()

    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.text = html
    mock_get.return_value = mock_response

    prices = search_gpu_prices("RTX 5070 Ti")

    assert isinstance(prices, list)
    assert all(isinstance(p, float) for p in prices)
    # tighten to the exact expected price list once you've inspected the fixture


@patch("retailers.ldlc.requests.get", side_effect=Exception("network error"))
def test_search_gpu_prices_returns_empty_list_on_network_failure(mock_get):
    assert search_gpu_prices("RTX 5070 Ti") == []
```

Tighten both fixture-based tests' assertions to the exact expected price list once you've inspected your captured fixtures — don't leave a weak `len(prices) >= 0` check in the final version.

Also add query-construction regression tests asserting the exact query string sent to `requests.get`, specific enough to catch a future regression (mirror the existing `test_search_prices_query_excludes_cpu_model`-style test already in this file).

- [ ] **Step 3: Run tests to verify they fail**

Run: `pytest tests/test_retailers_ldlc.py -v`
Expected: FAIL with `ImportError: cannot import name 'search_cpu_prices'`

- [ ] **Step 4: Implement**

Append to `retailers/ldlc.py` (adjust the query strings to whatever your Step 1 research actually found, and write a comment in the same documentation style as the existing `search_ram_prices`/`search_storage_prices` functions in this file — cite what you tried, what noise you found, and why you picked your final query):

```python
def search_cpu_prices(cpu_model):
    # <replace with your live-research findings, following the documentation
    # style of search_ram_prices/search_storage_prices above>
    return _search(f"Processeur {cpu_model}")


def search_gpu_prices(gpu_model):
    # <replace with your live-research findings>
    return _search(f"Carte graphique {gpu_model}")
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest tests/test_retailers_ldlc.py -v`
Expected: all pass.

- [ ] **Step 6: Run the full suite**

Run: `pytest -v`
Expected: no new failures beyond the already-expected ones (`test_app.py`/`test_cli.py`, pending Tasks 13-14).

- [ ] **Step 7: Commit**

```bash
git add retailers/ldlc.py tests/test_retailers_ldlc.py tests/fixtures/ldlc_cpu_search.html tests/fixtures/ldlc_gpu_search.html
git commit -m "feat: add LDLC CPU/GPU price search"
```

---

### Task 5: `retailers/pccomponentes.py` — add `search_cpu_prices`/`search_gpu_prices`

**Files:**
- Modify: `retailers/pccomponentes.py`
- Create: `tests/fixtures/pccomponentes_cpu_search.html`
- Create: `tests/fixtures/pccomponentes_gpu_search.html`
- Test: `tests/test_retailers_pccomponentes.py`

## Context

Same pattern as Task 4, applied to PcComponentes. This site's search is Algolia-backed and has so far tolerated bare, unanchored queries well (`search_ram_prices`/`search_storage_prices` both use `f"{size}Go {type}"` with no anchor word needed, unlike LDLC). A CPU/GPU model search will likely work as a bare model name too, but validate live rather than assuming — try `f"{cpu_model}"` and `f"{gpu_model}"` first against `https://www.pccomponentes.fr/search?query={query}`.

- [ ] **Step 1: Research the live site for CPU and GPU queries**

Search PcComponentes for `"Ryzen 7 9800X3D"` and separately `"RTX 5070 Ti"`. Confirm genuine standalone CPU/GPU listings, record the query that worked, save fixtures to `tests/fixtures/pccomponentes_cpu_search.html` and `tests/fixtures/pccomponentes_gpu_search.html`.

- [ ] **Step 2: Write the failing tests**

```python
# append to tests/test_retailers_pccomponentes.py
from retailers.pccomponentes import search_cpu_prices, search_gpu_prices


@patch("retailers.pccomponentes.requests.get")
def test_search_cpu_prices_extracts_prices_from_real_fixture(mock_get):
    with open("tests/fixtures/pccomponentes_cpu_search.html", encoding="utf-8") as f:
        html = f.read()

    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.text = html
    mock_get.return_value = mock_response

    prices = search_cpu_prices("Ryzen 7 9800X3D")

    assert isinstance(prices, list)
    assert all(isinstance(p, float) for p in prices)


@patch("retailers.pccomponentes.requests.get", side_effect=Exception("network error"))
def test_search_cpu_prices_returns_empty_list_on_network_failure(mock_get):
    assert search_cpu_prices("Ryzen 7 9800X3D") == []


@patch("retailers.pccomponentes.requests.get")
def test_search_gpu_prices_extracts_prices_from_real_fixture(mock_get):
    with open("tests/fixtures/pccomponentes_gpu_search.html", encoding="utf-8") as f:
        html = f.read()

    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.text = html
    mock_get.return_value = mock_response

    prices = search_gpu_prices("RTX 5070 Ti")

    assert isinstance(prices, list)
    assert all(isinstance(p, float) for p in prices)


@patch("retailers.pccomponentes.requests.get", side_effect=Exception("network error"))
def test_search_gpu_prices_returns_empty_list_on_network_failure(mock_get):
    assert search_gpu_prices("RTX 5070 Ti") == []
```

Tighten both fixture-based tests to exact expected price lists once inspected. Add query-construction regression tests asserting the exact query string.

- [ ] **Step 3: Run tests to verify they fail**

Run: `pytest tests/test_retailers_pccomponentes.py -v`
Expected: FAIL with `ImportError: cannot import name 'search_cpu_prices'`

- [ ] **Step 4: Implement**

Append to `retailers/pccomponentes.py`, adjusting queries/comments to your research findings:

```python
def search_cpu_prices(cpu_model):
    # <replace with your live-research findings>
    return _search(f"{cpu_model}")


def search_gpu_prices(gpu_model):
    # <replace with your live-research findings>
    return _search(f"{gpu_model}")
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest tests/test_retailers_pccomponentes.py -v`
Expected: all pass.

- [ ] **Step 6: Run the full suite**

Run: `pytest -v`
Expected: no new failures beyond the already-expected ones.

- [ ] **Step 7: Commit**

```bash
git add retailers/pccomponentes.py tests/test_retailers_pccomponentes.py tests/fixtures/pccomponentes_cpu_search.html tests/fixtures/pccomponentes_gpu_search.html
git commit -m "feat: add PcComponentes CPU/GPU price search"
```

---

### Task 6: `retailers/materiel_net.py` — add `search_cpu_prices`/`search_gpu_prices`

**Files:**
- Modify: `retailers/materiel_net.py`
- Create: `tests/fixtures/materiel_net_cpu_search.html`
- Create: `tests/fixtures/materiel_net_gpu_search.html`
- Test: `tests/test_retailers_materiel_net.py`

## Context

Same pattern as Task 4, applied to Materiel.net (same LDLC-Group platform, but has repeatedly needed different query wording than LDLC despite the shared platform — RAM needed a space before "Go" that LDLC didn't, storage needed the "Go" suffix dropped entirely where LDLC kept it). **Do not copy LDLC's Task 4 queries blindly** — validate live against `https://www.materiel.net/recherche/{query}/` independently, even though `"Processeur {cpu_model}"`/`"Carte graphique {gpu_model}"` are reasonable starting guesses given the shared platform.

- [ ] **Step 1: Research the live site for CPU and GPU queries**

Search Materiel.net for a CPU and a GPU query, confirm genuine standalone listings, save fixtures to `tests/fixtures/materiel_net_cpu_search.html` and `tests/fixtures/materiel_net_gpu_search.html`.

- [ ] **Step 2: Write the failing tests**

```python
# append to tests/test_retailers_materiel_net.py
from retailers.materiel_net import search_cpu_prices, search_gpu_prices


@patch("retailers.materiel_net.requests.get")
def test_search_cpu_prices_extracts_prices_from_real_fixture(mock_get):
    with open("tests/fixtures/materiel_net_cpu_search.html", encoding="utf-8") as f:
        html = f.read()

    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.text = html
    mock_get.return_value = mock_response

    prices = search_cpu_prices("Ryzen 7 9800X3D")

    assert isinstance(prices, list)
    assert all(isinstance(p, float) for p in prices)


@patch("retailers.materiel_net.requests.get", side_effect=Exception("network error"))
def test_search_cpu_prices_returns_empty_list_on_network_failure(mock_get):
    assert search_cpu_prices("Ryzen 7 9800X3D") == []


@patch("retailers.materiel_net.requests.get")
def test_search_gpu_prices_extracts_prices_from_real_fixture(mock_get):
    with open("tests/fixtures/materiel_net_gpu_search.html", encoding="utf-8") as f:
        html = f.read()

    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.text = html
    mock_get.return_value = mock_response

    prices = search_gpu_prices("RTX 5070 Ti")

    assert isinstance(prices, list)
    assert all(isinstance(p, float) for p in prices)


@patch("retailers.materiel_net.requests.get", side_effect=Exception("network error"))
def test_search_gpu_prices_returns_empty_list_on_network_failure(mock_get):
    assert search_gpu_prices("RTX 5070 Ti") == []
```

Tighten to exact expected price lists once inspected. Add query-construction regression tests.

- [ ] **Step 3: Run tests to verify they fail**

Run: `pytest tests/test_retailers_materiel_net.py -v`
Expected: FAIL with `ImportError: cannot import name 'search_cpu_prices'`

- [ ] **Step 4: Implement**

Append to `retailers/materiel_net.py`, adjusting queries/comments to your research findings:

```python
def search_cpu_prices(cpu_model):
    # <replace with your live-research findings>
    return _search(f"Processeur {cpu_model}")


def search_gpu_prices(gpu_model):
    # <replace with your live-research findings>
    return _search(f"Carte graphique {gpu_model}")
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest tests/test_retailers_materiel_net.py -v`
Expected: all pass.

- [ ] **Step 6: Run the full suite**

Run: `pytest -v`
Expected: no new failures beyond the already-expected ones.

- [ ] **Step 7: Commit**

```bash
git add retailers/materiel_net.py tests/test_retailers_materiel_net.py tests/fixtures/materiel_net_cpu_search.html tests/fixtures/materiel_net_gpu_search.html
git commit -m "feat: add Materiel.net CPU/GPU price search"
```

---

### Task 7: `retailers/topachat.py` — add `search_cpu_prices`/`search_gpu_prices`

**Files:**
- Modify: `retailers/topachat.py`
- Create: `tests/fixtures/topachat_cpu_search.html`
- Create: `tests/fixtures/topachat_gpu_search.html`
- Test: `tests/test_retailers_topachat.py`

## Context

TopAchat's shared `_search(query, category_label)` helper filters the JSON API response to a specific category label. **The RAM/stockage project already found that guessed category labels are usually wrong** — the plan's guesses for those were "Mémoire" and "Disque dur / SSD", but the real labels turned out to be "DDR4"/"DDR5" and "SSD". For CPU/GPU, `"Processeur"` and `"Carte Graphique"` are starting guesses only — you must inspect a real API response's `result.document.categories` list to find the actual `label_category` value(s), exactly as done for RAM/stockage. Don't guess and ship — read the real JSON.

- [ ] **Step 1: Research the live API for CPU and GPU category labels**

Query `https://www.topachat.com/api/search/search.main.php` with `params={"terms": "Ryzen 7 9800X3D"}` and inspect the JSON response's `result.document.categories` list for the `label_category` value(s) that correspond to genuine standalone CPU listings (not motherboard bundles, not prebuilt PCs). Do the same for `"RTX 5070 Ti"`. Save each raw JSON response to `tests/fixtures/topachat_cpu_search.html` and `tests/fixtures/topachat_gpu_search.html` (`.html` extension for consistency with the existing convention in this file, even though the content is JSON).

- [ ] **Step 2: Write the failing tests**

```python
# append to tests/test_retailers_topachat.py
import json

from retailers.topachat import search_cpu_prices, search_gpu_prices


@patch("retailers.topachat.requests.get")
def test_search_cpu_prices_extracts_prices_from_real_fixture(mock_get):
    with open("tests/fixtures/topachat_cpu_search.html", encoding="utf-8") as f:
        fixture_json = json.load(f)

    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = fixture_json
    mock_get.return_value = mock_response

    prices = search_cpu_prices("Ryzen 7 9800X3D")

    assert isinstance(prices, list)
    assert all(isinstance(p, float) for p in prices)


@patch("retailers.topachat.requests.get", side_effect=Exception("network error"))
def test_search_cpu_prices_returns_empty_list_on_network_failure(mock_get):
    assert search_cpu_prices("Ryzen 7 9800X3D") == []


@patch("retailers.topachat.requests.get")
def test_search_gpu_prices_extracts_prices_from_real_fixture(mock_get):
    with open("tests/fixtures/topachat_gpu_search.html", encoding="utf-8") as f:
        fixture_json = json.load(f)

    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = fixture_json
    mock_get.return_value = mock_response

    prices = search_gpu_prices("RTX 5070 Ti")

    assert isinstance(prices, list)
    assert all(isinstance(p, float) for p in prices)


@patch("retailers.topachat.requests.get", side_effect=Exception("network error"))
def test_search_gpu_prices_returns_empty_list_on_network_failure(mock_get):
    assert search_gpu_prices("RTX 5070 Ti") == []
```

Tighten both to exact expected price lists once fixtures are captured. Add query-construction + category-label regression tests (mirror `test_search_ram_prices_query_and_category_label` already in this file).

- [ ] **Step 3: Run tests to verify they fail**

Run: `pytest tests/test_retailers_topachat.py -v`
Expected: FAIL with `ImportError: cannot import name 'search_cpu_prices'`

- [ ] **Step 4: Implement**

Append to `retailers/topachat.py`, using whatever real category label(s) your Step 1 research found:

```python
def search_cpu_prices(cpu_model):
    # <replace with your live-research findings about the real category label>
    return _search(cpu_model, "<real category label found in Step 1>")


def search_gpu_prices(gpu_model):
    # <replace with your live-research findings about the real category label>
    return _search(gpu_model, "<real category label found in Step 1>")
```

Note: unlike `search_ram_prices`/`search_storage_prices` (whose category label tracks the size/type value itself), CPU/GPU category labels are almost certainly a **fixed string** (e.g. `"Processeur"`), not derived from the model — write whatever your research actually shows.

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest tests/test_retailers_topachat.py -v`
Expected: all pass.

- [ ] **Step 6: Run the full suite**

Run: `pytest -v`
Expected: no new failures beyond the already-expected ones.

- [ ] **Step 7: Commit**

```bash
git add retailers/topachat.py tests/test_retailers_topachat.py tests/fixtures/topachat_cpu_search.html tests/fixtures/topachat_gpu_search.html
git commit -m "feat: add TopAchat CPU/GPU price search"
```

---

### Task 8: `retailers/grosbill.py` — add `search_cpu_prices`/`search_gpu_prices`

**Files:**
- Modify: `retailers/grosbill.py`
- Create: `tests/fixtures/grosbill_cpu_search.html`
- Create: `tests/fixtures/grosbill_gpu_search.html`
- Test: `tests/test_retailers_grosbill.py`

## Context

Same pattern as Task 4, applied to Grosbill. `search_prices` uses `"PC gamer {cpu_model}"` (strict AND-matching, catalog pairs this CPU with newer GPUs so the GPU term is dropped). RAM/stockage both needed a category anchor (`"RAM"`, `"Disque"`) to avoid whole-machine pollution. Validate live against `https://www.grosbill.com/produit.aspx` whether CPU/GPU need a similar anchor, or whether a bare model name is already precise enough (a specific CPU/GPU model name is a much narrower query than `"{size}Go {type}"`, so it may not need one — check, don't assume).

- [ ] **Step 1: Research the live site for CPU and GPU queries**

Search Grosbill for a CPU and a GPU query, confirm genuine standalone listings (not bundled PCs unless that's unavoidable and acceptably rare — same ~5-10% noise tolerance already established for this project), save fixtures to `tests/fixtures/grosbill_cpu_search.html` and `tests/fixtures/grosbill_gpu_search.html`.

- [ ] **Step 2: Write the failing tests**

```python
# append to tests/test_retailers_grosbill.py
from retailers.grosbill import search_cpu_prices, search_gpu_prices


@patch("retailers.grosbill.requests.get")
def test_search_cpu_prices_extracts_prices_from_real_fixture(mock_get):
    with open("tests/fixtures/grosbill_cpu_search.html", encoding="utf-8") as f:
        html = f.read()

    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.text = html
    mock_get.return_value = mock_response

    prices = search_cpu_prices("Ryzen 7 9800X3D")

    assert isinstance(prices, list)
    assert all(isinstance(p, float) for p in prices)


@patch("retailers.grosbill.requests.get", side_effect=Exception("network error"))
def test_search_cpu_prices_returns_empty_list_on_network_failure(mock_get):
    assert search_cpu_prices("Ryzen 7 9800X3D") == []


@patch("retailers.grosbill.requests.get")
def test_search_gpu_prices_extracts_prices_from_real_fixture(mock_get):
    with open("tests/fixtures/grosbill_gpu_search.html", encoding="utf-8") as f:
        html = f.read()

    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.text = html
    mock_get.return_value = mock_response

    prices = search_gpu_prices("RTX 5070 Ti")

    assert isinstance(prices, list)
    assert all(isinstance(p, float) for p in prices)


@patch("retailers.grosbill.requests.get", side_effect=Exception("network error"))
def test_search_gpu_prices_returns_empty_list_on_network_failure(mock_get):
    assert search_gpu_prices("RTX 5070 Ti") == []
```

Tighten to exact expected price lists once inspected. Add query-construction regression tests.

- [ ] **Step 3: Run tests to verify they fail**

Run: `pytest tests/test_retailers_grosbill.py -v`
Expected: FAIL with `ImportError: cannot import name 'search_cpu_prices'`

- [ ] **Step 4: Implement**

Append to `retailers/grosbill.py`, adjusting queries/comments to your research findings:

```python
def search_cpu_prices(cpu_model):
    # <replace with your live-research findings>
    return _search(f"{cpu_model}")


def search_gpu_prices(gpu_model):
    # <replace with your live-research findings>
    return _search(f"{gpu_model}")
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest tests/test_retailers_grosbill.py -v`
Expected: all pass.

- [ ] **Step 6: Run the full suite**

Run: `pytest -v`
Expected: no new failures beyond the already-expected ones.

- [ ] **Step 7: Commit**

```bash
git add retailers/grosbill.py tests/test_retailers_grosbill.py tests/fixtures/grosbill_cpu_search.html tests/fixtures/grosbill_gpu_search.html
git commit -m "feat: add Grosbill CPU/GPU price search"
```

---

### Task 9: `retailers/rueducommerce.py` — add `search_cpu_prices`/`search_gpu_prices`

**Files:**
- Modify: `retailers/rueducommerce.py`
- Create: `tests/fixtures/rueducommerce_cpu_search.html`
- Create: `tests/fixtures/rueducommerce_gpu_search.html`
- Test: `tests/test_retailers_rueducommerce.py`

## Context

This module already has `_fetch_soup(query)`, `_extract_card_price(card)`, and a working `_title_matches_model(title, model)` relevance filter (used by `search_prices` for its combined CPU+GPU query, which has genuine ~30-55% noise). `search_ram_prices`/`search_storage_prices` deliberately do **not** use that filter — live research found 0% noise on their chosen queries.

For CPU/GPU standalone searches, **check first, don't assume either way** whether `_title_matches_model` is needed: a single specific model name is a narrower, more precise query than the combined CPU+GPU search, so it may turn out clean like RAM/stockage — or it may still pick up near-miss variants (e.g. a search for `"RTX 5070 Ti"` matching `"RTX 5070 Ti Super"` if that exists, or last-gen accessories). If your live research shows noise at or above the ~30% threshold already used elsewhere in this project, reuse `_title_matches_model(title, model)` exactly as `search_prices` does; if noise is low (~5-10% or less), leave it unfiltered per the RAM/stockage precedent.

- [ ] **Step 1: Research the live site for CPU and GPU queries**

Search `https://www.rueducommerce.fr/recherche/{query}/` for a CPU and a GPU query. Sample enough result titles to judge noise level. Save fixtures to `tests/fixtures/rueducommerce_cpu_search.html` and `tests/fixtures/rueducommerce_gpu_search.html`.

- [ ] **Step 2: Write the failing tests**

```python
# append to tests/test_retailers_rueducommerce.py
from retailers.rueducommerce import search_cpu_prices, search_gpu_prices


@patch("retailers.rueducommerce.requests.get")
def test_search_cpu_prices_extracts_prices_from_real_fixture(mock_get):
    with open("tests/fixtures/rueducommerce_cpu_search.html", encoding="utf-8") as f:
        html = f.read()

    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.text = html
    mock_get.return_value = mock_response

    prices = search_cpu_prices("Ryzen 7 9800X3D")

    assert isinstance(prices, list)
    assert all(isinstance(p, float) for p in prices)


@patch("retailers.rueducommerce.requests.get", side_effect=Exception("network error"))
def test_search_cpu_prices_returns_empty_list_on_network_failure(mock_get):
    assert search_cpu_prices("Ryzen 7 9800X3D") == []


@patch("retailers.rueducommerce.requests.get")
def test_search_gpu_prices_extracts_prices_from_real_fixture(mock_get):
    with open("tests/fixtures/rueducommerce_gpu_search.html", encoding="utf-8") as f:
        html = f.read()

    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.text = html
    mock_get.return_value = mock_response

    prices = search_gpu_prices("RTX 5070 Ti")

    assert isinstance(prices, list)
    assert all(isinstance(p, float) for p in prices)


@patch("retailers.rueducommerce.requests.get", side_effect=Exception("network error"))
def test_search_gpu_prices_returns_empty_list_on_network_failure(mock_get):
    assert search_gpu_prices("RTX 5070 Ti") == []
```

Tighten to exact expected price lists once inspected. Add query-construction regression tests asserting the exact URL.

- [ ] **Step 3: Run tests to verify they fail**

Run: `pytest tests/test_retailers_rueducommerce.py -v`
Expected: FAIL with `ImportError: cannot import name 'search_cpu_prices'`

- [ ] **Step 4: Implement**

Append to `retailers/rueducommerce.py` (shape depends on your Step 1 noise finding — this shows the unfiltered shape; add the `_title_matches_model` filter loop, matching `search_prices`'s pattern, only if your research shows it's needed):

```python
def search_cpu_prices(cpu_model):
    try:
        # <replace with your live-research findings>
        soup = _fetch_soup(f"{cpu_model}")
        prices = []
        for card in soup.select("li.pdt-item"):
            price = _extract_card_price(card)
            if price is not None:
                prices.append(price)
        return prices
    except Exception:
        return []


def search_gpu_prices(gpu_model):
    try:
        # <replace with your live-research findings>
        soup = _fetch_soup(f"{gpu_model}")
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
Expected: all pass.

- [ ] **Step 6: Run the full suite**

Run: `pytest -v`
Expected: no new failures beyond the already-expected ones.

- [ ] **Step 7: Commit**

```bash
git add retailers/rueducommerce.py tests/test_retailers_rueducommerce.py tests/fixtures/rueducommerce_cpu_search.html tests/fixtures/rueducommerce_gpu_search.html
git commit -m "feat: add Rue du Commerce CPU/GPU price search"
```

---

### Task 10: `retailers/amazon.py` — add `search_cpu_prices`/`search_gpu_prices`

**Files:**
- Modify: `retailers/amazon.py`
- Create: `tests/fixtures/amazon_cpu_search.html`
- Create: `tests/fixtures/amazon_gpu_search.html`
- Test: `tests/test_retailers_amazon.py`

## Context

Same refactor pattern as Task 9, applied to Amazon (which has the same `_title_matches_model` machinery, and is expected to be blocked by anti-bot protection most of the time — the RAM/stockage project already hit both an AWS WAF challenge and an Akamai "bm-verify" interstitial depending on the query, and treated a genuinely-blocked response as a valid, accepted outcome, not a bug to route around).

- [ ] **Step 1: Research the live site for CPU and GPU queries**

Attempt real HTTP GETs to `https://www.amazon.fr/s` for a CPU query and a GPU query. If blocked (as is the expected default), save the actual blocked-response HTML as the fixture — do not fabricate a fake success fixture, do not add CAPTCHA-solving or bot-evasion logic. If you unexpectedly get real results through, sample titles to judge noise level the same way as Task 9. Save fixtures to `tests/fixtures/amazon_cpu_search.html` and `tests/fixtures/amazon_gpu_search.html`.

- [ ] **Step 2: Write the failing tests**

```python
# append to tests/test_retailers_amazon.py
from retailers.amazon import search_cpu_prices, search_gpu_prices


@patch("retailers.amazon.requests.get")
def test_search_cpu_prices_handles_the_real_fixture_without_crashing(mock_get):
    with open("tests/fixtures/amazon_cpu_search.html", encoding="utf-8") as f:
        html = f.read()

    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.text = html
    mock_get.return_value = mock_response

    prices = search_cpu_prices("Ryzen 7 9800X3D")

    assert isinstance(prices, list)
    assert all(isinstance(p, float) for p in prices)
    # if Step 1 got real results, tighten to exact expected values;
    # if blocked, assert prices == []


@patch("retailers.amazon.requests.get", side_effect=Exception("network error"))
def test_search_cpu_prices_returns_empty_list_on_network_failure(mock_get):
    assert search_cpu_prices("Ryzen 7 9800X3D") == []


@patch("retailers.amazon.requests.get")
def test_search_gpu_prices_handles_the_real_fixture_without_crashing(mock_get):
    with open("tests/fixtures/amazon_gpu_search.html", encoding="utf-8") as f:
        html = f.read()

    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.text = html
    mock_get.return_value = mock_response

    prices = search_gpu_prices("RTX 5070 Ti")

    assert isinstance(prices, list)
    assert all(isinstance(p, float) for p in prices)


@patch("retailers.amazon.requests.get", side_effect=Exception("network error"))
def test_search_gpu_prices_returns_empty_list_on_network_failure(mock_get):
    assert search_gpu_prices("RTX 5070 Ti") == []
```

Add query-construction regression tests asserting the exact `params={"k": ...}` dict.

- [ ] **Step 3: Run tests to verify they fail**

Run: `pytest tests/test_retailers_amazon.py -v`
Expected: FAIL with `ImportError: cannot import name 'search_cpu_prices'`

- [ ] **Step 4: Implement**

Append to `retailers/amazon.py` (shape depends on whether you got real data or were blocked — this shows the unfiltered/blocked-safe shape; add `_title_matches_model` filtering only if live research shows real, noisy results):

```python
def search_cpu_prices(cpu_model):
    try:
        # <replace with your live-research findings>
        soup = _fetch_soup(f"{cpu_model}")
        prices = []
        for card in soup.select('div[data-component-type="s-search-result"]'):
            price = _extract_card_price(card)
            if price is not None:
                prices.append(price)
        return prices
    except Exception:
        return []


def search_gpu_prices(gpu_model):
    try:
        # <replace with your live-research findings>
        soup = _fetch_soup(f"{gpu_model}")
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
Expected: all pass.

- [ ] **Step 6: Run the full suite**

Run: `pytest -v`
Expected: no new failures beyond the already-expected ones.

- [ ] **Step 7: Commit**

```bash
git add retailers/amazon.py tests/test_retailers_amazon.py tests/fixtures/amazon_cpu_search.html tests/fixtures/amazon_gpu_search.html
git commit -m "feat: add Amazon CPU/GPU price search"
```

---

### Task 11: `retailers/__init__.py` — aggregate CPU/GPU search functions

**Files:**
- Modify: `retailers/__init__.py`
- Test: `tests/test_retailers_init.py`

- [ ] **Step 1: Write the failing tests**

```python
# append to tests/test_retailers_init.py
from retailers import ALL_CPU_SEARCH_FUNCTIONS, ALL_GPU_SEARCH_FUNCTIONS


def test_all_cpu_search_functions_lists_seven_callables():
    assert len(ALL_CPU_SEARCH_FUNCTIONS) == 7
    assert all(callable(fn) for fn in ALL_CPU_SEARCH_FUNCTIONS)


def test_all_gpu_search_functions_lists_seven_callables():
    assert len(ALL_GPU_SEARCH_FUNCTIONS) == 7
    assert all(callable(fn) for fn in ALL_GPU_SEARCH_FUNCTIONS)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_retailers_init.py -v`
Expected: FAIL with `ImportError: cannot import name 'ALL_CPU_SEARCH_FUNCTIONS' from 'retailers'`

- [ ] **Step 3: Update `retailers/__init__.py`**

Replace the whole file:

```python
from retailers.ldlc import search_prices as ldlc_search
from retailers.ldlc import search_ram_prices as ldlc_ram_search
from retailers.ldlc import search_storage_prices as ldlc_storage_search
from retailers.ldlc import search_cpu_prices as ldlc_cpu_search
from retailers.ldlc import search_gpu_prices as ldlc_gpu_search
from retailers.pccomponentes import search_prices as pccomponentes_search
from retailers.pccomponentes import search_ram_prices as pccomponentes_ram_search
from retailers.pccomponentes import search_storage_prices as pccomponentes_storage_search
from retailers.pccomponentes import search_cpu_prices as pccomponentes_cpu_search
from retailers.pccomponentes import search_gpu_prices as pccomponentes_gpu_search
from retailers.materiel_net import search_prices as materiel_net_search
from retailers.materiel_net import search_ram_prices as materiel_net_ram_search
from retailers.materiel_net import search_storage_prices as materiel_net_storage_search
from retailers.materiel_net import search_cpu_prices as materiel_net_cpu_search
from retailers.materiel_net import search_gpu_prices as materiel_net_gpu_search
from retailers.topachat import search_prices as topachat_search
from retailers.topachat import search_ram_prices as topachat_ram_search
from retailers.topachat import search_storage_prices as topachat_storage_search
from retailers.topachat import search_cpu_prices as topachat_cpu_search
from retailers.topachat import search_gpu_prices as topachat_gpu_search
from retailers.grosbill import search_prices as grosbill_search
from retailers.grosbill import search_ram_prices as grosbill_ram_search
from retailers.grosbill import search_storage_prices as grosbill_storage_search
from retailers.grosbill import search_cpu_prices as grosbill_cpu_search
from retailers.grosbill import search_gpu_prices as grosbill_gpu_search
from retailers.rueducommerce import search_prices as rueducommerce_search
from retailers.rueducommerce import search_ram_prices as rueducommerce_ram_search
from retailers.rueducommerce import search_storage_prices as rueducommerce_storage_search
from retailers.rueducommerce import search_cpu_prices as rueducommerce_cpu_search
from retailers.rueducommerce import search_gpu_prices as rueducommerce_gpu_search
from retailers.amazon import search_prices as amazon_search
from retailers.amazon import search_ram_prices as amazon_ram_search
from retailers.amazon import search_storage_prices as amazon_storage_search
from retailers.amazon import search_cpu_prices as amazon_cpu_search
from retailers.amazon import search_gpu_prices as amazon_gpu_search

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

ALL_CPU_SEARCH_FUNCTIONS = [
    ldlc_cpu_search,
    pccomponentes_cpu_search,
    materiel_net_cpu_search,
    topachat_cpu_search,
    grosbill_cpu_search,
    rueducommerce_cpu_search,
    amazon_cpu_search,
]

ALL_GPU_SEARCH_FUNCTIONS = [
    ldlc_gpu_search,
    pccomponentes_gpu_search,
    materiel_net_gpu_search,
    topachat_gpu_search,
    grosbill_gpu_search,
    rueducommerce_gpu_search,
    amazon_gpu_search,
]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_retailers_init.py -v`
Expected: all pass, including the pre-existing tests.

- [ ] **Step 5: Run the full suite**

Run: `pytest -v`
Expected: no new failures beyond the already-expected ones (`test_app.py`/`test_cli.py`, pending Tasks 13-14).

- [ ] **Step 6: Commit**

```bash
git add retailers/__init__.py tests/test_retailers_init.py
git commit -m "feat: aggregate CPU/GPU search functions across all 7 retailers"
```

---

### Task 12: `sourcing.py` — CPU/GPU search function builders (no eBay)

**Files:**
- Modify: `sourcing.py`
- Test: `tests/test_sourcing.py`

## Context

Unlike `make_ram_search_fn`/`make_storage_search_fn`, these two builders take **no credentials** — eBay stays occasion-only for CPU/GPU per the approved design, so there's no eBay function to prepend, just the 7 retailer functions passed through directly.

- [ ] **Step 1: Write the failing tests**

```python
# append to tests/test_sourcing.py
from sourcing import make_cpu_search_fn, make_gpu_search_fn


def test_make_cpu_search_fn_returns_seven_functions():
    fns = make_cpu_search_fn()
    assert len(fns) == 7
    assert all(callable(fn) for fn in fns)


def test_make_gpu_search_fn_returns_seven_functions():
    fns = make_gpu_search_fn()
    assert len(fns) == 7
    assert all(callable(fn) for fn in fns)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_sourcing.py -v`
Expected: FAIL with `ImportError: cannot import name 'make_cpu_search_fn'`

- [ ] **Step 3: Update `sourcing.py`**

Append to `sourcing.py`:

```python
def make_cpu_search_fn():
    return retailers.ALL_CPU_SEARCH_FUNCTIONS


def make_gpu_search_fn():
    return retailers.ALL_GPU_SEARCH_FUNCTIONS
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_sourcing.py -v`
Expected: all pass, including the pre-existing `make_new_pc_search_fn`/`make_ram_search_fn`/`make_storage_search_fn` tests.

- [ ] **Step 5: Run the full suite**

Run: `pytest -v`
Expected: no new failures beyond the already-expected ones.

- [ ] **Step 6: Commit**

```bash
git add sourcing.py tests/test_sourcing.py
git commit -m "feat: add CPU/GPU search function builders (retailers only, no eBay)"
```

---

### Task 13: `cli.py` — wire CPU/GPU market search into `main()`

**Files:**
- Modify: `cli.py`

## Context

`cli.py`'s `main()` currently calls `estimator.estimate_pc(...)` without `cpu_search_fns`/`gpu_search_fns` — after Task 3, this raises `TypeError`. This task fixes that by building the two new search-function lists via `sourcing.make_cpu_search_fn()`/`make_gpu_search_fn()` (no credentials needed) and passing them through.

- [ ] **Step 1: Update `main()` in `cli.py`**

Find this exact block:

```python
    ebay_search_fn = make_ebay_search_fn(client_id, client_secret)
    new_pc_search_fns = sourcing.make_new_pc_search_fn(client_id, client_secret)
    ram_search_fns = sourcing.make_ram_search_fn(client_id, client_secret)
    storage_search_fns = sourcing.make_storage_search_fn(client_id, client_secret)
```

Replace it with:

```python
    ebay_search_fn = make_ebay_search_fn(client_id, client_secret)
    new_pc_search_fns = sourcing.make_new_pc_search_fn(client_id, client_secret)
    ram_search_fns = sourcing.make_ram_search_fn(client_id, client_secret)
    storage_search_fns = sourcing.make_storage_search_fn(client_id, client_secret)
    cpu_search_fns = sourcing.make_cpu_search_fn()
    gpu_search_fns = sourcing.make_gpu_search_fn()
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
        ram_search_fns=ram_search_fns,
        storage_search_fns=storage_search_fns,
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
        cpu_search_fns=cpu_search_fns,
        gpu_search_fns=gpu_search_fns,
    )
```

- [ ] **Step 2: Run the full test suite**

Run: `pytest -v`
Expected: all previously-failing `test_cli.py` tests now pass. Confirm 0 failures across the entire suite except possibly still `tests/test_app.py` (fixed in Task 14).

- [ ] **Step 3: Commit**

```bash
git add cli.py
git commit -m "feat: wire CPU/GPU market search into the CLI"
```

---

### Task 14: `app.py` — wire CPU/GPU market search into the web form

**Files:**
- Modify: `app.py`

## Context

Same fix as Task 13, applied to `app.py`'s `index()` route.

- [ ] **Step 1: Update `index()` in `app.py`**

Find this exact block:

```python
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

Replace it with:

```python
            used_search_fn = cli_helpers.make_ebay_search_fn(client_id, client_secret)
            new_pc_search_fns = sourcing.make_new_pc_search_fn(client_id, client_secret)
            ram_search_fns = sourcing.make_ram_search_fn(client_id, client_secret)
            storage_search_fns = sourcing.make_storage_search_fn(client_id, client_secret)
            cpu_search_fns = sourcing.make_cpu_search_fn()
            gpu_search_fns = sourcing.make_gpu_search_fn()

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
                cpu_search_fns=cpu_search_fns,
                gpu_search_fns=gpu_search_fns,
            )
```

- [ ] **Step 2: Run the full test suite**

Run: `pytest -v`
Expected: 0 failures across the entire suite.

- [ ] **Step 3: Commit**

```bash
git add app.py
git commit -m "feat: wire CPU/GPU market search into the web app"
```

---

### Task 15: Manual end-to-end smoke test — confirm the original bug is fixed

**Files:** none (manual verification only)

- [ ] **Step 1: Run the full automated test suite**

Run: `pytest -v`
Expected: 0 failures

- [ ] **Step 2: Run the CLI end-to-end with the exact config that triggered the original bug report**

Run: `python cli.py`
Input: CPU `Ryzen 7 9800X3D`, RAM `32`, RAM type `ddr5`, Storage `1000`, Storage type `nvme`, GPU `RTX 5070 Ti`

Expected: no crash. The CPU and GPU lines in the component breakdown should show either `médiane sur N annonces neuves` (if any of the 7 retailers found a real new price — the expected common case for a current-generation part) or `médiane sur N annonces eBay`/`table de référence` (only if no retailer found anything). Confirm the "Total estimé" (component breakdown) no longer exceeds "Prix neuf équivalent estimé" (the whole-PC price) — that inconsistency was the original symptom (3602.76€ component total vs. 2199.95€ new-PC estimate) and should no longer occur once CPU/GPU pull from the same well-sampled retailer market as the rest of the build.

- [ ] **Step 3: Run the web app end-to-end with the same config**

Run: `python app.py`, then submit via curl:
```bash
curl -s -X POST http://127.0.0.1:5000/ -d "cpu_model=Ryzen 7 9800X3D&ram_go=32&ram_type=ddr5&storage_go=1000&storage_type=nvme&gpu_model=RTX 5070 Ti"
```
Expected: HTTP 200, no server error, response contains `Total estimé`, and the CPU/GPU lines show `annonces neuves` (or a documented graceful fallback) rather than a 1-2-sample eBay median.
