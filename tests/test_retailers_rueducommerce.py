from unittest.mock import patch, Mock

from retailers.rueducommerce import (
    search_prices,
    search_ram_prices,
    search_storage_prices,
    search_cpu_prices,
    search_gpu_prices,
)


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


# 3/12 fixture cards genuinely match "Ryzen 7 9800X3D": recomputed by running
# the filtering logic in retailers/rueducommerce.py's search_cpu_prices
# against the real fixture. The other 9 are dropped -- 8 are a different
# Ryzen X3D SKU (9850X3D/5800X3D/7800X3D, including a "7800X3D Bundle The
# Force" motherboard kit) that _title_matches_model's substring check
# rejects, and 1 is a genuine "Ryzen 7 9800X3D" listing carrying a
# <span class="label label--reconditioned"> marker that the reconditioned
# skip drops (see search_cpu_prices' comment).
EXPECTED_CPU_PRICES = [469.99, 451.0, 3292.95]


@patch("retailers.rueducommerce.requests.get")
def test_search_cpu_prices_extracts_prices_from_real_fixture(mock_get):
    with open("tests/fixtures/rueducommerce_cpu_search.html", encoding="utf-8") as f:
        html = f.read()

    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.text = html
    mock_get.return_value = mock_response

    prices = search_cpu_prices("Ryzen 7 9800X3D")

    assert isinstance(prices, list)
    assert all(isinstance(p, float) for p in prices)
    assert prices == EXPECTED_CPU_PRICES


@patch("retailers.rueducommerce.requests.get", side_effect=Exception("network error"))
def test_search_cpu_prices_returns_empty_list_on_network_failure(mock_get):
    assert search_cpu_prices("Ryzen 7 9800X3D") == []


@patch("retailers.rueducommerce.requests.get")
def test_search_cpu_prices_returns_empty_list_on_unparseable_html(mock_get):
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.text = "<html><body>not a product listing page</body></html>"
    mock_get.return_value = mock_response

    assert search_cpu_prices("Ryzen 7 9800X3D") == []


@patch("retailers.rueducommerce.requests.get")
def test_search_cpu_prices_rejects_reconditioned_listing(mock_get):
    # Regression test for the reconditioned-card skip: a card whose title
    # genuinely matches the requested model but carries a
    # <span class="label label--reconditioned"> marker (RdC's used/
    # refurbished-listing badge, verified live and against the real fixture
    # -- it sits as a sibling of the title inside the card, not inside the
    # title text, so it can't be caught by a title-only check) must be
    # dropped so used prices don't leak into this new-market search.
    html = """
    <html><body>
    <li class="pdt-item">
      <div class="listing-product__infos">
        <span class="label label--reconditioned">Reconditionn&#233;</span>
        <h3 class="title-3">AMD Ryzen 7 9800X3D (4.7 GHz / 5.2 GHz)</h3>
      </div>
      <div class="price"><div class="new-price">434,52&#8364;</div></div>
    </li>
    <li class="pdt-item">
      <div class="listing-product__infos">
        <h3 class="title-3">AMD Ryzen 7 9800X3D (4.7 GHz / 5.2 GHz)</h3>
      </div>
      <div class="price"><div class="new-price">469,99&#8364;</div></div>
    </li>
    </body></html>
    """
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.text = html
    mock_get.return_value = mock_response

    prices = search_cpu_prices("Ryzen 7 9800X3D")

    assert prices == [469.99]


@patch("retailers.rueducommerce.requests.get")
def test_search_cpu_prices_rejects_different_x3d_sku(mock_get):
    # Regression test for the title-relevance filter: a different Ryzen X3D
    # SKU that the "Processeur"-anchored query still returns alongside the
    # requested model (verified live: 9850X3D/5800X3D/7800X3D all show up
    # for a "Processeur Ryzen 7 9800X3D" search) must not have its price
    # counted.
    html = """
    <html><body>
    <li class="pdt-item">
      <h3 class="title-3">AMD Ryzen 7 9850X3D (4.7 GHz / 5.6 GHz)</h3>
      <div class="price"><div class="new-price">489,99&#8364;</div></div>
    </li>
    <li class="pdt-item">
      <h3 class="title-3">AMD Ryzen 7 9800X3D (4.7 GHz / 5.2 GHz)</h3>
      <div class="price"><div class="new-price">469,99&#8364;</div></div>
    </li>
    </body></html>
    """
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.text = html
    mock_get.return_value = mock_response

    prices = search_cpu_prices("Ryzen 7 9800X3D")

    assert prices == [469.99]


@patch("retailers.rueducommerce.requests.get")
def test_search_cpu_prices_query_uses_processeur_prefix(mock_get):
    # Regression test for the CPU query wording: verified live that a bare
    # "Ryzen 7 9800X3D" query is ~94% noise (whole "PC" prebuilts/laptops
    # that merely contain this CPU). Only prefixing with "Processeur"
    # anchors the search to the standalone-CPU category, so the exact query
    # wording matters and is worth pinning down with a regression test.
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.text = "<html><body>not a product listing page</body></html>"
    mock_get.return_value = mock_response

    search_cpu_prices("Ryzen 7 9800X3D")

    args, kwargs = mock_get.call_args
    assert (
        args[0]
        == "https://www.rueducommerce.fr/recherche/Processeur%20Ryzen%207%209800X3D/"
    )


