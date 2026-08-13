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
