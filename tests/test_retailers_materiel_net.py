from unittest.mock import patch, Mock
from urllib.parse import unquote

from retailers.materiel_net import (
    search_prices,
    search_ram_prices,
    search_storage_prices,
    search_cpu_prices,
    search_gpu_prices,
)


@patch("retailers.materiel_net.requests.get")
def test_search_prices_extracts_prices_from_real_fixture(mock_get):
    # This fixture was captured for a "PC gamer RTX 4060" query, but
    # inspecting it directly shows only ONE of the 48 cards' descriptions
    # genuinely mentions "RTX 4060" at all -- a used ("- Occasion") laptop,
    # which must not count as a new-market price. Every other card is
    # unrelated (different GPU generation or a laptop with a different GPU).
    # So an empty result is the verified-correct outcome here, not a
    # regression: the previous 48-value EXPECTED_PRICES (removed) was
    # unknowingly asserting on GPU-mismatched noise, from back before this
    # function had any relevance filtering at all.
    with open("tests/fixtures/materiel_net_search.html", encoding="utf-8") as f:
        html = f.read()

    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.text = html
    mock_get.return_value = mock_response

    prices = search_prices("Ryzen 7 5700X", "RTX 4060")

    assert prices == []


@patch("retailers.materiel_net.requests.get", side_effect=Exception("network error"))
def test_search_prices_returns_empty_list_on_network_failure(mock_get):
    assert search_prices("Ryzen 7 5700X", "RTX 4060") == []


def test_search_prices_returns_empty_list_without_making_a_request_when_no_gpu():
    with patch("retailers.materiel_net.requests.get") as mock_get:
        assert search_prices("i7-8700", "") == []
        mock_get.assert_not_called()


def _pc_card(title, desc, price="2999,95"):
    return f"""
    <li class="c-products-list__item">
        <h2 class="c-product__title">{title}</h2>
        <p class="c-product__description">{desc}</p>
        <span class="o-product__price">{price.split(",")[0]}<sup>{price.split(",")[1]}</sup></span>
    </li>
    """


@patch("retailers.materiel_net.requests.get")
def test_search_prices_accepts_a_genuine_complete_pc(mock_get):
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.text = _pc_card(
        "PC Gamer Permafrost - Win11 installé (version d'essai)",
        "NVIDIA GeForce RTX 5070 Ti, AMD Ryzen 7 9800X3D, 32 Go DDR5, SSD NVMe 1 To, Win11 version d'essai",
        "2499,95",
    )
    mock_get.return_value = mock_response

    assert search_prices("Ryzen 7 9800X3D", "RTX 5070 Ti") == [2499.95]


@patch("retailers.materiel_net.requests.get")
def test_search_prices_rejects_a_standalone_gpu_card(mock_get):
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.text = _pc_card(
        "Gainward GeForce RTX 5070 Ti Phoenix-S",
        "GeForce RTX 5070 Ti, PCI-Express 16x, 16 Go GDDR7, DLSS 4, HDMI / 3x DisplayPort",
        "1199,95",
    )
    mock_get.return_value = mock_response

    assert search_prices("Ryzen 7 9800X3D", "RTX 5070 Ti") == []


@patch("retailers.materiel_net.requests.get")
def test_search_prices_rejects_an_occasion_listing(mock_get):
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.text = _pc_card(
        "Asus ROG Strix G16 G614PR - Occasion",
        "PC portable gamer 16\", AMD Ryzen 9, RTX 5070 Ti, RAM 16 Go, SSD 1 To, Windows 11, AZERTY",
        "1899,95",
    )
    mock_get.return_value = mock_response

    assert search_prices("Ryzen 7 9800X3D", "RTX 5070 Ti") == []


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


EXPECTED_CPU_PRICES = [479.95, 499.95]

EXPECTED_GPU_PRICES = [
    1199.95, 1339.95, 1279.95, 1599.95, 1529.95, 1499.95, 1399.95, 1329.95,
    1329.95, 1399.95, 1329.95, 1349.95, 1429.95, 1279.95, 1429.95, 1399.95,
    1329.95,
]


@patch("retailers.materiel_net.requests.get")
def test_search_cpu_prices_extracts_prices_from_real_fixture(mock_get):
    with open("tests/fixtures/materiel_net_cpu_search.html", encoding="utf-8") as f:
        html = f.read()

    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.text = html
    mock_get.return_value = mock_response

    prices = search_cpu_prices("Ryzen 7 9800X3D")

    assert isinstance(prices, list)
    assert all(isinstance(p, float) for p in prices)
    assert prices == EXPECTED_CPU_PRICES


@patch("retailers.materiel_net.requests.get", side_effect=Exception("network error"))
def test_search_cpu_prices_returns_empty_list_on_network_failure(mock_get):
    assert search_cpu_prices("Ryzen 7 9800X3D") == []


