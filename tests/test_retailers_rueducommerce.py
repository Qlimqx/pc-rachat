from unittest.mock import patch, Mock

from retailers.rueducommerce import search_prices


# Filtered to the 12/48 fixture cards whose title actually references both
# "Ryzen 7 5700X" and "RTX 4060" (not 4060 Ti) -- recomputed by running the
# filtering logic in retailers/rueducommerce.py against the real fixture.
EXPECTED_PRICES = [
    1549.9, 1549.9, 1529.9, 1539.9, 1459.9, 1459.9, 1509.9, 1409.9, 1379.9,
    1359.9, 1329.9, 1609.9,
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
def test_search_prices_rejects_space_separated_near_miss_suffix(mock_get):
    # Regression test for the title-relevance filter's boundary check: a
    # near-miss variant written with a space before the suffix qualifier
    # (e.g. "RTX 4060 Ti") must be rejected exactly like the concatenated
    # form (e.g. "RTX4060Ti") already correctly seen in the real fixture --
    # both are a different, pricier card than a plain "RTX 4060" search.
    html = """
    <html><body>
    <li class="pdt-item">
      <h3 class="title-3">Sedatech PC Gamer, AMD Ryzen 7 5700X, RTX 4060 Ti, 32Go RAM</h3>
      <div class="price"><div class="new-price">1&nbsp;999,90&#8364;</div></div>
    </li>
    <li class="pdt-item">
      <h3 class="title-3">Sedatech PC Gamer, AMD Ryzen 7 5700X, RTX 4060, 32Go RAM</h3>
      <div class="price"><div class="new-price">1&nbsp;399,90&#8364;</div></div>
    </li>
    </body></html>
    """
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.text = html
    mock_get.return_value = mock_response

    prices = search_prices("Ryzen 7 5700X", "RTX 4060")

    assert prices == [1399.9]


@patch("retailers.rueducommerce.requests.get")
def test_search_prices_query_includes_both_cpu_and_gpu_model(mock_get):
    # Rue du Commerce's search (a path-based /recherche/{query}/ endpoint,
    # server-rendered -- no JSON API involved, verified live via network
    # inspection) handles a combined CPU+GPU query well, unlike LDLC/
    # Materiel.net/Grosbill which choke on it. Verified against the real
    # fixture: "Ryzen 7 5700X RTX 4060" returned 48 "PC" category listings,
    # but only 33/48 actually contain "5700X" and only 22/48 contain exact
    # "4060" (43/48 contain "4060" as part of a family match, the rest being
    # RTX 4060 Ti/RTX 5060/RTX 5060 Ti, and 15/48 are Ryzen 7 9700X or 7700X
    # builds) -- a mix of relevant and near-miss results typical of this
    # marketplace's fuzzy relevance ranking, similar to TopAchat/
    # PcComponentes. So, like those two, both models are kept together in
    # the query, and search_prices() applies its own title-relevance filter
    # afterward to drop the near-miss noise (see
    # test_search_prices_extracts_prices_from_real_fixture).
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
