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


NO_USED = lambda *args: []


def test_estimate_ram_known_type():
    result = estimate_ram(16, "ddr4", [], RATES, NO_USED)
    assert result == {"value": 32.0, "method": "formule €/Go"}


def test_estimate_ram_unknown_type_returns_none():
    assert estimate_ram(16, "ddr7", [], RATES, NO_USED) is None


def test_estimate_ram_type_is_case_insensitive():
    result = estimate_ram(8, "DDR4", [], RATES, NO_USED)
    assert result == {"value": 16.0, "method": "formule €/Go"}


def test_estimate_storage_known_type():
    result = estimate_storage(512, "ssd", [], RATES, NO_USED)
    assert result == {"value": 25.6, "method": "formule €/Go"}


def test_estimate_storage_unknown_type_returns_none():
    assert estimate_storage(512, "zip-disk", [], RATES, NO_USED) is None


def test_estimate_ram_uses_market_median_when_sources_find_prices():
    def source_a(size_go, ram_type):
        return [280.0, 300.0]

    def source_b(size_go, ram_type):
        return [320.0]

    result = estimate_ram(32, "ddr5", [source_a, source_b], RATES, NO_USED)

    assert result == {"value": 300.0, "method": "médiane sur 3 annonces neuves"}


def test_estimate_ram_falls_back_to_formula_when_no_market_results():
    def empty_source(size_go, ram_type):
        return []

    result = estimate_ram(16, "ddr4", [empty_source], RATES, NO_USED)

    assert result == {"value": 32.0, "method": "formule €/Go"}


def test_estimate_ram_falls_back_to_formula_when_no_search_fns():
    result = estimate_ram(16, "ddr4", [], RATES, NO_USED)

    assert result == {"value": 32.0, "method": "formule €/Go"}


def test_estimate_ram_falls_back_to_ebay_used_before_formula():
    def used_search(size_go, ram_type):
        return [90.0, 100.0]

    result = estimate_ram(16, "ddr4", [], RATES, used_search)

    assert result == {"value": 95.0, "method": "médiane sur 2 annonces eBay occasion"}


def test_estimate_ram_prefers_new_market_median_over_used_when_both_available():
    def new_source(size_go, ram_type):
        return [280.0, 300.0]

    def used_search(size_go, ram_type):
        return [90.0]

    result = estimate_ram(32, "ddr5", [new_source], RATES, used_search)

    assert result == {"value": 290.0, "method": "médiane sur 2 annonces neuves"}


def test_estimate_storage_uses_market_median_when_sources_find_prices():
    def source_a(size_go, storage_type):
        return [45.0, 50.0, 55.0]

    result = estimate_storage(512, "ssd", [source_a], RATES, NO_USED)

    assert result == {"value": 50.0, "method": "médiane sur 3 annonces neuves"}


def test_estimate_storage_falls_back_to_formula_when_no_market_results():
    def empty_source(size_go, storage_type):
        return []

    result = estimate_storage(512, "ssd", [empty_source], RATES, NO_USED)

    assert result == {"value": 25.6, "method": "formule €/Go"}


def test_estimate_storage_falls_back_to_ebay_used_before_formula():
    def used_search(size_go, storage_type):
        return [30.0, 40.0]

    result = estimate_storage(512, "ssd", [], RATES, used_search)

    assert result == {"value": 35.0, "method": "médiane sur 2 annonces eBay occasion"}


def test_estimate_ram_aggregates_sources_concurrently():
    import time

    def make_slow_source(price):
        def slow_source(size_go, ram_type):
            time.sleep(0.1)
            return [price]

        return slow_source

    slow_sources = [make_slow_source(280.0 + i) for i in range(5)]

    start = time.perf_counter()
    result = estimate_ram(32, "ddr5", slow_sources, RATES, NO_USED)
    elapsed = time.perf_counter() - start

    assert result is not None
    assert elapsed < 0.3, (
        f"expected concurrent execution (~0.1s), took {elapsed:.3f}s "
        "(sequential would take >=0.5s)"
    )


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
        ram_search_fns=[],
        storage_search_fns=[],
        cpu_search_fns=[],
        gpu_search_fns=[],
        ram_used_search_fn=lambda *args: [],
        storage_used_search_fn=lambda *args: [],
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
        ram_used_search_fn=lambda *args: [],
        storage_used_search_fn=lambda *args: [],
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
        ram_used_search_fn=lambda *args: [],
        storage_used_search_fn=lambda *args: [],
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
        ram_used_search_fn=lambda *args: [],
        storage_used_search_fn=lambda *args: [],
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
        ram_used_search_fn=lambda *args: [],
        storage_used_search_fn=lambda *args: [],
    )

    assert result["breakdown"]["cpu"] == {
        "value": 465.0,
        "method": "médiane sur 2 annonces neuves",
    }
    assert result["breakdown"]["gpu"] == {
        "value": 900.0,
        "method": "médiane sur 1 annonces neuves",
    }


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


def test_estimate_new_pc_price_returns_none_with_no_search_fns():
    # Regression test: ThreadPoolExecutor(max_workers=0) raises ValueError,
    # so estimate_new_pc_price must guard against an empty search_fns list
    # rather than constructing an executor with zero workers.
    result = estimate_new_pc_price("cpu", "gpu", [])

    assert result is None


def test_estimate_new_pc_price_works_with_a_single_source():
    def only_source(cpu_model, gpu_model):
        return [999.0]

    result = estimate_new_pc_price("cpu", "gpu", [only_source])

    assert result == {"value": 999.0, "method": "médiane sur 1 annonces neuves"}


