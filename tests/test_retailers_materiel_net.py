from unittest.mock import patch, Mock
from urllib.parse import unquote

from retailers.materiel_net import search_prices


EXPECTED_PRICES = [
    1349.96, 3449.95, 1469.95, 1299.95, 1299.95, 1469.95, 3049.95, 2849.95,
    1849.95, 7799.95, 1199.95, 1379.95, 1319.95, 3099.95, 899.95, 1219.95,
    1769.95, 1999.95, 2549.95, 4199.95, 1199.95, 1049.95, 3149.95, 1599.95,
    1349.95, 3599.95, 2049.95, 2599.95, 2079.95, 8999.95, 2249.95, 3149.95,
    1849.95, 1379.95, 2799.95, 2899.95, 3449.95, 1299.95, 2949.95, 2449.95,
    1199.95, 1649.95, 5299.96, 2949.95, 2929.95, 1299.95, 1399.95, 3349.95,
]


@patch("retailers.materiel_net.requests.get")
def test_search_prices_extracts_prices_from_real_fixture(mock_get):
    with open("tests/fixtures/materiel_net_search.html", encoding="utf-8") as f:
        html = f.read()

    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.text = html
    mock_get.return_value = mock_response

    prices = search_prices("Ryzen 7 5700X", "RTX 4060")

    assert isinstance(prices, list)
    assert all(isinstance(p, float) for p in prices)
    assert prices == EXPECTED_PRICES


@patch("retailers.materiel_net.requests.get", side_effect=Exception("network error"))
def test_search_prices_returns_empty_list_on_network_failure(mock_get):
    assert search_prices("Ryzen 7 5700X", "RTX 4060") == []


@patch("retailers.materiel_net.requests.get")
def test_search_prices_returns_empty_list_on_unparseable_html(mock_get):
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.text = "<html><body>not a product listing page</body></html>"
    mock_get.return_value = mock_response

    assert search_prices("Ryzen 7 5700X", "RTX 4060") == []


@patch("retailers.materiel_net.requests.get")
def test_search_prices_query_excludes_cpu_model(mock_get):
    # Materiel.net's search does strict AND-matching, just like LDLC (both
    # are part of the LDLC Group and share the same search platform), so
    # including both the CPU and GPU model in the query returns almost
    # nothing (verified via live research: "Ryzen 7 5700X RTX 4060" returned
    # only 3 unrelated products). This locks in that the requested URL is
    # built from the GPU model plus a generic "PC gamer" term, and never
    # leaks the CPU model.
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
