from unittest.mock import patch, Mock
from urllib.parse import unquote

from retailers.ldlc import search_prices


EXPECTED_PRICES = [
    1349.96, 1029.95, 949.99, 1169.95, 929.95, 1399.95, 1639.95, 1049.99,
    1469.95, 2599.95, 1299.95, 1039.95, 1549.95, 1319.95, 1149.95, 1199.95,
    1309.95, 1239.95, 1219.95, 1999.95, 1409.95, 1339.95, 1349.95, 1299.95,
    3949.95, 1849.95, 1199.95, 1599.95, 2499.95, 1999.95, 2299.95, 2299.95,
    1999.95, 1999.95, 1779.95, 1379.95, 1649.95, 1499.95, 2549.95, 2149.95,
    2149.95, 2199.95, 3699.95, 1659.95, 1899.95, 2399.95, 2699.95, 1699.95,
]


@patch("retailers.ldlc.requests.get")
def test_search_prices_extracts_prices_from_real_fixture(mock_get):
    with open("tests/fixtures/ldlc_search.html", encoding="utf-8") as f:
        html = f.read()

    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.text = html
    mock_get.return_value = mock_response

    prices = search_prices("Ryzen 7 5700X", "RTX 4060")

    assert isinstance(prices, list)
    assert all(isinstance(p, float) for p in prices)
    assert prices == EXPECTED_PRICES


@patch("retailers.ldlc.requests.get", side_effect=Exception("network error"))
def test_search_prices_returns_empty_list_on_network_failure(mock_get):
    assert search_prices("Ryzen 7 5700X", "RTX 4060") == []


@patch("retailers.ldlc.requests.get")
def test_search_prices_returns_empty_list_on_unparseable_html(mock_get):
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.text = "<html><body>not a product listing page</body></html>"
    mock_get.return_value = mock_response

    assert search_prices("Ryzen 7 5700X", "RTX 4060") == []


@patch("retailers.ldlc.requests.get")
def test_search_prices_query_excludes_cpu_model(mock_get):
    # LDLC's search does strict AND-matching, so including both the CPU and
    # GPU model in the query returns almost nothing (verified via live
    # research). This locks in that the requested URL is built from the GPU
    # model plus a generic "PC gamer" term, and never leaks the CPU model.
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.text = "<html><body>not a product listing page</body></html>"
    mock_get.return_value = mock_response

    search_prices("Ryzen 7 5700X", "RTX 4060")

    requested_url = mock_get.call_args[0][0]
    decoded_url = unquote(requested_url)

    assert "PC gamer" in decoded_url
    assert "RTX 4060" in decoded_url
    assert "ryzen" not in decoded_url.lower()
