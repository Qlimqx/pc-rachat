import statistics


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