def test_estimate_new_pc_price_calls_sources_concurrently():
    import time

    def make_slow_source(price):
        def slow_source(cpu_model, gpu_model):
            time.sleep(0.1)
            return [price]

        return slow_source

    slow_sources = [make_slow_source(1000.0 + i) for i in range(5)]

    start = time.perf_counter()
    result = estimate_new_pc_price("cpu", "gpu", slow_sources)
    elapsed = time.perf_counter() - start

    assert result is not None
    assert elapsed < 0.3, (
        f"expected concurrent execution (~0.1s), took {elapsed:.3f}s "
        "(sequential would take >=0.5s)"
    )


from estimator import estimate_similar_used_price


def test_estimate_similar_used_price_returns_median_and_method():
    def search_fn(cpu_model, ram_go, ram_type, storage_go, storage_type, gpu_model):
        assert cpu_model == "i5-10400F"
        assert (ram_go, ram_type) == (16, "ddr4")
        assert (storage_go, storage_type) == (512, "ssd")
        assert gpu_model == "GTX 1650 Super"
        return [450.0, 480.0, 500.0]

    result = estimate_similar_used_price(
        "i5-10400F", 16, "ddr4", 512, "ssd", "GTX 1650 Super", search_fn
    )

    assert result == {
        "value": 480.0,
        "method": "médiane sur 3 annonces d'occasion similaires",
    }


def test_estimate_similar_used_price_returns_none_when_search_fn_finds_nothing():
    def empty_search_fn(*args):
        return []

    result = estimate_similar_used_price(
        "cpu", 16, "ddr4", 512, "ssd", "gpu", empty_search_fn
    )

    assert result is None


from estimator import estimate_sell_grid


def test_estimate_sell_grid_computes_new_price_minus_discount():
    result = estimate_sell_grid(1000.0, [0.10, 0.20, 0.30], floor=0.0)

    assert result == [
        {"pct": 0.10, "price": 900.0},
        {"pct": 0.20, "price": 800.0},
        {"pct": 0.30, "price": 700.0},
    ]


def test_estimate_sell_grid_rounds_to_two_decimals():
    result = estimate_sell_grid(999.0, [0.10], floor=0.0)

    assert result == [{"pct": 0.10, "price": 899.1}]


def test_estimate_sell_grid_clamps_tiers_at_the_component_floor():
    # Regression test: live-observed case (Ryzen 7 5700X + RTX 4060, 16Go
    # DDR4, 512Go SSD) where the neuf-30% tier (1084.93€) came out BELOW the
    # component breakdown total (1099.92€) -- recommending a resale price
    # lower than what the parts alone are worth separately. No sell tier may
    # go below the component floor.
    result = estimate_sell_grid(1549.90, [0.10, 0.20, 0.30], floor=1099.92)

    assert result == [
        {"pct": 0.10, "price": 1394.91},
        {"pct": 0.20, "price": 1239.92},
        {"pct": 0.30, "price": 1099.92},
    ]


def test_estimate_sell_grid_floor_does_not_affect_tiers_already_above_it():
    result = estimate_sell_grid(1000.0, [0.10], floor=100.0)

    assert result == [{"pct": 0.10, "price": 900.0}]


from estimator import estimate_buy_grid


def test_estimate_buy_grid_computes_price_as_pv_minus_discount():
    tiers = [
        {"max_pct": 0.50, "emoji": "🔥", "label": "Très bonne affaire"},
        {"max_pct": 0.40, "emoji": "✅", "label": "Intéressant"},
        {"max_pct": 0.20, "emoji": "❌", "label": "Je passe"},
    ]

    result = estimate_buy_grid(1000.0, tiers, 0.20)

    assert result == [
        {"max_price": 500.0, "emoji": "🔥", "label": "Très bonne affaire", "is_last": False},
        {"max_price": 600.0, "emoji": "✅", "label": "Intéressant", "is_last": False},
        {"max_price": 800.0, "emoji": "❌", "label": "Je passe", "is_last": True},
    ]


def test_estimate_buy_grid_last_tier_uses_margin_floor_not_its_own_pct():
    tiers = [
        {"max_pct": 0.10, "emoji": "🔥", "label": "Très bonne affaire"},
        {"max_pct": 0.99, "emoji": "❌", "label": "Je passe"},
    ]

    result = estimate_buy_grid(300.0, tiers, 0.70)

    assert result == [
        {"max_price": 270.0, "emoji": "🔥", "label": "Très bonne affaire", "is_last": False},
        {"max_price": 90.0, "emoji": "❌", "label": "Je passe", "is_last": True},
    ]


def test_estimate_buy_grid_floors_ceiling_at_zero():
    tiers = [{"max_pct": 0.50, "emoji": "❌", "label": "Je passe"}]

    result = estimate_buy_grid(100.0, tiers, 1.20)

    assert result == [{"max_price": 0.0, "emoji": "❌", "label": "Je passe", "is_last": True}]


def test_estimate_buy_grid_rounds_to_two_decimals():
    tiers = [
        {"max_pct": 0.415, "emoji": "🔥", "label": "Très bonne affaire"},
        {"max_pct": 0.50, "emoji": "❌", "label": "Je passe"},
    ]

    result = estimate_buy_grid(999.0, tiers, 0)

    assert result[0] == {
        "max_price": 584.42,
        "emoji": "🔥",
        "label": "Très bonne affaire",
        "is_last": False,
    }
    assert result[1] == {"max_price": 999.0, "emoji": "❌", "label": "Je passe", "is_last": True}
