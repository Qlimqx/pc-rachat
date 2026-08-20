from unittest.mock import patch

import app as flask_app_module


def test_index_get_shows_the_form():
    client = flask_app_module.app.test_client()

    response = client.get("/")

    assert response.status_code == 200
    assert "Modèle CPU".encode("utf-8") in response.data


@patch("app.sourcing.make_new_pc_search_fn")
@patch("app.cli_helpers.make_ebay_search_fn")
def test_index_post_shows_component_breakdown(mock_used_search_fn, mock_new_search_fns):
    mock_used_search_fn.return_value = lambda model, category: []
    mock_new_search_fns.return_value = [lambda cpu, gpu: []]

    client = flask_app_module.app.test_client()
    response = client.post(
        "/",
        data={
            "cpu_model": "i5-10400",
            "ram_go": "16",
            "ram_type": "ddr4",
            "storage_go": "512",
            "storage_type": "ssd",
            "gpu_model": "gtx 1660",
        },
    )

    assert response.status_code == 200
    assert "Total estimé".encode("utf-8") in response.data


@patch("app.sourcing.make_new_pc_search_fn")
@patch("app.cli_helpers.make_ebay_search_fn")
def test_index_post_shows_buy_grid_when_new_pc_price_found(mock_used_search_fn, mock_new_search_fns):
    mock_used_search_fn.return_value = lambda model, category: []
    mock_new_search_fns.return_value = [lambda cpu, gpu: [1400.0]]

    client = flask_app_module.app.test_client()
    response = client.post(
        "/",
        data={
            "cpu_model": "Ryzen 7 5700X",
            "ram_go": "16",
            "ram_type": "ddr4",
            "storage_go": "1000",
            "storage_type": "nvme",
            "gpu_model": "RTX 4060",
        },
    )

    assert response.status_code == 200
    assert "Grille d".encode("utf-8") in response.data
    assert "Prix de revente".encode("utf-8") in response.data


@patch("app.sourcing.make_new_pc_search_fn")
@patch("app.cli_helpers.make_ebay_search_fn")
def test_index_post_buy_grid_tiers_have_colored_badge_classes(mock_used_search_fn, mock_new_search_fns):
    mock_used_search_fn.return_value = lambda model, category: []
    mock_new_search_fns.return_value = [lambda cpu, gpu: [1400.0]]

    client = flask_app_module.app.test_client()
    response = client.post(
        "/",
        data={
            "cpu_model": "Ryzen 7 5700X",
            "ram_go": "16",
            "ram_type": "ddr4",
            "storage_go": "1000",
            "storage_type": "nvme",
            "gpu_model": "RTX 4060",
        },
    )

    assert response.status_code == 200
    assert 'class="tier-badge tier-badge-0"'.encode("utf-8") in response.data


@patch("app.sourcing.make_new_pc_search_fn")
@patch("app.cli_helpers.make_ebay_search_fn")
@patch("app.cli_helpers.make_similar_used_search_fn")
def test_index_post_shows_similar_used_price_when_found(
    mock_similar_search_fn, mock_used_search_fn, mock_new_search_fns
):
    mock_used_search_fn.return_value = lambda model, category: []
    mock_new_search_fns.return_value = [lambda cpu, gpu: []]
    mock_similar_search_fn.return_value = (
        lambda cpu, ram_go, ram_type, storage_go, storage_type, gpu: [450.0, 480.0]
    )

    client = flask_app_module.app.test_client()
    response = client.post(
        "/",
        data={
            "cpu_model": "i5-10400F",
            "ram_go": "16",
            "ram_type": "ddr4",
            "storage_go": "1000",
            "storage_type": "ssd",
            "gpu_model": "GTX 1650 Super",
        },
    )

    assert response.status_code == 200
    assert "Configs d'occasion similaires".encode("utf-8") in response.data
    assert "465.00€".encode("utf-8") in response.data


