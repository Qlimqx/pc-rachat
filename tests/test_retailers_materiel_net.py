from unittest.mock import patch, Mock
from urllib.parse import unquote

from retailers.materiel_net import search_prices, search_ram_prices, search_storage_prices


EXPECTED_PRICES = [
    1349.96, 3449.95, 1469.95, 1299.95, 1299.95, 1469.95, 3049.95, 2849.95,
    1849.95, 7799.95, 1199.95, 1379.95, 1319.95, 3099.95, 899.95, 1219.95,
    1769.95, 1999.95, 2549.95, 4199.95, 1199.95, 1049.95, 3149.95, 1599.95,
    1349.95, 3599.95, 2049.95, 2599.95, 2079.95, 8999.95, 2249.95, 3149.95,
    1849.95, 1379.95, 2799.95, 2899.95, 3449.95, 1299.95, 2949.95, 2449.95,
    1199.95, 1649.95, 5299.96, 2949.95, 2929.95, 1299.95, 1399.95, 3349.95,
]


@patch("retailers.materiel_net.requests.get")
def test_search_prices_extracts_prices_from_real_fixture(mock_get):
    with open("tests/fixtures/materiel_net_search.html", encoding="utf-8") as f:
        html = f.read()

    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.text = html
    mock_get.return_value = mock_response

    prices = search_prices("Ryzen 7 5700X", "RTX 4060")

    assert isinstance(prices, list)
    assert all(isinstance(p, float) for p in prices)
    assert prices == EXPECTED_PRICES


@patch("retailers.materiel_net.requests.get", side_effect=Exception("network error"))
def test_search_prices_returns_empty_list_on_network_failure(mock_get):
    assert search_prices("Ryzen 7 5700X", "RTX 4060") == []


@patch("retailers.materiel_net.requests.get")
def test_search_prices_returns_empty_list_on_unparseable_html(mock_get):
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.text = "<html><body>not a product listing page</body></html>"
    mock_get.return_value = mock_response

    assert search_prices("Ryzen 7 5700X", "RTX 4060") == []


@patch("retailers.materiel_net.requests.get")
def test_search_prices_query_excludes_cpu_model(mock_get):
    # Materiel.net's search does strict AND-matching, just like LDLC (both
    # are part of the LDLC Group and share the same search platform), so
    # including both the CPU and GPU model in the query returns almost
    # nothing (verified via live research: "Ryzen 7 5700X RTX 4060" returned
    # only 3 unrelated products). This locks in that the requested URL is
    # built from the GPU model plus a generic "PC gamer" term, and never
    # leaks the CPU model.
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.text = "<html><body>not a product listing page</body></html>"
    mock_get.return_value = mock_response

    search_prices("Ryzen 7 5700X", "RTX 4060")

    requested_url = mock_get.call_args[0][0]
    decoded_url = unquote(requested_url)

    assert "PC gamer" in decoded_url
    assert "RTX 4060" in decoded_url
    assert "ryzen" not in decoded_url.lower()


EXPECTED_RAM_PRICES = [
    169.94, 159.95, 129.95, 129.95, 176.95, 309.95, 299.95, 163.94, 179.95,
    149.95, 104.95, 619.94, 249.95, 259.94, 429.95, 219.95, 79.95, 299.95,
    103.95, 199.95, 339.95, 84.95, 142.95, 619.94, 179.95, 104.95, 182.95,
    279.95, 179.95, 159.95, 142.95, 599.95, 79.95, 299.95, 151.95, 186.95,
    103.95, 130.95, 130.95, 142.95, 135.95, 186.95, 299.95, 304.95, 327.95,
    249.95, 279.95, 135.95,
]

EXPECTED_STORAGE_PRICES = [139.95, 144.95, 179.95, 174.95, 219.95, 149.95]


@patch("retailers.materiel_net.requests.get")
def test_search_ram_prices_extracts_prices_from_real_fixture(mock_get):
    with open("tests/fixtures/materiel_net_ram_search.html", encoding="utf-8") as f:
        html = f.read()

    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.text = html
    mock_get.return_value = mock_response

    prices = search_ram_prices(16, "ddr4")

    assert isinstance(prices, list)
    assert all(isinstance(p, float) for p in prices)
    assert prices == EXPECTED_RAM_PRICES


@patch("retailers.materiel_net.requests.get", side_effect=Exception("network error"))
def test_search_ram_prices_returns_empty_list_on_network_failure(mock_get):
    assert search_ram_prices(16, "ddr4") == []


@patch("retailers.materiel_net.requests.get")
def test_search_ram_prices_query_contains_size_and_type(mock_get):
    # Locks in the constructed query so a future edit to the f-string in
    # search_ram_prices can't silently regress without a test catching it.
    # Also guards against re-introducing a case transform (e.g. .upper()):
    # Materiel.net's search is case-insensitive (verified live -- "RAM 16
    # Go ddr4" and "RAM 16 Go DDR4" return byte-identical result sets), so
    # ram_type must be passed through unmodified. Note the space between
    # the capacity and "Go" is load-bearing: "RAM 16Go DDR4" (no space)
    # auto-redirects to a single unrelated CPU+motherboard+RAM upgrade-kit
    # product instead of returning a search results page (verified live).
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.text = "<html><body>not a product listing page</body></html>"
    mock_get.return_value = mock_response

    search_ram_prices(16, "ddr4")

    requested_url = mock_get.call_args[0][0]
    decoded_url = unquote(requested_url)

    assert "RAM" in decoded_url
    assert "16 Go" in decoded_url
    assert "ddr4" in decoded_url


@patch("retailers.materiel_net.requests.get")
def test_search_storage_prices_extracts_prices_from_real_fixture(mock_get):
    with open("tests/fixtures/materiel_net_storage_search.html", encoding="utf-8") as f:
        html = f.read()

    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.text = html
    mock_get.return_value = mock_response

    prices = search_storage_prices(512, "ssd")

    assert isinstance(prices, list)
    assert all(isinstance(p, float) for p in prices)
    assert prices == EXPECTED_STORAGE_PRICES


@patch("retailers.materiel_net.requests.get", side_effect=Exception("network error"))
def test_search_storage_prices_returns_empty_list_on_network_failure(mock_get):
    assert search_storage_prices(512, "ssd") == []


@patch("retailers.materiel_net.requests.get")
def test_search_storage_prices_query_contains_size_and_type(mock_get):
    # Locks in the constructed query so a future edit to the f-string in
    # search_storage_prices can't silently regress without a test catching
    # it. Also guards against re-introducing a case transform (e.g.
    # .upper()): Materiel.net's search is case-insensitive (verified live),
    # so storage_type must be passed through unmodified. Note that a "Go"
    # suffix on the capacity is deliberately NOT included: with it (e.g.
    # "Disque SSD 512 Go" or "Disque SSD 512Go"), the results are dominated
    # (~85%+, verified live) by whole computers (iMacs, laptops) that merely
    # have a 512 Go drive inside, drowning out standalone SSD listings.
    # Dropping "Go" entirely (e.g. "Disque SSD 512") anchors tightly to
    # standalone SSD products only (verified live: 6/6 results were
    # genuine SSD listings, zero pollution).
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.text = "<html><body>not a product listing page</body></html>"
    mock_get.return_value = mock_response

    search_storage_prices(512, "ssd")

    requested_url = mock_get.call_args[0][0]
    decoded_url = unquote(requested_url)

    assert "Disque" in decoded_url
    assert "ssd" in decoded_url
    assert "512" in decoded_url
    assert "512Go" not in decoded_url
    assert "512 Go" not in decoded_url
