from estimator import median_price


def test_median_price_odd_count():
    assert median_price([10.0, 30.0, 20.0]) == 20.0


def test_median_price_even_count():
    assert median_price([10.0, 20.0, 30.0, 40.0]) == 25.0


def test_median_price_single_value():
    assert median_price([42.0]) == 42.0
