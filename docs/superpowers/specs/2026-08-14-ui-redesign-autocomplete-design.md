# pc-rachat — Refonte visuelle & autocomplétion CPU/GPU — Design

## Contexte et objectif

L'interface web (`app.py` + `templates/index.html`) est actuellement du HTML brut sans style, avec des champs CPU/GPU en texte libre pur. Cette évolution ajoute :

1. Un vrai design visuel (style "Tech Dashboard")
2. Une autocomplétion pour les champs CPU et GPU : liste déroulante des modèles courants, tout en gardant la possibilité de taper une valeur qui n'y figure pas

Le CLI (`cli.py`) n'est pas concerné par cette évolution — l'autocomplétion n'a de sens que dans un navigateur.

## Style visuel

Palette "Tech Dashboard" (validée par maquette) :
- Fond principal : bleu-gris foncé `#1a2233`
- Fond des champs/cartes : `#0f1521`
- Bordures : `#2d3a52`
- Texte principal : `#f1f5f9`, texte secondaire : `#94a3b8`
- Accent (boutons, focus, badges) : orange/ambre `#f59e0b`

Implémentation :
- CSS intégré directement dans `templates/index.html` (balise `<style>`), pas de fichier CSS séparé ni de build step — cohérent avec le reste du projet (pas de dépendance frontend)
- Pas de framework JS. Le seul comportement dynamique (autocomplétion) repose sur `<datalist>`, natif au navigateur
- Restylage de : formulaire (labels, champs, boutons), grille d'achat (les paliers 🔥✅🟢🟠🔴❌ comme des badges colorés plutôt que du texte brut), prix de revente, détail par composant, messages d'erreur/d'avertissement

## Autocomplétion CPU/GPU

- Deux nouveaux champs `<input type="text" list="cpu-models">` / `<input type="text" list="gpu-models">`, chacun associé à une `<datalist>` correspondante remplie côté serveur
- Comportement natif du navigateur : liste filtrée au fur et à mesure de la frappe, sélection possible au clic, mais la saisie libre reste acceptée telle quelle (le champ reste un simple texte, pas une contrainte de valeur)
- Deux nouveaux fichiers de données, éditables comme le reste du projet :
  - `data/cpu_models.json` — liste plate de ~50-80 noms de CPU parmi les plus courants en occasion (Intel Core et AMD Ryzen des générations les plus croisées, pas de couverture exhaustive)
  - `data/gpu_models.json` — même principe pour les GPU (Nvidia GeForce et AMD Radeon les plus courants)
- `app.py` charge ces deux fichiers et les passe au template (`cpu_models`, `gpu_models`) à chaque affichage du formulaire (GET et POST)
- Ces listes sont indépendantes de `data/reference_prices.json` : elles ne servent qu'à l'autocomplétion, pas au calcul de prix. Un modèle suggéré dans la liste n'a pas besoin d'avoir une entrée dans `reference_prices.json` — le calcul de prix continue de fonctionner exactement comme avant (eBay puis fallback table de référence puis "prix inconnu" si rien ne correspond)

## Hors périmètre

- Pas d'autocomplétion côté CLI
- Pas de lien entre les listes d'autocomplétion et les prix de référence (deux mécanismes séparés)
- Pas de couverture exhaustive de tous les modèles existants (liste courte, modèles les plus fréquents seulement)
- Pas de framework JS ni de build step
