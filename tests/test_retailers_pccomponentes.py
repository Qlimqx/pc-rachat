from unittest.mock import patch, Mock
from urllib.parse import unquote

from retailers.pccomponentes import search_prices


EXPECTED_PRICES = [1291.2, 1297.8, 1264.83, 1242.4, 2710.19, 1548.39, 1465.3]


@patch("retailers.pccomponentes.requests.get")
def test_search_prices_extracts_prices_from_real_fixture(mock_get):
    with open("tests/fixtures/pccomponentes_search.html", encoding="utf-8") as f:
        html = f.read()

    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.text = html
    mock_get.return_value = mock_response

    prices = search_prices("Ryzen 7 5700X", "RTX 4060")

    assert isinstance(prices, list)
    assert all(isinstance(p, float) for p in prices)
    assert prices == EXPECTED_PRICES


@patch("retailers.pccomponentes.requests.get", side_effect=Exception("network error"))
def test_search_prices_returns_empty_list_on_network_failure(mock_get):
    assert search_prices("Ryzen 7 5700X", "RTX 4060") == []


@patch("retailers.pccomponentes.requests.get")
def test_search_prices_returns_empty_list_on_unparseable_html(mock_get):
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.text = "<html><body>not a product listing page</body></html>"
    mock_get.return_value = mock_response

    assert search_prices("Ryzen 7 5700X", "RTX 4060") == []


@patch("retailers.pccomponentes.requests.get")
def test_search_prices_query_includes_both_cpu_and_gpu_model(mock_get):
    # Unlike LDLC (strict AND-matching search that chokes on combined
    # CPU+GPU queries), PcComponentes' search is Algolia-backed and returns
    # highly relevant complete-PC results when both the CPU and GPU model
    # are included together (verified via live research: "Ryzen 7 5700X RTX
    # 4060" returned 7 matching PC builds containing both parts). This locks
    # in that, unlike ldlc.py, the CPU model is NOT dropped from the query.
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.text = "<html><body>not a product listing page</body></html>"
    mock_get.return_value = mock_response

    search_prices("Ryzen 7 5700X", "RTX 4060")

    requested_url = mock_get.call_args[0][0]
    decoded_url = unquote(requested_url)

    assert "Ryzen 7 5700X" in decoded_url
    assert "RTX 4060" in decoded_url
    assert decoded_url.startswith("https://www.pccomponentes.fr/search?query=")
