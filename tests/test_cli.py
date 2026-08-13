from cli import prompt_float, prompt_choice


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
