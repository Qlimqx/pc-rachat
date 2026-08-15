from unittest.mock import patch, Mock

from retailers.amazon import (
    search_prices,
    search_ram_prices,
    search_storage_prices,
    search_cpu_prices,
    search_gpu_prices,
)


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
def test_search_prices_rejects_space_separated_near_miss_suffix(mock_get):
    # Regression test for the title-relevance filter's boundary check: a
    # near-miss variant written with a space before the suffix qualifier
    # (e.g. "RTX 4060 Ti") must be rejected exactly like the concatenated
    # form (e.g. "RTX4060Ti") -- both are a different, pricier card than a
    # plain "RTX 4060" search.
    html = """
    <html><body>
    <div data-component-type="s-search-result">
      <h2><span>PC Gamer Ryzen 7 5700X RTX 4060 Ti 16GB</span></h2>
      <div class="a-price"><span class="a-offscreen">1&nbsp;999,90&#8364;</span></div>
    </div>
    <div data-component-type="s-search-result">
      <h2><span>PC Gamer Ryzen 7 5700X RTX 4060 16GB</span></h2>
      <div class="a-price"><span class="a-offscreen">1&nbsp;399,90&#8364;</span></div>
    </div>
    </body></html>
    """
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.text = html
    mock_get.return_value = mock_response

    prices = search_prices("Ryzen 7 5700X", "RTX 4060")

    assert prices == [1399.9]


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


@patch("retailers.amazon.requests.get")
def test_search_ram_prices_handles_the_real_fixture_without_crashing(mock_get):
    # tests/fixtures/amazon_ram_search.html is the actual, unmodified
    # response body a live `requests.get()` (same headers this module
    # sends) got back from https://www.amazon.fr/s?k=16Go+DDR4 : HTTP 200
    # with an Akamai Bot Manager "bm-verify" interstitial page (a
    # <meta http-equiv="refresh"> redirect loop plus a JS proof-of-work
    # challenge), not a product listing -- a different bot-mitigation
    # mechanism than the AWS WAF challenge documented for search_prices,
    # but the same accepted, expected "blocked, no real data" outcome.
    with open("tests/fixtures/amazon_ram_search.html", encoding="utf-8") as f:
        html = f.read()

    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.text = html
    mock_get.return_value = mock_response

    prices = search_ram_prices(16, "DDR4")

    assert isinstance(prices, list)
    assert all(isinstance(p, float) for p in prices)
    assert prices == []


@patch("retailers.amazon.requests.get", side_effect=Exception("network error"))
def test_search_ram_prices_returns_empty_list_on_network_failure(mock_get):
    assert search_ram_prices(16, "DDR4") == []


@patch("retailers.amazon.requests.get")
def test_search_ram_prices_query_includes_go_and_type(mock_get):
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.text = "<html><body>not a product listing page</body></html>"
    mock_get.return_value = mock_response

    search_ram_prices(16, "DDR4")

    args, kwargs = mock_get.call_args
    assert args[0] == "https://www.amazon.fr/s"
    assert kwargs["params"] == {"k": "16Go DDR4"}


@patch("retailers.amazon.requests.get")
def test_search_ram_prices_extracts_prices_without_title_filtering(mock_get):
    # No live noise data came back (see fixture-based test above), so --
    # mirroring Rue du Commerce's Task 9 default -- no title-relevance
    # filter is applied to RAM results; every card with a parseable price
    # counts, regardless of title content.
    html = """
    <html><body>
    <div data-component-type="s-search-result">
      <h2><span>Corsair Vengeance 16Go DDR4 3200MHz</span></h2>
      <div class="a-price"><span class="a-offscreen">54,99&#8364;</span></div>
    </div>
    <div data-component-type="s-search-result">
      <h2><span>Totally unrelated title</span></h2>
      <div class="a-price"><span class="a-offscreen">1&nbsp;399,90&#8364;</span></div>
    </div>
    </body></html>
    """
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.text = html
    mock_get.return_value = mock_response

    prices = search_ram_prices(16, "DDR4")

    assert prices == [54.99, 1399.9]


