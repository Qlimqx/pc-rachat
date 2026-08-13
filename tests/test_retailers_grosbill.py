from unittest.mock import patch, Mock

from retailers.grosbill import search_prices


EXPECTED_PRICES = [1649.99, 1279.99, 1299.99, 1199.99, 1479.99]


@patch("retailers.grosbill.requests.get")
def test_search_prices_extracts_prices_from_real_fixture(mock_get):
    with open("tests/fixtures/grosbill_search.html", encoding="utf-8") as f:
        html = f.read()

    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.text = html
    mock_get.return_value = mock_response

    prices = search_prices("Ryzen 7 5700X", "RTX 4060")

    assert isinstance(prices, list)
    assert all(isinstance(p, float) for p in prices)
    assert prices == EXPECTED_PRICES


@patch("retailers.grosbill.requests.get", side_effect=Exception("network error"))
def test_search_prices_returns_empty_list_on_network_failure(mock_get):
    assert search_prices("Ryzen 7 5700X", "RTX 4060") == []


@patch("retailers.grosbill.requests.get")
def test_search_prices_returns_empty_list_on_unparseable_html(mock_get):
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.text = "<html><body>not a product listing page</body></html>"
    mock_get.return_value = mock_response

    assert search_prices("Ryzen 7 5700X", "RTX 4060") == []


@patch("retailers.grosbill.requests.get")
def test_search_prices_query_excludes_gpu_model(mock_get):
    # Grosbill's search does strict AND-matching, just like LDLC and
    # Materiel.net. Combining the CPU and GPU model returns zero results
    # (verified live: "Ryzen 7 5700X RTX 4060" -> "aucun produit ne
    # correspond"). Searching "PC gamer {cpu_model}" alone, however, returns
    # only the "PC Gamer" complete-build category (5 matching builds,
    # verified live), filtering out standalone CPU/GPU component listings
    # that a bare cpu_model search would also return. This locks in that the
    # GPU model is never leaked into the query, unlike ldlc.py which drops
    # the CPU model instead (Grosbill's inventory pairs this CPU with newer
    # GPUs, not the requested RTX 4060, so keeping the GPU term would zero
    # out results).
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.text = "<html><body>not a product listing page</body></html>"
    mock_get.return_value = mock_response

    search_prices("Ryzen 7 5700X", "RTX 4060")

    args, kwargs = mock_get.call_args
    assert args[0] == "https://www.grosbill.com/produit.aspx"
    assert kwargs["params"] == {"q": "PC gamer Ryzen 7 5700X"}
