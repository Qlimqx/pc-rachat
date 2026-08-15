import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

import ebay_client
import estimator
import sourcing

DATA_DIR = Path(__file__).parent / "data"


def prompt_float(question):
    while True:
        raw = input(question).strip().replace(",", ".")
        try:
            return float(raw)
        except ValueError:
            print("Merci d'entrer un nombre valide.")


def prompt_choice(question, choices):
    choices_lower = [c.lower() for c in choices]
    while True:
        raw = input(question).strip().lower()
        if raw in choices_lower:
            return raw
        print(f"Merci de choisir parmi : {', '.join(choices)}")


LABELS = {"cpu": "CPU", "ram": "RAM", "storage": "Stockage", "gpu": "GPU"}


def format_result(result):
    lines = []
    for key in ["cpu", "ram", "storage", "gpu"]:
        entry = result["breakdown"].get(key)
        label = LABELS[key]
        if entry is not None:
            lines.append(f"{label} : {entry['value']:.2f}€ ({entry['method']})")
        elif key == "gpu" and key not in result["missing"]:
            lines.append(f"{label} : non renseigné")
        else:
            lines.append(f"{label} : prix inconnu ⚠")

    lines.append("")
    lines.append(f"Total estimé : {result['total']:.2f}€")

    if result["missing"]:
        lines.append(
            f"⚠ estimation incomplète — composants inconnus : {', '.join(result['missing'])}"
        )

    return "\n".join(lines)


def load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def make_ebay_search_fn(client_id, client_secret):
    if not client_id or not client_secret:
        return lambda model, category: []

    def real_ebay_search(model, category):
        prices = ebay_client.search_component_price(model, category, client_id, client_secret)
        return prices if prices else []

    return real_ebay_search


def format_pricing_grid(new_pc_price, buy_grid, resale_target):
    lines = [f"Prix neuf équivalent estimé : {new_pc_price:.2f}€", "", "Grille d'achat :"]
    for tier in buy_grid:
        if tier["is_last"]:
            lines.append(f"  au-delà de {tier['max_price']:.2f}€ {tier['emoji']} {tier['label']}")
        else:
            lines.append(f"  jusqu'à {tier['max_price']:.2f}€ {tier['emoji']} {tier['label']}")
    lines.append("")
    lines.append(
        f"Prix de revente visé : {resale_target['min']:.2f}€ – {resale_target['max']:.2f}€"
    )
    return "\n".join(lines)


def main():
    # On Windows, stdout is sometimes attached to a legacy codepage (e.g. cp1252)
    # instead of UTF-8 — particularly when output is piped/redirected. Without
    # this, printing characters like "⚠" or "€" raises UnicodeEncodeError and
    # crashes the CLI. Force UTF-8 output when the stream supports reconfiguring.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")

    load_dotenv()
    client_id = os.environ.get("EBAY_CLIENT_ID")
    client_secret = os.environ.get("EBAY_CLIENT_SECRET")

    if not client_id or not client_secret:
        print("(clé API eBay non configurée — utilisation de la table de référence uniquement)\n")

    reference_prices = load_json(DATA_DIR / "reference_prices.json")
    component_rates = load_json(DATA_DIR / "component_rates.json")
    buy_tiers = load_json(DATA_DIR / "buy_tiers.json")
    resale_config = load_json(DATA_DIR / "resale_target.json")
    ebay_search_fn = make_ebay_search_fn(client_id, client_secret)
    new_pc_search_fns = sourcing.make_new_pc_search_fn(client_id, client_secret)
    ram_search_fns = sourcing.make_ram_search_fn(client_id, client_secret)
    storage_search_fns = sourcing.make_storage_search_fn(client_id, client_secret)
    cpu_search_fns = sourcing.make_cpu_search_fn()
    gpu_search_fns = sourcing.make_gpu_search_fn()

    print("=== Estimation de rachat PC ===\n")
    cpu_model = input("Modèle CPU (ex: i5-10400) : ").strip()
    ram_go = prompt_float("RAM (Go) : ")
    ram_type = prompt_choice("Type RAM (ddr3/ddr4/ddr5) : ", ["ddr3", "ddr4", "ddr5"])
    storage_go = prompt_float("Stockage (Go) : ")
    storage_type = prompt_choice("Type stockage (hdd/ssd/nvme) : ", ["hdd", "ssd", "nvme"])
    gpu_model = input("Modèle GPU (laisser vide si carte intégrée) : ").strip()

    result = estimator.estimate_pc(
        cpu_model=cpu_model,
        ram_go=ram_go,
        ram_type=ram_type,
        storage_go=storage_go,
        storage_type=storage_type,
        gpu_model=gpu_model,
        ebay_search_fn=ebay_search_fn,
        reference_prices=reference_prices,
        component_rates=component_rates,
        ram_search_fns=ram_search_fns,
        storage_search_fns=storage_search_fns,
        cpu_search_fns=cpu_search_fns,
        gpu_search_fns=gpu_search_fns,
    )

    new_pc_result = estimator.estimate_new_pc_price(cpu_model, gpu_model, new_pc_search_fns)
    print()
    if new_pc_result is not None:
        resale_target = estimator.estimate_resale_target(new_pc_result["value"], resale_config)
        buy_grid = estimator.estimate_buy_grid(resale_target["max"], buy_tiers)
        print(format_pricing_grid(new_pc_result["value"], buy_grid, resale_target))
    else:
        print("Grille d'achat non disponible — aucun PC neuf comparable trouvé.")

    print("\n" + format_result(result))


if __name__ == "__main__":
    main()