@patch("retailers.amazon.requests.get")
def test_search_storage_prices_handles_the_real_fixture_without_crashing(mock_get):
    # tests/fixtures/amazon_storage_search.html is the actual, unmodified
    # response body a live `requests.get()` (same headers this module
    # sends) got back from https://www.amazon.fr/s?k=512Go+SSD -- the same
    # Akamai Bot Manager "bm-verify" interstitial as the RAM fixture above,
    # no product data.
    with open("tests/fixtures/amazon_storage_search.html", encoding="utf-8") as f:
        html = f.read()

    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.text = html
    mock_get.return_value = mock_response

    prices = search_storage_prices(512, "SSD")

    assert isinstance(prices, list)
    assert all(isinstance(p, float) for p in prices)
    assert prices == []


@patch("retailers.amazon.requests.get", side_effect=Exception("network error"))
def test_search_storage_prices_returns_empty_list_on_network_failure(mock_get):
    assert search_storage_prices(512, "SSD") == []


@patch("retailers.amazon.requests.get")
def test_search_storage_prices_query_includes_go_and_type(mock_get):
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.text = "<html><body>not a product listing page</body></html>"
    mock_get.return_value = mock_response

    search_storage_prices(512, "SSD")

    args, kwargs = mock_get.call_args
    assert args[0] == "https://www.amazon.fr/s"
    assert kwargs["params"] == {"k": "512Go SSD"}


@patch("retailers.amazon.requests.get")
def test_search_storage_prices_extracts_prices_without_title_filtering(mock_get):
    # No live noise data came back (see fixture-based test above), so --
    # mirroring Rue du Commerce's Task 9 default -- no title-relevance
    # filter is applied to storage results.
    html = """
    <html><body>
    <div data-component-type="s-search-result">
      <h2><span>Samsung SSD 512Go interne</span></h2>
      <div class="a-price"><span class="a-offscreen">39,99&#8364;</span></div>
    </div>
    <div data-component-type="s-search-result">
      <h2><span>Totally unrelated title</span></h2>
      <div class="a-price"><span class="a-offscreen">49,00&#8364;</span></div>
    </div>
    </body></html>
    """
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.text = html
    mock_get.return_value = mock_response

    prices = search_storage_prices(512, "SSD")

    assert prices == [39.99, 49.0]


@patch("retailers.amazon.requests.get")
def test_search_cpu_prices_handles_the_real_fixture_without_crashing(mock_get):
    # tests/fixtures/amazon_cpu_search.html is the actual, unmodified
    # response body a live `requests.get()` (same headers this module
    # sends) got back from https://www.amazon.fr/s?k=Ryzen+7+9800X3D : HTTP
    # 200 with an Akamai Bot Manager "bm-verify" interstitial page, the same
    # mechanism documented for search_ram_prices/search_storage_prices
    # above -- no product data, an accepted/expected outcome. Repeated live
    # attempts for this same query also got the AWS WAF empty-body 202
    # challenge on other tries (see the comment on search_cpu_prices in
    # retailers/amazon.py); either way the outcome is the same empty list.
    with open("tests/fixtures/amazon_cpu_search.html", encoding="utf-8") as f:
        html = f.read()

    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.text = html
    mock_get.return_value = mock_response

    prices = search_cpu_prices("Ryzen 7 9800X3D")

    assert isinstance(prices, list)
    assert all(isinstance(p, float) for p in prices)
    assert prices == []


@patch("retailers.amazon.requests.get", side_effect=Exception("network error"))
def test_search_cpu_prices_returns_empty_list_on_network_failure(mock_get):
    assert search_cpu_prices("Ryzen 7 9800X3D") == []


