from unittest.mock import patch, Mock

from ebay_client import get_access_token


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
