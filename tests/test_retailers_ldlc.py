from unittest.mock import patch, Mock
from urllib.parse import unquote

from retailers.ldlc import (
    search_prices,
    search_ram_prices,
    search_storage_prices,
    search_cpu_prices,
    search_gpu_prices,
)


EXPECTED_PRICES = [
    1349.96, 1029.95, 949.99, 1169.95, 929.95, 1399.95, 1639.95, 1049.99,
    1469.95, 2599.95, 1299.95, 1039.95, 1549.95, 1319.95, 1149.95, 1199.95,
    1309.95, 1239.95, 1219.95, 1999.95, 1409.95, 1339.95, 1349.95, 1299.95,
    3949.95, 1849.95, 1199.95, 1599.95, 2499.95, 1999.95, 2299.95, 2299.95,
    1999.95, 1999.95, 1779.95, 1379.95, 1649.95, 1499.95, 2549.95, 2149.95,
    2149.95, 2199.95, 3699.95, 1659.95, 1899.95, 2399.95, 2699.95, 1699.95,
]


@patch("retailers.ldlc.requests.get")
def test_search_prices_extracts_prices_from_real_fixture(mock_get):
    with open("tests/fixtures/ldlc_search.html", encoding="utf-8") as f:
        html = f.read()

    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.text = html
    mock_get.return_value = mock_response

    prices = search_prices("Ryzen 7 5700X", "RTX 4060")

    assert isinstance(prices, list)
    assert all(isinstance(p, float) for p in prices)
    assert prices == EXPECTED_PRICES


@patch("retailers.ldlc.requests.get", side_effect=Exception("network error"))
def test_search_prices_returns_empty_list_on_network_failure(mock_get):
    assert search_prices("Ryzen 7 5700X", "RTX 4060") == []


@patch("retailers.ldlc.requests.get")
def test_search_prices_returns_empty_list_on_unparseable_html(mock_get):
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.text = "<html><body>not a product listing page</body></html>"
    mock_get.return_value = mock_response

    assert search_prices("Ryzen 7 5700X", "RTX 4060") == []


@patch("retailers.ldlc.requests.get")
def test_search_prices_query_excludes_cpu_model(mock_get):
    # LDLC's search does strict AND-matching, so including both the CPU and
    # GPU model in the query returns almost nothing (verified via live
    # research). This locks in that the requested URL is built from the GPU
    # model plus a generic "PC gamer" term, and never leaks the CPU model.
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
    79.95, 169.94, 129.95, 299.95, 84.95, 309.95, 429.95, 79.95, 249.95,
    259.94, 159.95, 179.95, 176.95, 599.95, 129.95, 619.94, 163.94, 149.95,
    339.95, 318.95, 149.95, 299.95, 299.95, 119.95, 154.95, 99.95, 619.94,
    179.95, 159.95, 266.96, 249.95, 89.95, 139.95, 299.95, 139.95, 599.95,
    219.95, 95.95, 108.95, 182.95, 169.95, 381.95, 159.95, 94.95, 213.95,
    152.85, 179.95, 109.95,
]

EXPECTED_STORAGE_PRICES = [
    259.95, 499.95, 209.95, 269.95, 149.95, 399.95, 279.95, 129.95, 139.95,
    94.95, 749.95, 279.95, 99.95, 144.95, 269.95, 339.95, 529.95, 899.95,
    599.95, 219.95, 139.95, 199.95, 1449.95, 379.95, 369.95, 219.95, 44.95,
    79.95, 199.95, 329.95, 299.95, 239.95, 269.95, 229.95, 139.95, 239.95,
    197.95, 1199.95, 129.95, 1399.95, 169.95, 279.95, 299.95, 579.95,
    1299.95, 239.95, 1349.95, 1899.95,
]


@patch("retailers.ldlc.requests.get")
def test_search_ram_prices_extracts_prices_from_real_fixture(mock_get):
    with open("tests/fixtures/ldlc_ram_search.html", encoding="utf-8") as f:
        html = f.read()

    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.text = html
    mock_get.return_value = mock_response

    prices = search_ram_prices(16, "ddr4")

    assert isinstance(prices, list)
    assert all(isinstance(p, float) for p in prices)
    assert prices == EXPECTED_RAM_PRICES


@patch("retailers.ldlc.requests.get", side_effect=Exception("network error"))
def test_search_ram_prices_returns_empty_list_on_network_failure(mock_get):
    assert search_ram_prices(16, "ddr4") == []


@patch("retailers.ldlc.requests.get")
def test_search_ram_prices_query_contains_size_and_type(mock_get):
    # Locks in the constructed query so a future edit to the f-string in
    # search_ram_prices can't silently regress without a test catching it.
    # Also guards against re-introducing a case transform (e.g. .upper()):
    # LDLC's search is case-insensitive (verified live -- "RAM 16Go ddr4"
    # and "RAM 16Go DDR4" return identical results), so ram_type must be
    # passed through unmodified.
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.text = "<html><body>not a product listing page</body></html>"
    mock_get.return_value = mock_response

    search_ram_prices(16, "ddr4")

    requested_url = mock_get.call_args[0][0]
    decoded_url = unquote(requested_url)

    assert "RAM" in decoded_url
    assert "16Go" in decoded_url
    assert "ddr4" in decoded_url


