from cli import prompt_float, prompt_choice, format_result


def test_prompt_float_parses_valid_number(monkeypatch):
    monkeypatch.setattr("builtins.input", lambda _: "16")
    assert prompt_float("RAM (Go) : ") == 16.0


def test_prompt_float_accepts_comma_decimal(monkeypatch):
    monkeypatch.setattr("builtins.input", lambda _: "1,5")
    assert prompt_float("Go : ") == 1.5


def test_prompt_float_retries_on_invalid_input(monkeypatch, capsys):
    responses = iter(["abc", "16"])
    monkeypatch.setattr("builtins.input", lambda _: next(responses))

    result = prompt_float("RAM (Go) : ")

    assert result == 16.0
    assert "nombre valide" in capsys.readouterr().out


def test_prompt_choice_accepts_valid_option(monkeypatch):
    monkeypatch.setattr("builtins.input", lambda _: "ddr4")
    assert prompt_choice("Type RAM : ", ["ddr3", "ddr4", "ddr5"]) == "ddr4"


def test_prompt_choice_is_case_insensitive(monkeypatch):
    monkeypatch.setattr("builtins.input", lambda _: "DDR4")
    assert prompt_choice("Type RAM : ", ["ddr3", "ddr4", "ddr5"]) == "ddr4"


def test_prompt_choice_retries_on_invalid_option(monkeypatch, capsys):
    responses = iter(["ddr7", "ddr4"])
    monkeypatch.setattr("builtins.input", lambda _: next(responses))

    result = prompt_choice("Type RAM : ", ["ddr3", "ddr4", "ddr5"])

    assert result == "ddr4"
    assert "ddr3, ddr4, ddr5" in capsys.readouterr().out


def test_format_result_shows_all_components_and_total():
    result = {
        "breakdown": {
            "cpu": {"value": 55.0, "method": "médiane sur 3 annonces eBay"},
            "ram": {"value": 32.0, "method": "formule €/Go"},
            "storage": {"value": 25.6, "method": "formule €/Go"},
            "gpu": {"value": 110.0, "method": "médiane sur 3 annonces eBay"},
        },
        "total": 222.6,
        "missing": [],
    }

    output = format_result(result)

    assert "CPU : 55.00€ (médiane sur 3 annonces eBay)" in output
    assert "RAM : 32.00€ (formule €/Go)" in output
    assert "Stockage : 25.60€ (formule €/Go)" in output
    assert "GPU : 110.00€ (médiane sur 3 annonces eBay)" in output
    assert "Total estimé : 222.60€" in output
    assert "incomplète" not in output


def test_format_result_flags_missing_components():
    result = {
        "breakdown": {
            "cpu": None,
            "ram": {"value": 32.0, "method": "formule €/Go"},
            "storage": {"value": 25.6, "method": "formule €/Go"},
            "gpu": None,
        },
        "total": 57.6,
        "missing": ["cpu", "gpu"],
    }

    output = format_result(result)

    assert "CPU : prix inconnu" in output
    assert "GPU : prix inconnu" in output
    assert "estimation incomplète" in output
    assert "cpu, gpu" in output


def test_format_result_omits_gpu_line_details_when_no_gpu_given():
    result = {
        "breakdown": {
            "cpu": {"value": 55.0, "method": "table de référence"},
            "ram": {"value": 32.0, "method": "formule €/Go"},
            "storage": {"value": 25.6, "method": "formule €/Go"},
            "gpu": None,
        },
        "total": 112.6,
        "missing": [],
    }

    output = format_result(result)

    assert "GPU : non renseigné" in output
    assert "estimation incomplète" not in output


from cli import format_pricing_grid


def test_format_pricing_grid_renders_sell_and_buy_tiers():
    sell_grid = [
        {"pct": 0.10, "price": 100.0},
        {"pct": 0.30, "price": 300.0},
    ]
    buy_grid = [
        {"max_price": 40.0, "emoji": "🔥", "label": "Très bonne affaire", "is_last": False},
        {"max_price": 100.0, "emoji": "❌", "label": "Je passe", "is_last": True},
    ]

    output = format_pricing_grid(1000.0, sell_grid, buy_grid)

    assert "Prix neuf équivalent estimé : 1000.00€" in output
    assert "neuf -10% : 100.00€" in output
    assert "neuf -30% : 300.00€" in output
    assert "jusqu'à 40.00€ 🔥 Très bonne affaire" in output
    assert "au-delà de 100.00€ ❌ Je passe" in output


from cli import format_similar_used_price, make_similar_used_search_fn


def test_format_similar_used_price_renders_value_and_method():
    result = format_similar_used_price(
        {"value": 480.0, "method": "médiane sur 3 annonces d'occasion similaires"}
    )

    assert result == "Configs d'occasion similaires : 480.00€ (médiane sur 3 annonces d'occasion similaires)"


def test_format_similar_used_price_handles_none():
    result = format_similar_used_price(None)

    assert result == "Configs d'occasion similaires : aucune annonce comparable trouvée."


def test_make_ebay_used_ram_fn_returns_empty_list_without_credentials():
    from cli import make_ebay_used_ram_fn

    search_fn = make_ebay_used_ram_fn(None, None)

    assert search_fn(16, "ddr4") == []


def test_make_ebay_used_ram_fn_calls_ebay_client_with_credentials():
    from unittest.mock import patch

    from cli import make_ebay_used_ram_fn

    with patch("cli.ebay_client.search_used_ram_prices") as mock_search:
        mock_search.return_value = [90.0, 100.0]
        search_fn = make_ebay_used_ram_fn("id", "secret")

        result = search_fn(16, "ddr4")

        assert result == [90.0, 100.0]
        mock_search.assert_called_once_with(16, "ddr4", "id", "secret")


def test_make_ebay_used_storage_fn_returns_empty_list_without_credentials():
    from cli import make_ebay_used_storage_fn

    search_fn = make_ebay_used_storage_fn(None, None)

    assert search_fn(512, "ssd") == []


def test_make_ebay_used_storage_fn_calls_ebay_client_with_credentials():
    from unittest.mock import patch

    from cli import make_ebay_used_storage_fn

    with patch("cli.ebay_client.search_used_storage_prices") as mock_search:
        mock_search.return_value = [30.0, 40.0]
        search_fn = make_ebay_used_storage_fn("id", "secret")

        result = search_fn(512, "ssd")

        assert result == [30.0, 40.0]
        mock_search.assert_called_once_with(512, "ssd", "id", "secret")


def test_make_similar_used_search_fn_returns_empty_list_without_credentials():
    search_fn = make_similar_used_search_fn(None, None)

    assert search_fn("cpu", 16, "ddr4", 512, "ssd", "gpu") == []


def test_make_similar_used_search_fn_calls_ebay_client_with_credentials():
    from unittest.mock import patch

    with patch("cli.ebay_client.search_similar_used_pc_prices") as mock_search:
        mock_search.return_value = [450.0, 480.0]
        search_fn = make_similar_used_search_fn("id", "secret")

        result = search_fn("i5-10400F", 16, "ddr4", 512, "ssd", "GTX 1650 Super")

        assert result == [450.0, 480.0]
        mock_search.assert_called_once_with(
            "i5-10400F", 16, "ddr4", 512, "ssd", "GTX 1650 Super", "id", "secret"
        )
