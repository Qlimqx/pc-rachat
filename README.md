# pc-rachat

Outil en ligne de commande pour estimer la valeur de marché des composants d'un PC d'occasion (CPU, RAM, stockage, GPU), afin d'aider à décider combien le racheter en vue de revente.

L'estimation combine :
- **eBay Browse API** (annonces d'occasion, médiane des prix trouvés) en priorité pour le CPU et le GPU
- une **table de référence locale** (`data/reference_prices.json`) en secours si eBay ne trouve rien
- une **formule €/Go** (`data/component_rates.json`) pour la RAM et le stockage

Le résultat donne le détail par composant et un total. La marge de revente et l'ajustement selon l'état du PC restent à ta charge — l'outil n'estime que la valeur marché des pièces.

## Installation

```bash
git clone <url-du-repo>
cd pc-rachat
pip install -r requirements.txt
```

## Configuration de l'API eBay (optionnel mais recommandé)

Sans clé API, l'outil fonctionne quand même, mais uniquement avec la table de référence locale pour le CPU/GPU.

1. Va sur https://developer.ebay.com/ et crée un compte développeur (gratuit, aucune validation à attendre).
2. Dans le tableau de bord, crée une "application" en mode **Production**.
3. Récupère l'**App ID (Client ID)** et le **Cert ID (Client Secret)**.
4. Copie `.env.example` vers `.env` et renseigne tes clés :

```bash
cp .env.example .env
```

```
EBAY_CLIENT_ID=ton_app_id
EBAY_CLIENT_SECRET=ton_client_secret
```

## Utilisation

```bash
python cli.py
```

Le script te demande le modèle du CPU, la taille et le type de RAM, la taille et le type de stockage, puis le modèle du GPU (laisse vide si carte graphique intégrée). Il affiche ensuite le détail par composant et le total estimé.

## Personnaliser les données

- `data/reference_prices.json` : ajoute/ajuste les prix de secours pour les CPU/GPU que tu rachètes souvent.
- `data/component_rates.json` : ajuste les taux €/Go pour la RAM et le stockage selon le marché actuel.

## Tests

```bash
pytest -v
```

## Limites connues

- Les prix eBay sont ceux des **annonces actives** (prix demandés), pas des prix de vente confirmés — l'API eBay gratuite ne donne pas accès aux prix de vente réels sans demande d'accès restreint.
- Pas de scraping leboncoin (bloqué par leur protection anti-bot et contraire à leurs CGU).
- Pas de coefficient d'état du PC (esthétique, usure) ni de calcul de marge automatique — ces décisions restent manuelles.
- Pas de cache du token eBay, et pas de distinction entre "eBay n'a rien trouvé" et "l'appel à eBay a échoué" (identifiants invalides, panne réseau, quota dépassé) : dans les deux cas, l'outil bascule silencieusement sur la table de référence locale sans le signaler.
