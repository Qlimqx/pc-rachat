from unittest.mock import patch, Mock

from retailers.rueducommerce import search_prices, search_ram_prices, search_storage_prices


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


# All 48 fixture cards, in order -- recomputed by running the (unfiltered)
# extraction logic in retailers/rueducommerce.py against the real fixture.
# No title-relevance filter is applied to search_ram_prices: verified live
# and against this fixture that "Barrette RAM 16Go DDR4" returns 48/48
# genuine standalone RAM module listings, 0% category noise (unlike the
# bare "16Go DDR4" query, which is 100% laptops/PCs/NAS appliances that
# merely mention "16Go DDR4" in their spec sheet), so filtering would only
# discard legitimate results.
EXPECTED_RAM_PRICES = [
    181.24, 146.2, 239.1, 209.99, 219.98, 229.99, 229.99, 229.99, 193.86,
    281.99, 289.99, 347.18, 206.99, 235.23, 298.35, 290.41, 305.99, 328.99,
    341.75, 236.39, 245.77, 223.35, 198.52, 380.55, 380.72, 329.0, 305.08,
    329.98, 339.9, 318.99, 518.23, 451.27, 389.0, 344.96, 478.04, 171.53,
    195.99, 186.99, 338.96, 622.94, 263.48, 260.96, 279.99, 331.37, 347.02,
    810.48, 223.99, 283.29,
]


@patch("retailers.rueducommerce.requests.get")
def test_search_ram_prices_extracts_prices_from_real_fixture(mock_get):
    with open("tests/fixtures/rueducommerce_ram_search.html", encoding="utf-8") as f:
        html = f.read()

    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.text = html
    mock_get.return_value = mock_response

    prices = search_ram_prices(16, "ddr4")

    assert isinstance(prices, list)
    assert all(isinstance(p, float) for p in prices)
    assert prices == EXPECTED_RAM_PRICES


@patch("retailers.rueducommerce.requests.get", side_effect=Exception("network error"))
def test_search_ram_prices_returns_empty_list_on_network_failure(mock_get):
    assert search_ram_prices(16, "ddr4") == []


@patch("retailers.rueducommerce.requests.get")
def test_search_ram_prices_returns_empty_list_on_unparseable_html(mock_get):
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.text = "<html><body>not a product listing page</body></html>"
    mock_get.return_value = mock_response

    assert search_ram_prices(16, "ddr4") == []


@patch("retailers.rueducommerce.requests.get")
def test_search_ram_prices_query_uses_barrette_ram_prefix(mock_get):
    # Regression test for the RAM query wording: verified live that a bare
    # "16Go DDR4" query returns 100% noise (whole laptops/PCs/NAS
    # appliances that merely mention "16Go DDR4" in their spec sheet), and
    # a plain "RAM 16Go DDR4" prefix (the pattern that works on LDLC)
    # barely helps here (~21% genuine RAM modules). Only prefixing with
    # "Barrette RAM" anchors the search to the standalone-memory-module
    # category, so the exact query wording matters and is worth pinning
    # down with a regression test.
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.text = "<html><body>not a product listing page</body></html>"
    mock_get.return_value = mock_response

    search_ram_prices(16, "ddr4")

    args, kwargs = mock_get.call_args
    assert (
        args[0]
        == "https://www.rueducommerce.fr/recherche/Barrette%20RAM%2016Go%20ddr4/"
    )


# All 15 fixture cards, in order -- recomputed by running the (unfiltered)
# extraction logic in retailers/rueducommerce.py against the real fixture.
# No title-relevance filter is applied to search_storage_prices: verified
# live and against this fixture that "ssd interne 512Go" returns 15/15
# genuine standalone SSD listings, 0% category noise (unlike bare "512Go
# SSD" or "Disque SSD 512Go", both of which mix in laptops that merely
# ship with a 512Go SSD), so filtering would only discard legitimate
# results.
EXPECTED_STORAGE_PRICES = [
    111.85, 118.99, 114.78, 129.25, 149.29, 112.3, 101.75, 92.11, 93.98,
    173.9, 187.35, 237.39, 174.99, 160.55, 98.99,
]


@patch("retailers.rueducommerce.requests.get")
def test_search_storage_prices_extracts_prices_from_real_fixture(mock_get):
    with open(
        "tests/fixtures/rueducommerce_storage_search.html", encoding="utf-8"
    ) as f:
        html = f.read()

    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.text = html
    mock_get.return_value = mock_response

    prices = search_storage_prices(512, "ssd")

    assert isinstance(prices, list)
    assert all(isinstance(p, float) for p in prices)
    assert prices == EXPECTED_STORAGE_PRICES


@patch("retailers.rueducommerce.requests.get", side_effect=Exception("network error"))
def test_search_storage_prices_returns_empty_list_on_network_failure(mock_get):
    assert search_storage_prices(512, "ssd") == []


@patch("retailers.rueducommerce.requests.get")
def test_search_storage_prices_returns_empty_list_on_unparseable_html(mock_get):
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.text = "<html><body>not a product listing page</body></html>"
    mock_get.return_value = mock_response

    assert search_storage_prices(512, "ssd") == []


@patch("retailers.rueducommerce.requests.get")
def test_search_storage_prices_query_uses_interne_qualifier(mock_get):
    # Regression test for the storage query wording: verified live that
    # neither a bare "512Go SSD" query nor the LDLC/Grosbill-style "Disque
    # SSD 512Go"/"Disque SSD 512" pattern avoids whole-laptop pollution on
    # this site (~42-100% noise). Only adding an "interne" qualifier after
    # the type (e.g. "ssd interne 512Go") anchors the search to standalone
    # drives, so the exact query wording matters and is worth pinning down
    # with a regression test.
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.text = "<html><body>not a product listing page</body></html>"
    mock_get.return_value = mock_response

    search_storage_prices(512, "ssd")

    args, kwargs = mock_get.call_args
    assert (
        args[0]
        == "https://www.rueducommerce.fr/recherche/ssd%20interne%20512Go/"
    )
