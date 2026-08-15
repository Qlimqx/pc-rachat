from unittest.mock import patch, Mock

from retailers.grosbill import (
    search_prices,
    search_ram_prices,
    search_storage_prices,
    search_cpu_prices,
    search_gpu_prices,
)


EXPECTED_PRICES = [1649.99, 1279.99, 1299.99, 1199.99, 1479.99]


@patch("retailers.grosbill.requests.get")
def test_search_prices_extracts_prices_from_real_fixture(mock_get):
    with open("tests/fixtures/grosbill_search.html", encoding="utf-8") as f:
        html = f.read()

    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.text = html
    mock_get.return_value = mock_response

    prices = search_prices("Ryzen 7 5700X", "RTX 4060")

    assert isinstance(prices, list)
    assert all(isinstance(p, float) for p in prices)
    assert prices == EXPECTED_PRICES


@patch("retailers.grosbill.requests.get", side_effect=Exception("network error"))
def test_search_prices_returns_empty_list_on_network_failure(mock_get):
    assert search_prices("Ryzen 7 5700X", "RTX 4060") == []


@patch("retailers.grosbill.requests.get")
def test_search_prices_returns_empty_list_on_unparseable_html(mock_get):
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.text = "<html><body>not a product listing page</body></html>"
    mock_get.return_value = mock_response

    assert search_prices("Ryzen 7 5700X", "RTX 4060") == []


@patch("retailers.grosbill.requests.get")
def test_search_prices_query_excludes_gpu_model(mock_get):
    # Grosbill's search does strict AND-matching, just like LDLC and
    # Materiel.net. Combining the CPU and GPU model returns zero results
    # (verified live: "Ryzen 7 5700X RTX 4060" -> "aucun produit ne
    # correspond"). Searching "PC gamer {cpu_model}" alone, however, returns
    # only the "PC Gamer" complete-build category (5 matching builds,
    # verified live), filtering out standalone CPU/GPU component listings
    # that a bare cpu_model search would also return. This locks in that the
    # GPU model is never leaked into the query, unlike ldlc.py which drops
    # the CPU model instead (Grosbill's inventory pairs this CPU with newer
    # GPUs, not the requested RTX 4060, so keeping the GPU term would zero
    # out results).
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.text = "<html><body>not a product listing page</body></html>"
    mock_get.return_value = mock_response

    search_prices("Ryzen 7 5700X", "RTX 4060")

    args, kwargs = mock_get.call_args
    assert args[0] == "https://www.grosbill.com/produit.aspx"
    assert kwargs["params"] == {"q": "PC gamer Ryzen 7 5700X"}


EXPECTED_RAM_PRICES = [
    159.99, 119.99, 109.49, 269.99, 79.99, 36.99, 139.99, 259.9, 179.99,
    92.0, 189.99, 114.99, 109.99,
]

EXPECTED_STORAGE_PRICES = [109.99, 89.99, 139.99]


@patch("retailers.grosbill.requests.get")
def test_search_ram_prices_extracts_prices_from_real_fixture(mock_get):
    with open("tests/fixtures/grosbill_ram_search.html", encoding="utf-8") as f:
        html = f.read()

    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.text = html
    mock_get.return_value = mock_response

    prices = search_ram_prices(16, "ddr4")

    assert isinstance(prices, list)
    assert all(isinstance(p, float) for p in prices)
    assert prices == EXPECTED_RAM_PRICES


@patch("retailers.grosbill.requests.get", side_effect=Exception("network error"))
def test_search_ram_prices_returns_empty_list_on_network_failure(mock_get):
    assert search_ram_prices(16, "ddr4") == []


@patch("retailers.grosbill.requests.get")
def test_search_ram_prices_returns_empty_list_on_unparseable_html(mock_get):
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.text = "<html><body>not a product listing page</body></html>"
    mock_get.return_value = mock_response

    assert search_ram_prices(16, "ddr4") == []


