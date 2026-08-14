from unittest.mock import patch, Mock

from ebay_client import get_access_token, search_used_prices


@patch("ebay_client.requests.post")
def test_get_access_token_returns_token_on_success(mock_post):
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"access_token": "abc123", "expires_in": 7200}
    mock_post.return_value = mock_response

    token = get_access_token("client-id", "client-secret")

    assert token == "abc123"


@patch("ebay_client.requests.post")
def test_get_access_token_raises_on_http_error(mock_post):
    mock_response = Mock()
    mock_response.status_code = 401
    mock_response.raise_for_status.side_effect = Exception("401 Unauthorized")
    mock_post.return_value = mock_response

    try:
        get_access_token("bad-id", "bad-secret")
        assert False, "expected an exception"
    except Exception as e:
        assert "401" in str(e)


@patch("ebay_client.requests.get")
def test_search_used_prices_extracts_prices(mock_get):
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "itemSummaries": [
            {"price": {"value": "55.00", "currency": "EUR"}},
            {"price": {"value": "60.50", "currency": "EUR"}},
        ]
    }
    mock_get.return_value = mock_response

    prices = search_used_prices("i5-10400 processor", "token123")

    assert prices == [55.00, 60.50]


@patch("ebay_client.requests.get")
def test_search_used_prices_returns_empty_list_when_no_results(mock_get):
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {}
    mock_get.return_value = mock_response

    prices = search_used_prices("completely-unknown-part", "token123")

    assert prices == []


@patch("ebay_client.requests.get")
def test_search_used_prices_sends_marketplace_and_condition_filters(mock_get):
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"itemSummaries": []}
    mock_get.return_value = mock_response

    search_used_prices("i5-10400 processor", "token123")

    _, kwargs = mock_get.call_args
    assert kwargs["headers"]["X-EBAY-C-MARKETPLACE-ID"] == "EBAY_FR"
    assert "conditionIds" in kwargs["params"]["filter"]


from ebay_client import search_component_price


@patch("ebay_client.search_used_prices")
@patch("ebay_client.get_access_token")
def test_search_component_price_returns_prices_on_success(mock_token, mock_search):
    mock_token.return_value = "tok"
    mock_search.return_value = [50.0, 60.0]

    result = search_component_price("i5-10400", "cpu", "id", "secret")

    assert result == [50.0, 60.0]
    mock_search.assert_called_once_with("i5-10400 cpu", "tok")


@patch("ebay_client.get_access_token", side_effect=Exception("network error"))
def test_search_component_price_returns_none_on_token_failure(mock_token):
    result = search_component_price("i5-10400", "cpu", "id", "secret")

    assert result is None


@patch("ebay_client.search_used_prices", side_effect=Exception("timeout"))
@patch("ebay_client.get_access_token")
def test_search_component_price_returns_none_on_search_failure(mock_token, mock_search):
    mock_token.return_value = "tok"

    result = search_component_price("gtx 1660", "gpu", "id", "secret")

    assert result is None


from ebay_client import search_new_prices, search_new_pc_prices


@patch("ebay_client.requests.get")
def test_search_new_prices_uses_new_condition_filter(mock_get):
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "itemSummaries": [{"price": {"value": "1400.00", "currency": "EUR"}}]
    }
    mock_get.return_value = mock_response

    prices = search_new_prices("Ryzen 7 5700X RTX 4060 PC", "token123")

    assert prices == [1400.00]
    _, kwargs = mock_get.call_args
    assert "1000" in kwargs["params"]["filter"]


@patch("ebay_client.search_new_prices")
@patch("ebay_client.get_access_token")
def test_search_new_pc_prices_returns_prices_on_success(mock_token, mock_search):
    mock_token.return_value = "tok"
    mock_search.return_value = [1400.0, 1420.0]

    result = search_new_pc_prices("Ryzen 7 5700X", "RTX 4060", "id", "secret")

    assert result == [1400.0, 1420.0]
    mock_search.assert_called_once_with("Ryzen 7 5700X RTX 4060 PC", "tok")


@patch("ebay_client.get_access_token", side_effect=Exception("network error"))
def test_search_new_pc_prices_returns_empty_list_on_token_failure(mock_token):
    result = search_new_pc_prices("Ryzen 7 5700X", "RTX 4060", "id", "secret")
    assert result == []


@patch("ebay_client.search_new_prices", side_effect=Exception("timeout"))
@patch("ebay_client.get_access_token")
def test_search_new_pc_prices_returns_empty_list_on_search_failure(mock_token, mock_search):
    mock_token.return_value = "tok"
    result = search_new_pc_prices("Ryzen 7 5700X", "RTX 4060", "id", "secret")
    assert result == []


from ebay_client import search_ram_prices, search_storage_prices


@patch("ebay_client.search_new_prices")
@patch("ebay_client.get_access_token")
def test_search_ram_prices_returns_prices_on_success(mock_token, mock_search):
    mock_token.return_value = "tok"
    mock_search.return_value = [280.0, 300.0]

    result = search_ram_prices(32, "ddr5", "id", "secret")

    assert result == [280.0, 300.0]
    mock_search.assert_called_once_with("32Go ddr5 RAM", "tok")


@patch("ebay_client.get_access_token", side_effect=Exception("network error"))
def test_search_ram_prices_returns_empty_list_on_failure(mock_token):
    result = search_ram_prices(32, "ddr5", "id", "secret")
    assert result == []


@patch("ebay_client.search_new_prices")
@patch("ebay_client.get_access_token")
def test_search_storage_prices_returns_prices_on_success(mock_token, mock_search):
    mock_token.return_value = "tok"
    mock_search.return_value = [45.0, 50.0]

    result = search_storage_prices(512, "ssd", "id", "secret")

    assert result == [45.0, 50.0]
    mock_search.assert_called_once_with("512Go ssd", "tok")


@patch("ebay_client.get_access_token", side_effect=Exception("network error"))
def test_search_storage_prices_returns_empty_list_on_failure(mock_token):
    result = search_storage_prices(512, "ssd", "id", "secret")
    assert result == []
