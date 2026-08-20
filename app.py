import os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, render_template, request

import cli as cli_helpers
import estimator
import sourcing

load_dotenv()

app = Flask(__name__)
DATA_DIR = Path(__file__).parent / "data"
CPU_MODELS = cli_helpers.load_json(DATA_DIR / "cpu_models.json")
GPU_MODELS = cli_helpers.load_json(DATA_DIR / "gpu_models.json")


@app.route("/", methods=["GET", "POST"])
def index():
    result = None
    buy_grid = None
    sell_grid = None
    new_pc_price = None
    similar_used_result = None
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
            sell_tiers = cli_helpers.load_json(DATA_DIR / "sell_tiers.json")
            buy_margin = cli_helpers.load_json(DATA_DIR / "buy_margin.json")

            used_search_fn = cli_helpers.make_ebay_search_fn(client_id, client_secret)
            new_pc_search_fns = sourcing.make_new_pc_search_fn(client_id, client_secret)
            ram_search_fns = sourcing.make_ram_search_fn(client_id, client_secret)
            storage_search_fns = sourcing.make_storage_search_fn(client_id, client_secret)
            cpu_search_fns = sourcing.make_cpu_search_fn()
            gpu_search_fns = sourcing.make_gpu_search_fn()
            similar_used_search_fn = cli_helpers.make_similar_used_search_fn(client_id, client_secret)
            ram_used_search_fn = cli_helpers.make_ebay_used_ram_fn(client_id, client_secret)
            storage_used_search_fn = cli_helpers.make_ebay_used_storage_fn(client_id, client_secret)

            # estimate_pc, estimate_new_pc_price and estimate_similar_used_price
            # each do their own independent network searches -- run them
            # concurrently instead of one after the other so a single
            # request's wall time is bounded by the slowest of the three,
            # not their sum.
            with ThreadPoolExecutor(max_workers=3) as executor:
                result_future = executor.submit(
                    estimator.estimate_pc,
                    cpu_model=cpu_model,
                    ram_go=ram_go,
                    ram_type=ram_type,
                    storage_go=storage_go,
                    storage_type=storage_type,
                    gpu_model=gpu_model,
                    ebay_search_fn=used_search_fn,
                    reference_prices=reference_prices,
                    component_rates=component_rates,
                    ram_search_fns=ram_search_fns,
                    storage_search_fns=storage_search_fns,
                    cpu_search_fns=cpu_search_fns,
                    gpu_search_fns=gpu_search_fns,
                    ram_used_search_fn=ram_used_search_fn,
                    storage_used_search_fn=storage_used_search_fn,
                )
                new_pc_future = executor.submit(
                    estimator.estimate_new_pc_price, cpu_model, gpu_model, new_pc_search_fns
                )
                similar_used_future = executor.submit(
                    estimator.estimate_similar_used_price,
                    cpu_model, ram_go, ram_type, storage_go, storage_type, gpu_model, similar_used_search_fn,
                )
                result = result_future.result()
                new_pc_result = new_pc_future.result()
                similar_used_result = similar_used_future.result()
            if new_pc_result is not None:
                new_pc_price = new_pc_result["value"]
                sell_grid = estimator.estimate_sell_grid(new_pc_price, sell_tiers, result["total"])
                buy_grid = estimator.estimate_buy_grid(
                    sell_grid[0]["price"], buy_tiers, buy_margin["min_margin_pct"]
                )

    return render_template(
        "index.html",
        result=result,
        buy_grid=buy_grid,
        sell_grid=sell_grid,
        new_pc_price=new_pc_price,
        similar_used_result=similar_used_result,
        error=error,
        form_values=form_values,
        cpu_models=CPU_MODELS,
        gpu_models=GPU_MODELS,
    )


if __name__ == "__main__":
    app.run(debug=True)
