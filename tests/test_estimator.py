from estimator import median_price, estimate_ram, estimate_storage


def test_median_price_odd_count():
    assert median_price([10.0, 30.0, 20.0]) == 20.0


def test_median_price_even_count():
    assert median_price([10.0, 20.0, 30.0, 40.0]) == 25.0


def test_median_price_single_value():
    assert median_price([42.0]) == 42.0


RATES = {
    "ram": {"ddr3": 1.0, "ddr4": 2.0, "ddr5": 3.0},
    "storage": {"hdd": 0.02, "ssd": 0.05, "nvme": 0.07},
}


def test_estimate_ram_known_type():
    result = estimate_ram(16, "ddr4", RATES)
    assert result == {"value": 32.0, "method": "formule €/Go"}


def test_estimate_ram_unknown_type_returns_none():
    assert estimate_ram(16, "ddr7", RATES) is None


def test_estimate_ram_type_is_case_insensitive():
    result = estimate_ram(8, "DDR4", RATES)
    assert result == {"value": 16.0, "method": "formule €/Go"}


def test_estimate_storage_known_type():
    result = estimate_storage(512, "ssd", RATES)
    assert result == {"value": 25.6, "method": "formule €/Go"}


def test_estimate_storage_unknown_type_returns_none():
    assert estimate_storage(512, "zip-disk", RATES) is None


from estimator import normalize_model


def test_normalize_model_lowercases_and_strips():
    assert normalize_model("  Intel Core i5-10400  ") == "intel core i5-10400"


def test_normalize_model_collapses_internal_whitespace():
    assert normalize_model("Ryzen   5    3600") == "ryzen 5 3600"


from estimator import estimate_component

REFERENCE = {
    "cpu": {"i5-10400": 55},
    "gpu": {"gtx 1660": 110},
}


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


from estimator import estimate_pc


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
    )

    assert result["missing"] == ["cpu", "gpu"]
    assert result["breakdown"]["cpu"] is None
    assert result["total"] == 32.0 + 25.6