@patch("retailers.grosbill.requests.get")
def test_search_ram_prices_query_contains_size_and_type(mock_get):
    # Locks in the constructed query so a future edit to the f-string in
    # search_ram_prices can't silently regress without a test catching it.
    # Also guards against re-introducing a case transform (e.g. .upper()):
    # Grosbill's search is case-insensitive (verified live -- "RAM 16Go
    # ddr4" and "RAM 16Go DDR4" return the same result set), so ram_type
    # must be passed through unmodified. A bare "16Go DDR4" query (no "RAM"
    # prefix) was tried first but mixed in laptops/PCs whose spec sheet
    # merely mentions "16Go" RAM (~35% noise, verified live); the "RAM"
    # prefix anchors the search to the memory-module category.
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.text = "<html><body>not a product listing page</body></html>"
    mock_get.return_value = mock_response

    search_ram_prices(16, "ddr4")

    args, kwargs = mock_get.call_args
    assert args[0] == "https://www.grosbill.com/produit.aspx"
    assert kwargs["params"] == {"q": "RAM 16Go ddr4"}


@patch("retailers.grosbill.requests.get")
def test_search_storage_prices_extracts_prices_from_real_fixture(mock_get):
    with open("tests/fixtures/grosbill_storage_search.html", encoding="utf-8") as f:
        html = f.read()

    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.text = html
    mock_get.return_value = mock_response

    prices = search_storage_prices(512, "ssd")

    assert isinstance(prices, list)
    assert all(isinstance(p, float) for p in prices)
    assert prices == EXPECTED_STORAGE_PRICES


@patch("retailers.grosbill.requests.get", side_effect=Exception("network error"))
def test_search_storage_prices_returns_empty_list_on_network_failure(mock_get):
    assert search_storage_prices(512, "ssd") == []


@patch("retailers.grosbill.requests.get")
def test_search_storage_prices_returns_empty_list_on_unparseable_html(mock_get):
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.text = "<html><body>not a product listing page</body></html>"
    mock_get.return_value = mock_response

    assert search_storage_prices(512, "ssd") == []


@patch("retailers.grosbill.requests.get")
def test_search_storage_prices_query_contains_size_and_type(mock_get):
    # Locks in the constructed query so a future edit to the f-string in
    # search_storage_prices can't silently regress without a test catching
    # it. Also guards against re-introducing a case transform (e.g.
    # .upper()): Grosbill's search is case-insensitive (verified live), so
    # storage_type must be passed through unmodified. Note that a "Go"
    # suffix on the capacity is deliberately NOT included: with it (e.g.
    # "Disque SSD 512Go" or bare "512Go SSD"), results are dominated by
    # laptops/PCs that merely have a 512Go drive inside (verified live, up
    # to 100% noise for the bare query), drowning out standalone SSD
    # listings. Dropping "Go" entirely (e.g. "Disque SSD 512") anchors
    # tightly to standalone SSD products only (verified live: 3/3 results
    # were genuine SSD listings, zero pollution).
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.text = "<html><body>not a product listing page</body></html>"
    mock_get.return_value = mock_response

    search_storage_prices(512, "ssd")

    args, kwargs = mock_get.call_args
    assert args[0] == "https://www.grosbill.com/produit.aspx"
    assert kwargs["params"] == {"q": "Disque ssd 512"}


EXPECTED_CPU_PRICES = [479.99, 450.0]

# The bundle card ("Kit Upgrade PC" - RTX 5070Ti WF OC SFF 16Go + RM850e
# 850W Gold 3.1, 1199,00EUR) is deliberately excluded: it's a GPU+PSU kit,
# not a standalone card, even though its title contains the full GPU model
# as a substring. See _title_matches_model's docstring in retailers/grosbill.py.
EXPECTED_GPU_PRICES = [
    1379.99, 1294.99, 1399.99, 1249.99, 1379.99, 1294.99, 1329.99,
    1189.99, 1149.99, 1294.99, 1449.9, 1239.9, 1149.9, 1024.89,
]


@patch("retailers.grosbill.requests.get")
def test_search_cpu_prices_extracts_prices_from_real_fixture(mock_get):
    with open("tests/fixtures/grosbill_cpu_search.html", encoding="utf-8") as f:
        html = f.read()

    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.text = html
    mock_get.return_value = mock_response

    prices = search_cpu_prices("Ryzen 7 9800X3D")

    assert isinstance(prices, list)
    assert all(isinstance(p, float) for p in prices)
    assert prices == EXPECTED_CPU_PRICES