@patch("app.sourcing.make_new_pc_search_fn")
@patch("app.cli_helpers.make_ebay_search_fn")
def test_index_post_shows_no_similar_used_price_message_when_none_found(
    mock_used_search_fn, mock_new_search_fns
):
    mock_used_search_fn.return_value = lambda model, category: []
    mock_new_search_fns.return_value = [lambda cpu, gpu: []]

    client = flask_app_module.app.test_client()
    response = client.post(
        "/",
        data={
            "cpu_model": "i5-10400",
            "ram_go": "16",
            "ram_type": "ddr4",
            "storage_go": "512",
            "storage_type": "ssd",
            "gpu_model": "",
        },
    )

    assert response.status_code == 200
    assert "Aucune annonce comparable trouvée".encode("utf-8") in response.data


@patch("app.sourcing.make_storage_search_fn")
@patch("app.sourcing.make_ram_search_fn")
@patch("app.sourcing.make_cpu_search_fn")
@patch("app.sourcing.make_new_pc_search_fn")
@patch("app.cli_helpers.make_ebay_search_fn")
def test_index_post_clamps_sell_grid_to_component_floor(
    mock_used_search_fn,
    mock_new_search_fns,
    mock_cpu_search_fns,
    mock_ram_search_fns,
    mock_storage_search_fns,
):
    # Regression test for the raccord-de-prix issue: a component breakdown
    # total higher than a deeply discounted sell-grid tier must not produce
    # a resale target below what the parts alone are worth. CPU=900, RAM=50,
    # storage=50 -> component floor=1000.0, exactly equal to the new-PC
    # price, so every sell-grid tier (which would otherwise be strictly
    # below 1000.0) must get clamped up to 1000.0.
    mock_used_search_fn.return_value = lambda model, category: []
    mock_new_search_fns.return_value = [lambda cpu, gpu: [1000.0]]
    mock_cpu_search_fns.return_value = [lambda model: [900.0]]
    mock_ram_search_fns.return_value = [lambda ram_go, ram_type: [50.0]]
    mock_storage_search_fns.return_value = [lambda storage_go, storage_type: [50.0]]

    client = flask_app_module.app.test_client()
    response = client.post(
        "/",
        data={
            "cpu_model": "Ryzen 7 5700X",
            "ram_go": "16",
            "ram_type": "ddr4",
            "storage_go": "512",
            "storage_type": "ssd",
            "gpu_model": "",
        },
    )

    assert response.status_code == 200
    html = response.data.decode("utf-8")
    assert "Total estimé : 1000.00€" in html
    assert "neuf -10% : 1000.00€" in html
    assert "neuf -20% : 1000.00€" in html
    assert "neuf -30% : 1000.00€" in html


def test_index_post_with_invalid_number_reshows_form_with_error():
    client = flask_app_module.app.test_client()

    response = client.post(
        "/",
        data={
            "cpu_model": "i5-10400",
            "ram_go": "pas-un-nombre",
            "ram_type": "ddr4",
            "storage_go": "512",
            "storage_type": "ssd",
            "gpu_model": "",
        },
    )

    assert response.status_code == 200
    assert "Modèle CPU".encode("utf-8") in response.data


def test_index_post_with_validation_error_keeps_ram_type_selected():
    client = flask_app_module.app.test_client()

    response = client.post(
        "/",
        data={
            "cpu_model": "i5-10400",
            "ram_go": "pas-un-nombre",
            "ram_type": "ddr5",
            "storage_go": "512",
            "storage_type": "ssd",
            "gpu_model": "",
        },
    )

    assert response.status_code == 200
    html = response.data.decode("utf-8")
    assert '<option value="ddr5" selected>' in html
    assert '<option value="ddr3" selected>' not in html


def test_index_get_shows_cpu_and_gpu_datalists_with_options():
    client = flask_app_module.app.test_client()

    response = client.get("/")

    assert response.status_code == 200
    assert b'list="cpu-models"' in response.data
    assert b'list="gpu-models"' in response.data
    assert b'<datalist id="cpu-models">' in response.data
    assert b'<datalist id="gpu-models">' in response.data
    assert "Ryzen 7 5700X".encode("utf-8") in response.data
    assert "RTX 4060".encode("utf-8") in response.data


def test_index_get_includes_dark_theme_stylesheet():
    client = flask_app_module.app.test_client()

    response = client.get("/")

    assert response.status_code == 200
    assert b"<style>" in response.data
    assert b"#1a2233" in response.data