@patch("retailers.ldlc.requests.get")
def test_search_storage_prices_extracts_prices_from_real_fixture(mock_get):
    with open("tests/fixtures/ldlc_storage_search.html", encoding="utf-8") as f:
        html = f.read()

    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.text = html
    mock_get.return_value = mock_response

    prices = search_storage_prices(512, "ssd")

    assert isinstance(prices, list)
    assert all(isinstance(p, float) for p in prices)
    assert prices == EXPECTED_STORAGE_PRICES


@patch("retailers.ldlc.requests.get", side_effect=Exception("network error"))
def test_search_storage_prices_returns_empty_list_on_network_failure(mock_get):
    assert search_storage_prices(512, "ssd") == []


@patch("retailers.ldlc.requests.get")
def test_search_storage_prices_query_contains_size_and_type(mock_get):
    # Locks in the constructed query so a future edit to the f-string in
    # search_storage_prices can't silently regress without a test catching
    # it. Also guards against re-introducing a case transform (e.g.
    # .upper()): LDLC's search is case-insensitive (verified live), so
    # storage_type must be passed through unmodified.
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.text = "<html><body>not a product listing page</body></html>"
    mock_get.return_value = mock_response

    search_storage_prices(512, "ssd")

    requested_url = mock_get.call_args[0][0]
    decoded_url = unquote(requested_url)

    assert "Disque" in decoded_url
    assert "ssd" in decoded_url
    assert "512Go" in decoded_url


EXPECTED_CPU_PRICES = [479.95, 499.95, 431.95]

EXPECTED_GPU_PRICES = [
    1199.95, 1339.95, 1079.95, 1279.95, 1599.95, 1499.95, 1529.95, 1329.95,
    1329.95, 1399.95, 1279.95, 1399.95, 1429.95, 1329.95, 1349.95, 1429.95,
    1151.96, 1151.96, 1196.96, 1399.95, 1329.95, 839.95, 899.95, 849.95,
    764.96, 764.96, 979.95,
]


@patch("retailers.ldlc.requests.get")
def test_search_cpu_prices_extracts_prices_from_real_fixture(mock_get):
    with open("tests/fixtures/ldlc_cpu_search.html", encoding="utf-8") as f:
        html = f.read()

    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.text = html
    mock_get.return_value = mock_response

    prices = search_cpu_prices("Ryzen 7 9800X3D")

    assert isinstance(prices, list)
    assert all(isinstance(p, float) for p in prices)
    assert prices == EXPECTED_CPU_PRICES


@patch("retailers.ldlc.requests.get", side_effect=Exception("network error"))
def test_search_cpu_prices_returns_empty_list_on_network_failure(mock_get):
    assert search_cpu_prices("Ryzen 7 9800X3D") == []


@patch("retailers.ldlc.requests.get")
def test_search_cpu_prices_query_contains_anchor_and_model(mock_get):
    # Locks in the constructed query so a future edit to the f-string in
    # search_cpu_prices can't silently regress without a test catching it.
    # Live research found that a bare model name (no "Processeur" anchor)
    # lets whole prebuilt PCs ("LDLC PC11 BBBG", "LDLC PC BBBG" -- both
    # thousands of euros) leak into the results, which would badly skew a
    # CPU price median upward -- verified live against ldlc.com. Also guards
    # against re-introducing a case transform: cpu_model must be passed
    # through unmodified.
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.text = "<html><body>not a product listing page</body></html>"
    mock_get.return_value = mock_response

    search_cpu_prices("Ryzen 7 9800X3D")

    requested_url = mock_get.call_args[0][0]
    decoded_url = unquote(requested_url)

    assert "Processeur" in decoded_url
    assert "Ryzen 7 9800X3D" in decoded_url


@patch("retailers.ldlc.requests.get")
def test_search_gpu_prices_extracts_prices_from_real_fixture(mock_get):
    with open("tests/fixtures/ldlc_gpu_search.html", encoding="utf-8") as f:
        html = f.read()

    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.text = html
    mock_get.return_value = mock_response

    prices = search_gpu_prices("RTX 5070 Ti")

    assert isinstance(prices, list)
    assert all(isinstance(p, float) for p in prices)
    assert prices == EXPECTED_GPU_PRICES


@patch("retailers.ldlc.requests.get", side_effect=Exception("network error"))
def test_search_gpu_prices_returns_empty_list_on_network_failure(mock_get):
    assert search_gpu_prices("RTX 5070 Ti") == []


@patch("retailers.ldlc.requests.get")
def test_search_gpu_prices_query_contains_anchor_and_model(mock_get):
    # Locks in the constructed query so a future edit to the f-string in
    # search_gpu_prices can't silently regress without a test catching it.
    # Live research found that dropping the "Carte graphique" anchor lets
    # laptops that merely contain the GPU (e.g. "ASUS ROG Zephyrus G14
    # GA403WR-DR4W") leak in as ~43% of results -- worse pollution than with
    # the anchor -- verified live against ldlc.com. Also guards against
    # re-introducing a case transform: gpu_model must be passed through
    # unmodified.
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.text = "<html><body>not a product listing page</body></html>"
    mock_get.return_value = mock_response

    search_gpu_prices("RTX 5070 Ti")

    requested_url = mock_get.call_args[0][0]
    decoded_url = unquote(requested_url)

    assert "Carte graphique" in decoded_url
    assert "RTX 5070 Ti" in decoded_url
