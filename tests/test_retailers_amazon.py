from unittest.mock import patch, Mock

from retailers.amazon import search_prices


@patch("retailers.amazon.requests.get")
def test_search_prices_handles_the_real_fixture_without_crashing(mock_get):
    # tests/fixtures/amazon_search.html is the actual, unmodified response
    # body a live `requests.get()` (same headers this module sends, no
    # cookies, no JS execution) got back from
    # https://www.amazon.fr/s?k=Ryzen+7+5700X+RTX+4060 : HTTP 202 with
    # `x-amzn-waf-action: challenge` -- an AWS WAF bot-challenge page (a
    # `window.gokuProps` / challenge.js loader with a "we need to verify
    # that you're not a robot" noscript fallback), not a product listing. A
    # full browser render of the same query did return real results, which
    # confirms this is anti-bot gating specific to plain HTTP requests, not
    # a broken selector. That's the accepted, expected outcome for this
    # scraper, so the fixture legitimately yields no prices.
    with open("tests/fixtures/amazon_search.html", encoding="utf-8") as f:
        html = f.read()

    mock_response = Mock()
    mock_response.status_code = 202
    mock_response.text = html
    mock_get.return_value = mock_response

    prices = search_prices("Ryzen 7 5700X", "RTX 4060")

    assert isinstance(prices, list)
    assert all(isinstance(p, float) for p in prices)
    assert prices == []


@patch("retailers.amazon.requests.get", side_effect=Exception("network error"))
def test_search_prices_returns_empty_list_on_network_failure(mock_get):
    assert search_prices("Ryzen 7 5700X", "RTX 4060") == []


@patch("retailers.amazon.requests.get")
def test_search_prices_returns_empty_list_on_unparseable_html(mock_get):
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.text = "<html><body>not a product listing page</body></html>"
    mock_get.return_value = mock_response

    assert search_prices("Ryzen 7 5700X", "RTX 4060") == []


@patch("retailers.amazon.requests.get")
def test_search_prices_query_includes_both_cpu_and_gpu_model(mock_get):
    # Unlike LDLC/Materiel.net/Grosbill (strict AND-matching, choke on
    # combined CPU+GPU queries), Amazon's search doesn't reject a combined
    # query outright -- verified live via a full browser render that
    # "Ryzen 7 5700X RTX 4060" returned 557 total results (56 on the first
    # page). So, like PcComponentes/TopAchat/Rue du Commerce, both models
    # are kept together in the query, and search_prices() applies its own
    # title-relevance filter to drop near-miss noise (verified live: 0 of
    # the 56 first-page titles actually mention "4060" at all -- the ranked
    # builds pair this CPU with newer cards like RTX 5060/5060 Ti/5070
    # instead).
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.text = "<html><body>not a product listing page</body></html>"
    mock_get.return_value = mock_response

    search_prices("Ryzen 7 5700X", "RTX 4060")

    args, kwargs = mock_get.call_args
    assert args[0] == "https://www.amazon.fr/s"
    assert kwargs["params"] == {"k": "Ryzen 7 5700X RTX 4060"}