# 22/22 fixture cards genuinely match "RTX 5070 Ti": recomputed by running
# the filtering logic in retailers/rueducommerce.py's search_gpu_prices
# against the real fixture.
EXPECTED_GPU_PRICES = [
    1466.1, 1159.99, 1379.99, 1299.99, 1235.92, 1399.99, 1322.26, 1249.99,
    1565.89, 1219.36, 1299.99, 1379.99, 1382.92, 1299.99, 1249.99, 1299.99,
    1299.99, 1481.54, 1459.99, 1590.8, 1792.99, 1492.2,
]


@patch("retailers.rueducommerce.requests.get")
def test_search_gpu_prices_extracts_prices_from_real_fixture(mock_get):
    with open("tests/fixtures/rueducommerce_gpu_search.html", encoding="utf-8") as f:
        html = f.read()

    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.text = html
    mock_get.return_value = mock_response

    prices = search_gpu_prices("RTX 5070 Ti")

    assert isinstance(prices, list)
    assert all(isinstance(p, float) for p in prices)
    assert prices == EXPECTED_GPU_PRICES


@patch("retailers.rueducommerce.requests.get", side_effect=Exception("network error"))
def test_search_gpu_prices_returns_empty_list_on_network_failure(mock_get):
    assert search_gpu_prices("RTX 5070 Ti") == []


@patch("retailers.rueducommerce.requests.get")
def test_search_gpu_prices_returns_empty_list_on_unparseable_html(mock_get):
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.text = "<html><body>not a product listing page</body></html>"
    mock_get.return_value = mock_response

    assert search_gpu_prices("RTX 5070 Ti") == []


@patch("retailers.rueducommerce.requests.get")
def test_search_gpu_prices_rejects_reconditioned_listing(mock_get):
    # Regression test for the reconditioned-card skip applied defensively to
    # search_gpu_prices too -- see search_cpu_prices' identical test for why
    # the marker can't be caught via title text alone.
    html = """
    <html><body>
    <li class="pdt-item">
      <div class="listing-product__infos">
        <span class="label label--reconditioned">Reconditionn&#233;</span>
        <h3 class="title-3">MSI GeForce RTX 5070 Ti 16G GAMING TRIO OC</h3>
      </div>
      <div class="price"><div class="new-price">1199,00&#8364;</div></div>
    </li>
    <li class="pdt-item">
      <div class="listing-product__infos">
        <h3 class="title-3">MSI GeForce RTX 5070 Ti 16G GAMING TRIO OC</h3>
      </div>
      <div class="price"><div class="new-price">1379,99&#8364;</div></div>
    </li>
    </body></html>
    """
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.text = html
    mock_get.return_value = mock_response

    prices = search_gpu_prices("RTX 5070 Ti")

    assert prices == [1379.99]


@patch("retailers.rueducommerce.requests.get")
def test_search_gpu_prices_rejects_space_separated_near_miss_suffix(mock_get):
    # Regression test mirroring search_prices' equivalent test: a near-miss
    # tier variant (e.g. a hypothetical "RTX 5070 Ti Super") must be
    # rejected by the same suffix-boundary check, kept here as insurance
    # even though 0/22 fixture cards exercised it live.
    html = """
    <html><body>
    <li class="pdt-item">
      <h3 class="title-3">Gigabyte GeForce RTX 5070 Ti Super WINDFORCE OC 16G</h3>
      <div class="price"><div class="new-price">1699,99&#8364;</div></div>
    </li>
    <li class="pdt-item">
      <h3 class="title-3">Gigabyte GeForce RTX 5070 Ti WINDFORCE OC 16G</h3>
      <div class="price"><div class="new-price">1299,99&#8364;</div></div>
    </li>
    </body></html>
    """
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.text = html
    mock_get.return_value = mock_response

    prices = search_gpu_prices("RTX 5070 Ti")

    assert prices == [1299.99]


@patch("retailers.rueducommerce.requests.get")
def test_search_gpu_prices_query_uses_carte_graphique_prefix(mock_get):
    # Regression test for the GPU query wording: verified live that a bare
    # "RTX 5070 Ti" query is ~54% noise (whole "PC" prebuilts/gaming
    # laptops that merely contain this GPU). Only prefixing with "Carte
    # graphique" anchors the search to the standalone-GPU category, so the
    # exact query wording matters and is worth pinning down with a
    # regression test.
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.text = "<html><body>not a product listing page</body></html>"
    mock_get.return_value = mock_response

    search_gpu_prices("RTX 5070 Ti")

    args, kwargs = mock_get.call_args
    assert (
        args[0]
        == "https://www.rueducommerce.fr/recherche/Carte%20graphique%20RTX%205070%20Ti/"
    )
