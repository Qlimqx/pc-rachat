import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

import ebay_client
import estimator

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
    ebay_search_fn = make_ebay_search_fn(client_id, client_secret)

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
    )

    print("\n" + format_result(result))


if __name__ == "__main__":
    main()
