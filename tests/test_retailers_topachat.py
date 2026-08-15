import json
from unittest.mock import patch, Mock

from retailers.topachat import (
    search_prices,
    search_ram_prices,
    search_storage_prices,
    search_cpu_prices,
    search_gpu_prices,
)


EXPECTED_PRICES = [
    1449.99, 1249.99, 1519.99, 1549.99, 1199.99, 1299.99, 1399.99, 1229.99,
    1369.99, 1779.99, 1629.99, 1299.99, 1949.99, 1999.99, 999.99,
]


@patch("retailers.topachat.requests.get")
def test_search_prices_extracts_prices_from_real_fixture(mock_get):
    with open("tests/fixtures/topachat_search.html", encoding="utf-8") as f:
        fixture_json = json.load(f)

    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = fixture_json
    mock_get.return_value = mock_response

    prices = search_prices("Ryzen 7 5700X", "RTX 4060")

    assert isinstance(prices, list)
    assert all(isinstance(p, float) for p in prices)
    assert prices == EXPECTED_PRICES


@patch("retailers.topachat.requests.get", side_effect=Exception("network error"))
def test_search_prices_returns_empty_list_on_network_failure(mock_get):
    assert search_prices("Ryzen 7 5700X", "RTX 4060") == []


@patch("retailers.topachat.requests.get")
def test_search_prices_returns_empty_list_on_unparseable_html(mock_get):
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.side_effect = ValueError("not json")
    mock_get.return_value = mock_response

    assert search_prices("Ryzen 7 5700X", "RTX 4060") == []


@patch("retailers.topachat.requests.get")
def test_search_prices_query_includes_both_cpu_and_gpu_model(mock_get):
    # TopAchat's search handles combined CPU+GPU queries well (verified live:
    # "Ryzen 7 5700X RTX 4060" returned a "PC Gamer" category where 13 of the
    # first 15 sampled builds actually contain a Ryzen 7 5700X). This locks
    # in that both models are sent together as the "terms" query param,
    # unlike LDLC which has to drop the CPU model.
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"result": {"document": {"categories": []}}}
    mock_get.return_value = mock_response

    search_prices("Ryzen 7 5700X", "RTX 4060")

    _, kwargs = mock_get.call_args
    assert kwargs["params"] == {"terms": "Ryzen 7 5700X RTX 4060"}


RAM_EXPECTED_PRICES = [
    159.98, 159.99, 339.98, 429.99, 599.99, 154.99, 289.99, 132.99, 318.99,
    139.99, 152.99, 104.99, 199.99, 612.98, 279.99,
]

STORAGE_EXPECTED_PRICES = [144.99, 144.99, 149.99, 174.99, 169.99]


@patch("retailers.topachat.requests.get")
def test_search_ram_prices_extracts_prices_from_real_fixture(mock_get):
    with open("tests/fixtures/topachat_ram_search.html", encoding="utf-8") as f:
        fixture_json = json.load(f)

    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = fixture_json
    mock_get.return_value = mock_response

    prices = search_ram_prices(16, "ddr4")

    assert isinstance(prices, list)
    assert all(isinstance(p, float) for p in prices)
    assert prices == RAM_EXPECTED_PRICES


@patch("retailers.topachat.requests.get", side_effect=Exception("network error"))
def test_search_ram_prices_returns_empty_list_on_network_failure(mock_get):
    assert search_ram_prices(16, "ddr4") == []


@patch("retailers.topachat.requests.get")
def test_search_ram_prices_query_and_category_label(mock_get):
    # Locks in both the exact query wording and the category-label matching:
    # TopAchat groups RAM under a category literally named after the DDR
    # generation ("DDR4"), not the plan's originally-guessed "Mémoire" --
    # verified live. This test would catch a regression back to that wrong
    # guess, or to a different query shape (e.g. a "RAM" prefix like LDLC
    # needs), since the fixture's "DDR4" category would then go unmatched
    # and prices would come back empty.
    with open("tests/fixtures/topachat_ram_search.html", encoding="utf-8") as f:
        fixture_json = json.load(f)

    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = fixture_json
    mock_get.return_value = mock_response

    prices = search_ram_prices(16, "ddr4")

    _, kwargs = mock_get.call_args
    assert kwargs["params"] == {"terms": "16Go ddr4"}
    assert prices == RAM_EXPECTED_PRICES


@patch("retailers.topachat.requests.get")
def test_search_storage_prices_extracts_prices_from_real_fixture(mock_get):
    with open("tests/fixtures/topachat_storage_search.html", encoding="utf-8") as f:
        fixture_json = json.load(f)

    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = fixture_json
    mock_get.return_value = mock_response

    prices = search_storage_prices(512, "ssd")

    assert isinstance(prices, list)
    assert all(isinstance(p, float) for p in prices)
    assert prices == STORAGE_EXPECTED_PRICES


@patch("retailers.topachat.requests.get", side_effect=Exception("network error"))
def test_search_storage_prices_returns_empty_list_on_network_failure(mock_get):
    assert search_storage_prices(512, "ssd") == []