@patch("retailers.materiel_net.requests.get")
def test_search_cpu_prices_query_contains_anchor_and_model(mock_get):
    # Locks in the constructed query so a future edit to the f-string in
    # search_cpu_prices can't silently regress without a test catching it.
    # A bare model name (verified live) pulls in mostly "PC Gamer <name>"
    # prebuilt listings (17/22); prefixing with "Processeur" drops every one
    # of them.
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.text = "<html><body>not a product listing page</body></html>"
    mock_get.return_value = mock_response

    search_cpu_prices("Ryzen 7 9800X3D")

    requested_url = mock_get.call_args[0][0]
    decoded_url = unquote(requested_url)

    assert decoded_url.endswith("/recherche/Processeur Ryzen 7 9800X3D/")


@patch("retailers.materiel_net.requests.get")
def test_search_cpu_prices_excludes_kit_and_used_listings(mock_get):
    # Regression test for the two noise sources found live in the CPU
    # fixture: a motherboard+CPU "Kit upgrade PC" bundle whose title
    # contains the full requested model as a verbatim substring (a genuine
    # substring/superset case a plain substring check would miss), and a
    # used ("- Occasion") listing of the same genuine model, which must not
    # leak into a search meant to source *new* prices.
    html = """
    <html><body>
    <li class="c-products-list__item">
        <h2 class="c-product__title">AMD Ryzen 7 9800X3D (4.7 GHz / 5.2 GHz)</h2>
        <div class="o-product__price">499€<sup>95</sup></div>
    </li>
    <li class="c-products-list__item">
        <h2 class="c-product__title">MSI MAG B850 TOMAHAWK MAX WIFI + AMD Ryzen 7 9800X3D (Version tray)</h2>
        <div class="o-product__price">739€<sup>90</sup></div>
    </li>
    <li class="c-products-list__item">
        <h2 class="c-product__title">AMD Ryzen 7 9800X3D (4.7 GHz) - Version tray - Occasion</h2>
        <div class="o-product__price">431€<sup>95</sup></div>
    </li>
    </body></html>
    """
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.text = html
    mock_get.return_value = mock_response

    assert search_cpu_prices("Ryzen 7 9800X3D") == [499.95]


@patch("retailers.materiel_net.requests.get")
def test_search_gpu_prices_extracts_prices_from_real_fixture(mock_get):
    with open("tests/fixtures/materiel_net_gpu_search.html", encoding="utf-8") as f:
        html = f.read()

    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.text = html
    mock_get.return_value = mock_response

    prices = search_gpu_prices("RTX 5070 Ti")

    assert isinstance(prices, list)
    assert all(isinstance(p, float) for p in prices)
    assert prices == EXPECTED_GPU_PRICES


@patch("retailers.materiel_net.requests.get", side_effect=Exception("network error"))
def test_search_gpu_prices_returns_empty_list_on_network_failure(mock_get):
    assert search_gpu_prices("RTX 5070 Ti") == []


@patch("retailers.materiel_net.requests.get")
def test_search_gpu_prices_query_contains_anchor_and_model(mock_get):
    # Locks in the constructed query so a future edit to the f-string in
    # search_gpu_prices can't silently regress without a test catching it.
    # A bare model name (verified live) pulls in mostly prebuilt PCs and
    # gaming laptops (50 results); prefixing with "Carte graphique" drops
    # them all (27 results left).
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.text = "<html><body>not a product listing page</body></html>"
    mock_get.return_value = mock_response

    search_gpu_prices("RTX 5070 Ti")

    requested_url = mock_get.call_args[0][0]
    decoded_url = unquote(requested_url)

    assert decoded_url.endswith("/recherche/Carte graphique RTX 5070 Ti/")


@patch("retailers.materiel_net.requests.get")
def test_search_gpu_prices_excludes_non_ti_and_used_listings(mock_get):
    # Regression test for the two noise sources found live in the GPU
    # fixture: plain non-Ti "RTX 5070" cards (Materiel.net's search doesn't
    # do exact phrase matching on "Ti") and used ("- Occasion") listings of
    # the genuine Ti model, which must not leak into a search meant to
    # source *new* prices.
    html = """
    <html><body>
    <li class="c-products-list__item">
        <h2 class="c-product__title">Gainward GeForce RTX 5070 Ti Phoenix-S</h2>
        <div class="o-product__price">1 199€<sup>95</sup></div>
    </li>
    <li class="c-products-list__item">
        <h2 class="c-product__title">Asus DUAL GeForce RTX 5070 12GB GDDR7 OC</h2>
        <div class="o-product__price">839€<sup>95</sup></div>
    </li>
    <li class="c-products-list__item">
        <h2 class="c-product__title">Gainward GeForce RTX 5070 Ti Phoenix-S - Occasion</h2>
        <div class="o-product__price">1 079€<sup>95</sup></div>
    </li>
    </body></html>
    """
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.text = html
    mock_get.return_value = mock_response

    assert search_gpu_prices("RTX 5070 Ti") == [1199.95]
