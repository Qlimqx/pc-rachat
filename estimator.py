import statistics
from concurrent.futures import ThreadPoolExecutor
from decimal import ROUND_HALF_UP, Decimal


def median_price(prices):
    return statistics.median(prices)


def _estimate_by_rate(size_go, component_type, rates, category):
    rate = rates.get(category, {}).get(component_type.lower())
    if rate is None:
        return None
    return {"value": round(size_go * rate, 2), "method": "formule €/Go"}


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


def estimate_ram(size_go, ram_type, search_fns, rates, used_search_fn):
    # search_fns are all new-condition sources (retailers + eBay new-condition
    # search) -- if none find a result, try a genuine eBay used-condition
    # search before falling back to the €/Go formula, so "no new listing
    # found" doesn't silently jump straight to the (much lower, used-market-
    # calibrated) formula while skipping actual used-market data that exists.
    all_prices = _aggregate_market_prices(search_fns, size_go, ram_type)
    if all_prices:
        return {
            "value": median_price(all_prices),
            "method": f"médiane sur {len(all_prices)} annonces neuves",
        }
    used_prices = used_search_fn(size_go, ram_type)
    if used_prices:
        return {
            "value": median_price(used_prices),
            "method": f"médiane sur {len(used_prices)} annonces eBay occasion",
        }
    return _estimate_by_rate(size_go, ram_type, rates, "ram")


def estimate_storage(size_go, storage_type, search_fns, rates, used_search_fn):
    all_prices = _aggregate_market_prices(search_fns, size_go, storage_type)
    if all_prices:
        return {
            "value": median_price(all_prices),
            "method": f"médiane sur {len(all_prices)} annonces neuves",
        }
    used_prices = used_search_fn(size_go, storage_type)
    if used_prices:
        return {
            "value": median_price(used_prices),
            "method": f"médiane sur {len(used_prices)} annonces eBay occasion",
        }
    return _estimate_by_rate(size_go, storage_type, rates, "storage")


def normalize_model(name):
    return " ".join(name.lower().split())


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
    ram_used_search_fn,
    storage_used_search_fn,
):
    # cpu/ram/storage/gpu each do their own independent multi-source network
    # search (see _aggregate_market_prices) -- running them one after another
    # made a single request's worst-case wall time the SUM of all 4 searches
    # (up to ~40s), which was slow enough to trip both gunicorn's and
    # Render's own proxy timeout. Running them concurrently here (nested
    # thread pools are fine -- Python releases the GIL during the blocking
    # I/O each one does) cuts worst-case wall time to the SLOWEST single
    # search instead, matching the pattern already used inside
    # _aggregate_market_prices for combining sources within one search.
    keys = ["cpu", "ram", "storage"]
    if gpu_model:
        keys.append("gpu")

    def compute(key):
        if key == "cpu":
            return estimate_component(cpu_model, "cpu", ebay_search_fn, reference_prices, cpu_search_fns)
        if key == "ram":
            return estimate_ram(ram_go, ram_type, ram_search_fns, component_rates, ram_used_search_fn)
        if key == "storage":
            return estimate_storage(
                storage_go, storage_type, storage_search_fns, component_rates, storage_used_search_fn
            )
        return estimate_component(gpu_model, "gpu", ebay_search_fn, reference_prices, gpu_search_fns)

    with ThreadPoolExecutor(max_workers=len(keys)) as executor:
        results = dict(zip(keys, executor.map(compute, keys)))

    breakdown = {key: results.get(key) for key in ["cpu", "ram", "storage", "gpu"]}
    missing = [key for key in keys if breakdown[key] is None]

    total = sum(r["value"] for r in breakdown.values() if r is not None)

    return {"breakdown": breakdown, "total": round(total, 2), "missing": missing}


def estimate_new_pc_price(cpu_model, gpu_model, search_fns):
    all_prices = _aggregate_market_prices(search_fns, cpu_model, gpu_model)

    if not all_prices:
        return None

    return {
        "value": median_price(all_prices),
        "method": f"médiane sur {len(all_prices)} annonces neuves",
    }


def estimate_similar_used_price(cpu_model, ram_go, ram_type, storage_go, storage_type, gpu_model, search_fn):
    # Purely informational reference (not used to adjust the sell/buy grids):
    # what similar full configs (same CPU/GPU/RAM/storage) actually sell for
    # used, as a sanity check alongside the component-sum floor and the
    # new-PC-based ceiling. Single-source (eBay) -- unlike the multi-source
    # searches above, no French retailer sells whole used PCs at retail.
    prices = search_fn(cpu_model, ram_go, ram_type, storage_go, storage_type, gpu_model)
    if not prices:
        return None
    return {
        "value": median_price(prices),
        "method": f"médiane sur {len(prices)} annonces d'occasion similaires",
    }


def _round2(value):
    # Plain round() on a binary float can land just below a .xx5 boundary
    # (e.g. 999.0 * 0.415 == 414.58499999999997...) and round the wrong way.
    # Route through Decimal(str(...)) so we round the same value a human
    # would read, using standard half-up rounding.
    return float(Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def estimate_sell_grid(new_pc_price, discount_percentages, floor):
    # Each entry is "neuf minus X%" (a discount off the new-PC price), not a
    # straight percentage of it -- e.g. pct=0.10 means 90% of new_pc_price.
    # Every tier is clamped to the range [floor, new_pc_price]:
    # - floor (estimate_pc's "total") is the cost of buying the same parts
    #   separately. Without this lower clamp, an aggressive discount tier can
    #   undercut that total (observed live: a Ryzen 7 5700X + RTX 4060
    #   build's neuf-30% tier came out to 1084.93€, BELOW its 1099.92€
    #   component total), recommending less for the whole PC than the parts
    #   alone are worth.
    # - new_pc_price is the upper clamp: a resale price must always stay
    #   cheaper than "neuf" by definition. Without this, a floor that
    #   exceeds new_pc_price (component prices and the new-PC-bundle search
    #   are two independent, occasionally conflicting data sources) pushed
    #   every tier up to the floor -- observed live as a "prix neuf" of
    #   700€ next to a "prix de revente" of 900€, backwards. When floor
    #   itself exceeds new_pc_price, every tier collapses to new_pc_price
    #   (the strictest constraint that still holds is "never more than
    #   neuf").
    return [
        {"pct": pct, "price": min(max(_round2(new_pc_price * (1 - pct)), floor), new_pc_price)}
        for pct in discount_percentages
    ]


def estimate_buy_grid(pv_price, tiers, min_margin_pct):
    # Each tier (except the last) is "PV minus X%" -- tier["max_pct"] is a
    # discount to subtract from pv_price, e.g. max_pct=0.50 means "pay at
    # most PV - 50%". Tiers must be listed biggest-discount-first (🔥, the
    # cheapest/best deal) down to smallest-discount-last, so the computed
    # prices come out ascending. The final tier ignores its own max_pct and
    # is instead pinned to pv_price * (1 - min_margin_pct) -- the point
    # where margin drops to the VAT-driven minimum (VAT owed on margin
    # under the used-goods VAT-on-margin scheme) -- so that reject
    # threshold has a single source of truth instead of being duplicated
    # in data/buy_tiers.json.
    ceiling = max(pv_price * (1 - min_margin_pct), 0)
    last_index = len(tiers) - 1
    grid = []
    for index, tier in enumerate(tiers):
        is_last = index == last_index
        max_price = ceiling if is_last else pv_price * (1 - tier["max_pct"])
        grid.append({
            "max_price": _round2(max_price),
            "emoji": tier["emoji"],
            "label": tier["label"],
            "is_last": is_last,
        })
    return grid