@patch("retailers.topachat.requests.get")
def test_search_storage_prices_query_and_category_label(mock_get):
    # Locks in both the exact query wording and the category-label matching:
    # TopAchat groups standalone SSDs under a category literally named "SSD"
    # (5 of ~500+ total results across the search), not the plan's
    # originally-guessed "Disque dur / SSD" -- verified live. This test
    # would catch a regression back to that wrong guess, since the fixture's
    # "SSD" category would then go unmatched and prices would come back
    # empty, or a switch to a noisier query shape that pulls in the laptop
    # categories ("PC Portable", "PC Portable Gamer", "Portable Mac") that
    # dominate this same search.
    with open("tests/fixtures/topachat_storage_search.html", encoding="utf-8") as f:
        fixture_json = json.load(f)

    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = fixture_json
    mock_get.return_value = mock_response

    prices = search_storage_prices(512, "ssd")

    _, kwargs = mock_get.call_args
    assert kwargs["params"] == {"terms": "512Go ssd"}
    assert prices == STORAGE_EXPECTED_PRICES


CPU_EXPECTED_PRICES = [469.99, 479.99]

GPU_EXPECTED_PRICES = [
    1299.99, 1299.99, 1379.99, 1379.99, 1299.99, 1249.99, 1159.99, 1249.99,
    1399.99, 1299.99, 1299.99, 1399.99, 1499.99, 1469.99, 1329.99,
]


@patch("retailers.topachat.requests.get")
def test_search_cpu_prices_extracts_prices_from_real_fixture(mock_get):
    with open("tests/fixtures/topachat_cpu_search.html", encoding="utf-8") as f:
        fixture_json = json.load(f)

    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = fixture_json
    mock_get.return_value = mock_response

    prices = search_cpu_prices("Ryzen 7 9800X3D")

    assert isinstance(prices, list)
    assert all(isinstance(p, float) for p in prices)
    assert prices == CPU_EXPECTED_PRICES


@patch("retailers.topachat.requests.get", side_effect=Exception("network error"))
def test_search_cpu_prices_returns_empty_list_on_network_failure(mock_get):
    assert search_cpu_prices("Ryzen 7 9800X3D") == []


@patch("retailers.topachat.requests.get")
def test_search_cpu_prices_query_and_category_label(mock_get):
    # Locks in both the exact query (bare CPU model, no "Processeur" prefix
    # baked into the query itself -- unlike LDLC/Materiel.net which need that
    # word in the search terms, TopAchat's category filtering does the work)
    # and the category-label matching: verified live, "Processeur" is the
    # real category label here (unlike RAM/storage above, where the guessed
    # labels were both wrong -- this one happened to match the plan's
    # starting guess). This test would catch a regression to a wrong label
    # or an unintended query-wording change, since the fixture's
    # "Processeur" category would then go unmatched and prices would come
    # back empty.
    with open("tests/fixtures/topachat_cpu_search.html", encoding="utf-8") as f:
        fixture_json = json.load(f)

    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = fixture_json
    mock_get.return_value = mock_response

    prices = search_cpu_prices("Ryzen 7 9800X3D")

    _, kwargs = mock_get.call_args
    assert kwargs["params"] == {"terms": "Ryzen 7 9800X3D"}
    assert prices == CPU_EXPECTED_PRICES


@patch("retailers.topachat.requests.get")
def test_search_gpu_prices_extracts_prices_from_real_fixture(mock_get):
    with open("tests/fixtures/topachat_gpu_search.html", encoding="utf-8") as f:
        fixture_json = json.load(f)

    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = fixture_json
    mock_get.return_value = mock_response

    prices = search_gpu_prices("RTX 5070 Ti")

    assert isinstance(prices, list)
    assert all(isinstance(p, float) for p in prices)
    assert prices == GPU_EXPECTED_PRICES


@patch("retailers.topachat.requests.get", side_effect=Exception("network error"))
def test_search_gpu_prices_returns_empty_list_on_network_failure(mock_get):
    assert search_gpu_prices("RTX 5070 Ti") == []


@patch("retailers.topachat.requests.get")
def test_search_gpu_prices_query_and_category_label(mock_get):
    # Locks in both the exact query (bare GPU model) and the category-label
    # matching: verified live, "Carte graphique" is the real category label
    # for standalone GPU listings, and it happened to match the plan's
    # starting guess (unlike RAM/storage). This test would catch a
    # regression to a wrong label or query-wording change, since the
    # fixture's "Carte graphique" category would then go unmatched and
    # prices would come back empty.
    with open("tests/fixtures/topachat_gpu_search.html", encoding="utf-8") as f:
        fixture_json = json.load(f)

    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = fixture_json
    mock_get.return_value = mock_response

    prices = search_gpu_prices("RTX 5070 Ti")

    _, kwargs = mock_get.call_args
    assert kwargs["params"] == {"terms": "RTX 5070 Ti"}
    assert prices == GPU_EXPECTED_PRICES
