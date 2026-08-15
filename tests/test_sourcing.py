from unittest.mock import patch

from sourcing import make_new_pc_search_fn, make_ram_search_fn, make_storage_search_fn


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
