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
