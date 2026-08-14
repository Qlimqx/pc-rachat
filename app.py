import os
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, render_template, request

import cli as cli_helpers
import estimator
import sourcing

load_dotenv()

app = Flask(__name__)
DATA_DIR = Path(__file__).parent / "data"


@app.route("/", methods=["GET", "POST"])
def index():
    result = None
    buy_grid = None
    resale_target = None
    new_pc_price = None
    error = None
    form_values = None

    if request.method == "POST":
        form_values = request.form
        try:
            cpu_model = request.form.get("cpu_model", "").strip()
            ram_go = float(request.form.get("ram_go", "").replace(",", "."))
            ram_type = request.form.get("ram_type", "").strip().lower()
            storage_go = float(request.form.get("storage_go", "").replace(",", "."))
            storage_type = request.form.get("storage_type", "").strip().lower()
            gpu_model = request.form.get("gpu_model", "").strip()
        except ValueError:
            error = "Merci d'entrer des nombres valides pour la RAM et le stockage."
        else:
            client_id = os.environ.get("EBAY_CLIENT_ID")
            client_secret = os.environ.get("EBAY_CLIENT_SECRET")

            reference_prices = cli_helpers.load_json(DATA_DIR / "reference_prices.json")
            component_rates = cli_helpers.load_json(DATA_DIR / "component_rates.json")
            buy_tiers = cli_helpers.load_json(DATA_DIR / "buy_tiers.json")
            resale_config = cli_helpers.load_json(DATA_DIR / "resale_target.json")

            used_search_fn = cli_helpers.make_ebay_search_fn(client_id, client_secret)
            new_pc_search_fns = sourcing.make_new_pc_search_fn(client_id, client_secret)

            result = estimator.estimate_pc(
                cpu_model=cpu_model,
                ram_go=ram_go,
                ram_type=ram_type,
                storage_go=storage_go,
                storage_type=storage_type,
                gpu_model=gpu_model,
                ebay_search_fn=used_search_fn,
                reference_prices=reference_prices,
                component_rates=component_rates,
            )

            new_pc_result = estimator.estimate_new_pc_price(cpu_model, gpu_model, new_pc_search_fns)
            if new_pc_result is not None:
                new_pc_price = new_pc_result["value"]
                buy_grid = estimator.estimate_buy_grid(new_pc_price, buy_tiers)
                resale_target = estimator.estimate_resale_target(new_pc_price, resale_config)

    return render_template(
        "index.html",
        result=result,
        buy_grid=buy_grid,
        resale_target=resale_target,
        new_pc_price=new_pc_price,
        error=error,
        form_values=form_values,
    )


if __name__ == "__main__":
    app.run(debug=True)
