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
