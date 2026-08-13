from unittest.mock import patch, Mock

from retailers.rueducommerce import search_prices


EXPECTED_PRICES = [
    1639.9, 1549.9, 1549.9, 1529.9, 1539.9, 1619.9, 1609.9, 1629.9, 1459.9,
    1539.9, 1899.9, 1539.9, 1489.9, 1629.9, 1679.9, 1459.9, 1589.9, 1509.9,
    1549.9, 1459.9, 1409.9, 1379.9, 1409.9, 1489.9, 1439.9, 1359.9, 1329.9,
    1609.9, 1689.9, 1299.0, 1089.0, 1199.0, 1519.99, 1369.99, 1959.9,
    2149.9, 1909.9, 2179.9, 2269.9, 2069.9, 1929.9, 2289.9, 2369.9, 2169.9,
    2149.9, 2179.9, 1979.9, 2269.9,
]


@patch("retailers.rueducommerce.requests.get")
def test_search_prices_extracts_prices_from_real_fixture(mock_get):
    with open("tests/fixtures/rueducommerce_search.html", encoding="utf-8") as f:
        html = f.read()

    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.text = html
    mock_get.return_value = mock_response

    prices = search_prices("Ryzen 7 5700X", "RTX 4060")

    assert isinstance(prices, list)
    assert all(isinstance(p, float) for p in prices)
    assert prices == EXPECTED_PRICES


@patch("retailers.rueducommerce.requests.get", side_effect=Exception("network error"))
def test_search_prices_returns_empty_list_on_network_failure(mock_get):
    assert search_prices("Ryzen 7 5700X", "RTX 4060") == []


@patch("retailers.rueducommerce.requests.get")
def test_search_prices_returns_empty_list_on_unparseable_html(mock_get):
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.text = "<html><body>not a product listing page</body></html>"
    mock_get.return_value = mock_response

    assert search_prices("Ryzen 7 5700X", "RTX 4060") == []


@patch("retailers.rueducommerce.requests.get")
def test_search_prices_query_includes_both_cpu_and_gpu_model(mock_get):
    # Rue du Commerce's search (a path-based /recherche/{query}/ endpoint,
    # server-rendered -- no JSON API involved, verified live via network
    # inspection) handles a combined CPU+GPU query well, unlike LDLC/
    # Materiel.net/Grosbill which choke on it. Verified live: "Ryzen 7
    # 5700X RTX 4060" returned 48 "PC" category listings, 34 of which
    # actually contain "5700X" and all of which contain "4060" -- a mix of
    # relevant and near-miss (RTX 4060 Ti, Ryzen 7 9700X) results typical of
    # this marketplace's fuzzy relevance ranking, similar to TopAchat/
    # PcComponentes. So, like those two, both models are kept together in
    # the query.
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.text = "<html><body>not a product listing page</body></html>"
    mock_get.return_value = mock_response

    search_prices("Ryzen 7 5700X", "RTX 4060")

    args, kwargs = mock_get.call_args
    assert (
        args[0]
        == "https://www.rueducommerce.fr/recherche/Ryzen%207%205700X%20RTX%204060/"
    )
