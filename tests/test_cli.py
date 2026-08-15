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
