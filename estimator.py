import statistics
from decimal import ROUND_HALF_UP, Decimal


def median_price(prices):
    return statistics.median(prices)


def _estimate_by_rate(size_go, component_type, rates, category):
    rate = rates.get(category, {}).get(component_type.lower())
    if rate is None:
        return None
    return {"value": round(size_go * rate, 2), "method": "formule €/Go"}


def estimate_ram(size_go, ram_type, rates):
    return _estimate_by_rate(size_go, ram_type, rates, "ram")


def estimate_storage(size_go, storage_type, rates):
    return _estimate_by_rate(size_go, storage_type, rates, "storage")


def normalize_model(name):
    return " ".join(name.lower().split())


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


def _round2(value):
    # Plain round() on a binary float can land just below a .xx5 boundary
    # (e.g. 999.0 * 0.415 == 414.58499999999997...) and round the wrong way.
    # Route through Decimal(str(...)) so we round the same value a human
    # would read, using standard half-up rounding.
    return float(Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def estimate_buy_grid(new_pc_price, tiers):
    grid = []
    for index, tier in enumerate(tiers):
        grid.append({
            "max_price": _round2(new_pc_price * tier["max_pct"]),
            "emoji": tier["emoji"],
            "label": tier["label"],
            "is_last": index == len(tiers) - 1,
        })
    return grid


def estimate_resale_target(new_pc_price, resale_config):
    return {
        "min": _round2(new_pc_price * resale_config["min_pct"]),
        "max": _round2(new_pc_price * resale_config["max_pct"]),
    }