@patch("retailers.grosbill.requests.get", side_effect=Exception("network error"))
def test_search_cpu_prices_returns_empty_list_on_network_failure(mock_get):
    assert search_cpu_prices("Ryzen 7 9800X3D") == []


@patch("retailers.grosbill.requests.get")
def test_search_cpu_prices_returns_empty_list_on_unparseable_html(mock_get):
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.text = "<html><body>not a product listing page</body></html>"
    mock_get.return_value = mock_response

    assert search_cpu_prices("Ryzen 7 9800X3D") == []


@patch("retailers.grosbill.requests.get")
def test_search_cpu_prices_query_uses_processeur_anchor(mock_get):
    # Locks in the constructed query. A bare "Ryzen 7 9800X3D" query
    # returned 71% noise (5/7 results were "PC Gamer" prebuilts that merely
    # contain this CPU, verified live); prefixing with "Processeur" drops
    # every prebuilt (2/2 results genuine standalone CPU listings,
    # verified live). No case transform is applied -- guards against
    # re-introducing one.
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.text = "<html><body>not a product listing page</body></html>"
    mock_get.return_value = mock_response

    search_cpu_prices("Ryzen 7 9800X3D")

    args, kwargs = mock_get.call_args
    assert args[0] == "https://www.grosbill.com/produit.aspx"
    assert kwargs["params"] == {"q": "Processeur Ryzen 7 9800X3D"}


@patch("retailers.grosbill.requests.get")
def test_search_gpu_prices_extracts_prices_from_real_fixture(mock_get):
    with open("tests/fixtures/grosbill_gpu_search.html", encoding="utf-8") as f:
        html = f.read()

    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.text = html
    mock_get.return_value = mock_response

    prices = search_gpu_prices("RTX 5070 Ti")

    assert isinstance(prices, list)
    assert all(isinstance(p, float) for p in prices)
    assert prices == EXPECTED_GPU_PRICES


@patch("retailers.grosbill.requests.get", side_effect=Exception("network error"))
def test_search_gpu_prices_returns_empty_list_on_network_failure(mock_get):
    assert search_gpu_prices("RTX 5070 Ti") == []


@patch("retailers.grosbill.requests.get")
def test_search_gpu_prices_returns_empty_list_on_unparseable_html(mock_get):
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.text = "<html><body>not a product listing page</body></html>"
    mock_get.return_value = mock_response

    assert search_gpu_prices("RTX 5070 Ti") == []


@patch("retailers.grosbill.requests.get")
def test_search_gpu_prices_query_uses_carte_graphique_anchor(mock_get):
    # Locks in the constructed query. A bare "RTX 5070 Ti" query returned
    # 35% noise (prebuilt PCs, laptops, and a GPU+PSU kit bundle mixed in
    # with genuine cards, verified live); prefixing with "Carte graphique"
    # drops every prebuilt/laptop (verified live). No case transform is
    # applied -- guards against re-introducing one.
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.text = "<html><body>not a product listing page</body></html>"
    mock_get.return_value = mock_response

    search_gpu_prices("RTX 5070 Ti")

    args, kwargs = mock_get.call_args
    assert args[0] == "https://www.grosbill.com/produit.aspx"
    assert kwargs["params"] == {"q": "Carte graphique RTX 5070 Ti"}


def test_title_matches_model_rejects_bundle_kit():
    from retailers.grosbill import _title_matches_model

    assert not _title_matches_model(
        "RTX 5070Ti WF OC SFF 16Go + RM850e 850W Gold 3.1", "RTX 5070 Ti"
    )


def test_title_matches_model_tolerates_missing_space_before_suffix():
    from retailers.grosbill import _title_matches_model

    assert _title_matches_model(
        "RTX 5070Ti 16GB Overclocked Triple Fan V1", "RTX 5070 Ti"
    )


def test_title_matches_model_rejects_suffix_variant():
    from retailers.grosbill import _title_matches_model

    assert not _title_matches_model(
        "GeForce RTX 5070 Ti Super 16G GAMING TRIO OC", "RTX 5070 Ti"
    )


def test_title_matches_model_accepts_genuine_match():
    from retailers.grosbill import _title_matches_model

    assert _title_matches_model("GeForce RTX 5070 Ti 16G GAMING TRIO OC", "RTX 5070 Ti")
