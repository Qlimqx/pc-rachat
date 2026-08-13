from unittest.mock import patch, Mock

from retailers.topachat import search_prices


EXPECTED_PRICES = [
    1449.99, 1249.99, 1519.99, 1549.99, 1199.99, 1299.99, 1399.99, 1229.99,
    1369.99, 1779.99, 1629.99, 1299.99, 1949.99, 1999.99, 999.99,
]


@patch("retailers.topachat.requests.get")
def test_search_prices_extracts_prices_from_real_fixture(mock_get):
    with open("tests/fixtures/topachat_search.html", encoding="utf-8") as f:
        html = f.read()

    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.text = html
    mock_get.return_value = mock_response

    prices = search_prices("Ryzen 7 5700X", "RTX 4060")

    assert isinstance(prices, list)
    assert all(isinstance(p, float) for p in prices)
    assert prices == EXPECTED_PRICES


@patch("retailers.topachat.requests.get", side_effect=Exception("network error"))
def test_search_prices_returns_empty_list_on_network_failure(mock_get):
    assert search_prices("Ryzen 7 5700X", "RTX 4060") == []


@patch("retailers.topachat.requests.get")
def test_search_prices_returns_empty_list_on_unparseable_html(mock_get):
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.text = "<html><body>not a product listing page</body></html>"
    mock_get.return_value = mock_response

    assert search_prices("Ryzen 7 5700X", "RTX 4060") == []


@patch("retailers.topachat.requests.get")
def test_search_prices_query_includes_both_cpu_and_gpu_model(mock_get):
    # TopAchat's search handles combined CPU+GPU queries well (verified live:
    # "Ryzen 7 5700X RTX 4060" returned a "PC Gamer" category where 13 of the
    # first 15 sampled builds actually contain a Ryzen 7 5700X). This locks
    # in that both models are sent together as the "terms" query param,
    # unlike LDLC which has to drop the CPU model.
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.text = "<html><body>not a product listing page</body></html>"
    mock_get.return_value = mock_response

    search_prices("Ryzen 7 5700X", "RTX 4060")

    _, kwargs = mock_get.call_args
    assert kwargs["params"] == {"terms": "Ryzen 7 5700X RTX 4060"}