@patch("retailers.amazon.requests.get")
def test_search_cpu_prices_query_is_bare_model_name(mock_get):
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.text = "<html><body>not a product listing page</body></html>"
    mock_get.return_value = mock_response

    search_cpu_prices("Ryzen 7 9800X3D")

    args, kwargs = mock_get.call_args
    assert args[0] == "https://www.amazon.fr/s"
    assert kwargs["params"] == {"k": "Ryzen 7 9800X3D"}


@patch("retailers.amazon.requests.get")
def test_search_cpu_prices_extracts_prices_without_title_filtering(mock_get):
    # No live noise data came back (see fixture-based test above), so --
    # mirroring search_ram_prices/search_storage_prices' default -- no
    # title-relevance filter is applied to CPU results; every card with a
    # parseable price counts, regardless of title content.
    html = """
    <html><body>
    <div data-component-type="s-search-result">
      <h2><span>AMD Ryzen 7 9800X3D Processeur</span></h2>
      <div class="a-price"><span class="a-offscreen">479,00&#8364;</span></div>
    </div>
    <div data-component-type="s-search-result">
      <h2><span>Totally unrelated title</span></h2>
      <div class="a-price"><span class="a-offscreen">1&nbsp;399,90&#8364;</span></div>
    </div>
    </body></html>
    """
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.text = html
    mock_get.return_value = mock_response

    prices = search_cpu_prices("Ryzen 7 9800X3D")

    assert prices == [479.0, 1399.9]


@patch("retailers.amazon.requests.get")
def test_search_gpu_prices_handles_the_real_fixture_without_crashing(mock_get):
    # tests/fixtures/amazon_gpu_search.html is the actual, unmodified
    # response body a live `requests.get()` got back from
    # https://www.amazon.fr/s?k=RTX+5070+Ti : same Akamai "bm-verify"
    # interstitial as the CPU fixture above (and, on other attempts, the
    # same AWS WAF empty-body 202 challenge) -- no product data either way.
    with open("tests/fixtures/amazon_gpu_search.html", encoding="utf-8") as f:
        html = f.read()

    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.text = html
    mock_get.return_value = mock_response

    prices = search_gpu_prices("RTX 5070 Ti")

    assert isinstance(prices, list)
    assert all(isinstance(p, float) for p in prices)
    assert prices == []


@patch("retailers.amazon.requests.get", side_effect=Exception("network error"))
def test_search_gpu_prices_returns_empty_list_on_network_failure(mock_get):
    assert search_gpu_prices("RTX 5070 Ti") == []


@patch("retailers.amazon.requests.get")
def test_search_gpu_prices_query_is_bare_model_name(mock_get):
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.text = "<html><body>not a product listing page</body></html>"
    mock_get.return_value = mock_response

    search_gpu_prices("RTX 5070 Ti")

    args, kwargs = mock_get.call_args
    assert args[0] == "https://www.amazon.fr/s"
    assert kwargs["params"] == {"k": "RTX 5070 Ti"}


@patch("retailers.amazon.requests.get")
def test_search_gpu_prices_extracts_prices_without_title_filtering(mock_get):
    # No live noise data came back (see fixture-based test above), so --
    # mirroring search_ram_prices/search_storage_prices' default -- no
    # title-relevance filter is applied to GPU results.
    html = """
    <html><body>
    <div data-component-type="s-search-result">
      <h2><span>NVIDIA GeForce RTX 5070 Ti 16GB</span></h2>
      <div class="a-price"><span class="a-offscreen">899,00&#8364;</span></div>
    </div>
    <div data-component-type="s-search-result">
      <h2><span>Totally unrelated title</span></h2>
      <div class="a-price"><span class="a-offscreen">49,00&#8364;</span></div>
    </div>
    </body></html>
    """
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.text = html
    mock_get.return_value = mock_response

    prices = search_gpu_prices("RTX 5070 Ti")

    assert prices == [899.0, 49.0]
