from unittest.mock import patch, Mock
from urllib.parse import unquote

from retailers.pccomponentes import search_prices


EXPECTED_PRICES = [1291.2, 1297.8, 1264.83, 1242.4, 2710.19, 1548.39, 1465.3]


@patch("retailers.pccomponentes.requests.get")
def test_search_prices_extracts_prices_from_real_fixture(mock_get):
    with open("tests/fixtures/pccomponentes_search.html", encoding="utf-8") as f:
        html = f.read()

    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.text = html
    mock_get.return_value = mock_response

    prices = search_prices("Ryzen 7 5700X", "RTX 4060")

    assert isinstance(prices, list)
    assert all(isinstance(p, float) for p in prices)
    assert prices == EXPECTED_PRICES


@patch("retailers.pccomponentes.requests.get", side_effect=Exception("network error"))
def test_search_prices_returns_empty_list_on_network_failure(mock_get):
    assert search_prices("Ryzen 7 5700X", "RTX 4060") == []


@patch("retailers.pccomponentes.requests.get")
def test_search_prices_returns_empty_list_on_unparseable_html(mock_get):
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.text = "<html><body>not a product listing page</body></html>"
    mock_get.return_value = mock_response

    assert search_prices("Ryzen 7 5700X", "RTX 4060") == []


@patch("retailers.pccomponentes.requests.get")
def test_search_prices_query_includes_both_cpu_and_gpu_model(mock_get):
    # Unlike LDLC (strict AND-matching search that chokes on combined
    # CPU+GPU queries), PcComponentes' search is Algolia-backed and returns
    # highly relevant complete-PC results when both the CPU and GPU model
    # are included together (verified via live research: "Ryzen 7 5700X RTX
    # 4060" returned 7 matching PC builds containing both parts). This locks
    # in that, unlike ldlc.py, the CPU model is NOT dropped from the query.
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.text = "<html><body>not a product listing page</body></html>"
    mock_get.return_value = mock_response

    search_prices("Ryzen 7 5700X", "RTX 4060")

    requested_url = mock_get.call_args[0][0]
    decoded_url = unquote(requested_url)

    assert "Ryzen 7 5700X" in decoded_url
    assert "RTX 4060" in decoded_url
    assert decoded_url.startswith("https://www.pccomponentes.fr/search?query=")


from retailers.pccomponentes import search_ram_prices, search_storage_prices


EXPECTED_RAM_PRICES = [
    128.88, 121.0, 220.73, 306.08, 163.78, 221.45, 221.45, 197.99, 124.99,
    639.0, 162.44, 158.99, 574.96, 755.51, 151.99, 124.0, 358.88, 240.61,
    240.14, 926.24, 106.6, 125.35, 143.99, 163.0, 177.08, 134.99, 352.89,
    161.53, 244.48, 171.91, 269.26, 236.91, 217.19, 182.04, 221.45, 221.45,
    221.45, 221.45, 221.45, 221.45,
]

EXPECTED_STORAGE_PRICES = [
    109.48, 112.0, 88.69, 88.99, 132.03, 88.0, 161.44, 112.96, 100.0,
    139.79, 824.74, 76.98, 113.99, 199.12, 100.0, 86.99, 126.8, 134.99,
    160.19, 76.0, 359.1, 124.99, 231.19, 79.98, 122.62, 98.19, 101.99,
    108.36, 147.19, 80.98, 105.35, 182.77, 121.02, 1192.25, 91.29, 113.99,
    100.99, 94.99, 85.99, 1072.43,
]


@patch("retailers.pccomponentes.requests.get")
def test_search_ram_prices_extracts_prices_from_real_fixture(mock_get):
    with open("tests/fixtures/pccomponentes_ram_search.html", encoding="utf-8") as f:
        html = f.read()

    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.text = html
    mock_get.return_value = mock_response

    prices = search_ram_prices(16, "ddr4")

    assert isinstance(prices, list)
    assert all(isinstance(p, float) for p in prices)
    assert prices == EXPECTED_RAM_PRICES


@patch("retailers.pccomponentes.requests.get", side_effect=Exception("network error"))
def test_search_ram_prices_returns_empty_list_on_network_failure(mock_get):
    assert search_ram_prices(16, "ddr4") == []


@patch("retailers.pccomponentes.requests.get")
def test_search_ram_prices_query_contains_size_and_type(mock_get):
    # Locks in the constructed query so a future edit to the f-string in
    # search_ram_prices can't silently regress without a test catching it.
    # Verified live: "16Go DDR4" returned 40/40 genuine RAM module listings
    # (Corsair, G.Skill, Patriot, Samsung, etc.) with no unrelated noise, so
    # no extra anchor term (unlike LDLC's "RAM" prefix) is needed here.
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.text = "<html><body>not a product listing page</body></html>"
    mock_get.return_value = mock_response

    search_ram_prices(16, "ddr4")

    requested_url = mock_get.call_args[0][0]
    decoded_url = unquote(requested_url)

    assert "16Go" in decoded_url
    assert "ddr4" in decoded_url
    assert decoded_url.startswith("https://www.pccomponentes.fr/search?query=")


@patch("retailers.pccomponentes.requests.get")
def test_search_storage_prices_extracts_prices_from_real_fixture(mock_get):
    with open("tests/fixtures/pccomponentes_storage_search.html", encoding="utf-8") as f:
        html = f.read()

    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.text = html
    mock_get.return_value = mock_response

    prices = search_storage_prices(512, "ssd")

    assert isinstance(prices, list)
    assert all(isinstance(p, float) for p in prices)
    assert prices == EXPECTED_STORAGE_PRICES


@patch("retailers.pccomponentes.requests.get", side_effect=Exception("network error"))
def test_search_storage_prices_returns_empty_list_on_network_failure(mock_get):
    assert search_storage_prices(512, "ssd") == []


@patch("retailers.pccomponentes.requests.get")
def test_search_storage_prices_query_contains_size_and_type(mock_get):
    # Locks in the constructed query so a future edit to the f-string in
    # search_storage_prices can't silently regress without a test catching
    # it. Verified live: "512Go SSD" returned 40/40 results, the large
    # majority genuine standalone SSD listings (a couple of pre-built PCs
    # that happen to ship a 512Go SSD slip in too, same tradeoff LDLC's
    # storage search has), with no case-sensitivity effect observed.
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.text = "<html><body>not a product listing page</body></html>"
    mock_get.return_value = mock_response

    search_storage_prices(512, "ssd")

    requested_url = mock_get.call_args[0][0]
    decoded_url = unquote(requested_url)

    assert "512Go" in decoded_url
    assert "ssd" in decoded_url
    assert decoded_url.startswith("https://www.pccomponentes.fr/search?query=")


from retailers.pccomponentes import search_cpu_prices, search_gpu_prices


EXPECTED_CPU_PRICES = [446.18, 435.0, 485.85]

EXPECTED_GPU_PRICES = [
    1159.99, 1193.02, 1618.27, 1269.99, 1299.99, 1299.99, 1688.46, 1399.99,
    1369.99, 1259.99, 1338.83, 1349.99, 1169.99, 1189.99, 1311.83, 1299.99,
    1299.99, 1199.99, 1279.99, 1470.92, 1600.22, 1479.99, 1399.99, 1311.05,
    1604.46, 1397.75, 1526.15, 1343.9, 1834.99, 1696.12, 1678.99, 1578.56,
    1380.42,
]


@patch("retailers.pccomponentes.requests.get")
def test_search_cpu_prices_extracts_prices_from_real_fixture(mock_get):
    with open("tests/fixtures/pccomponentes_cpu_search.html", encoding="utf-8") as f:
        html = f.read()

    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.text = html
    mock_get.return_value = mock_response

    prices = search_cpu_prices("Ryzen 7 9800X3D")

    assert isinstance(prices, list)
    assert all(isinstance(p, float) for p in prices)
    assert prices == EXPECTED_CPU_PRICES


@patch("retailers.pccomponentes.requests.get", side_effect=Exception("network error"))
def test_search_cpu_prices_returns_empty_list_on_network_failure(mock_get):
    assert search_cpu_prices("Ryzen 7 9800X3D") == []


@patch("retailers.pccomponentes.requests.get")
def test_search_cpu_prices_query_contains_anchor_and_model(mock_get):
    # Locks in the constructed query so a future edit to the f-string in
    # search_cpu_prices can't silently regress without a test catching it.
    # Verified live: bare "Ryzen 7 9800X3D" returned 33 results but only
    # 2/33 were genuine standalone CPU listings (31 were prebuilt PCs that
    # merely include this CPU). Prefixing with "Processeur" drops all 31
    # prebuilt PCs, leaving only 3 results (2 genuine + 1 near-miss for the
    # different "9850X3D" SKU) -- a median-invariance check confirmed that
    # near-miss barely moves the median (446.18 with it vs 440.59 without,
    # a 1.3% difference), so the anchored query is used as-is.
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.text = "<html><body>not a product listing page</body></html>"
    mock_get.return_value = mock_response

    search_cpu_prices("Ryzen 7 9800X3D")

    requested_url = mock_get.call_args[0][0]
    decoded_url = unquote(requested_url)

    assert decoded_url == "https://www.pccomponentes.fr/search?query=Processeur Ryzen 7 9800X3D"


@patch("retailers.pccomponentes.requests.get")
def test_search_gpu_prices_extracts_prices_from_real_fixture(mock_get):
    with open("tests/fixtures/pccomponentes_gpu_search.html", encoding="utf-8") as f:
        html = f.read()

    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.text = html
    mock_get.return_value = mock_response

    prices = search_gpu_prices("RTX 5070 Ti")

    assert isinstance(prices, list)
    assert all(isinstance(p, float) for p in prices)
    assert prices == EXPECTED_GPU_PRICES


@patch("retailers.pccomponentes.requests.get", side_effect=Exception("network error"))
def test_search_gpu_prices_returns_empty_list_on_network_failure(mock_get):
    assert search_gpu_prices("RTX 5070 Ti") == []


@patch("retailers.pccomponentes.requests.get")
def test_search_gpu_prices_query_contains_anchor_and_model(mock_get):
    # Locks in the constructed query so a future edit to the f-string in
    # search_gpu_prices can't silently regress without a test catching it.
    # Verified live: bare "RTX 5070 Ti" returned 40 results but ~53%
    # (21/40) were laptops/prebuilt desktops that merely include this GPU.
    # Prefixing with "Carte graphique" drops every laptop and desktop --
    # all 33 results are genuine standalone RTX 5070 Ti graphics cards, 0%
    # noise.
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.text = "<html><body>not a product listing page</body></html>"
    mock_get.return_value = mock_response

    search_gpu_prices("RTX 5070 Ti")

    requested_url = mock_get.call_args[0][0]
    decoded_url = unquote(requested_url)

    assert decoded_url == "https://www.pccomponentes.fr/search?query=Carte graphique RTX 5070 Ti"
