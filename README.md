# pc-rachat

Outil en ligne de commande pour estimer la valeur de marché des composants d'un PC d'occasion (CPU, RAM, stockage, GPU), afin d'aider à décider combien le racheter en vue de revente.

L'estimation combine :
- pour le CPU et le GPU : une recherche de **prix neuf** en priorité (médiane sur 7 revendeurs français — LDLC, PcComponentes, Materiel.net, TopAchat, Grosbill, Rue du Commerce, Amazon), avec repli sur l'**eBay Browse API** (annonces d'occasion, médiane des prix trouvés) si aucun revendeur ne trouve le modèle neuf, puis sur une **table de référence locale** (`data/reference_prices.json`) en tout dernier recours
- pour la RAM et le stockage : une recherche de **prix marché** (médiane sur eBay + les mêmes 7 revendeurs), avec repli sur une **formule €/Go** (`data/component_rates.json`) si aucune source ne trouve de résultat

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

### Interface web (en local)

```bash
python app.py
```

Lance un serveur Flask en local (par défaut sur `http://127.0.0.1:5000`). Ouvre l'URL dans ton navigateur : tu retrouves les mêmes champs que la version en ligne de commande (CPU, RAM, stockage, GPU), avec en plus la grille d'achat et le prix de revente visé si l'outil trouve un PC neuf comparable.

## Déploiement sur Render

L'appli web (`app.py`) est prête à être déployée sur [Render](https://render.com/) :

1. Connecte ton compte Render à GitHub et sélectionne ce repo.
2. Render détecte automatiquement `render.yaml` (Blueprint) — sinon, configure manuellement :
   - Build command : `pip install -r requirements.txt`
   - Start command : `gunicorn app:app`
3. Dans les paramètres du service Render, ajoute tes variables d'environnement : `EBAY_CLIENT_ID` et `EBAY_CLIENT_SECRET` (les mêmes valeurs que dans ton `.env` local — voir la section eBay ci-dessus).
4. Déploie. Render te donne une URL publique (`https://<nom-du-service>.onrender.com`).

Sans ces variables configurées sur Render, l'appli fonctionne quand même pour le détail par composant (table de référence locale), mais la recherche eBay est désactivée jusqu'à ce que les clés soient ajoutées.

## Personnaliser les données

- `data/reference_prices.json` : ajoute/ajuste les prix de secours pour les CPU/GPU que tu rachètes souvent.
- `data/component_rates.json` : ajuste les taux €/Go de secours pour la RAM et le stockage, utilisés uniquement si aucune des 8 sources de prix marché ne trouve de résultat.

## Tests

```bash
pytest -v
```

## Limites connues

- Les prix eBay sont ceux des **annonces actives** (prix demandés), pas des prix de vente confirmés — l'API eBay gratuite ne donne pas accès aux prix de vente réels sans demande d'accès restreint.
- Pas de scraping leboncoin (bloqué par leur protection anti-bot et contraire à leurs CGU).
- Pas de coefficient d'état du PC (esthétique, usure) ni de calcul de marge automatique — ces décisions restent manuelles.
- Pas de cache du token eBay, et pas de distinction entre "eBay n'a rien trouvé" et "l'appel à eBay a échoué" (identifiants invalides, panne réseau, quota dépassé) : dans les deux cas, l'outil bascule silencieusement sur la table de référence locale sans le signaler.
- La grille d'achat et l'objectif de revente reposent sur un prix de "PC neuf équivalent" obtenu en interrogeant 7 sites marchands (`retailers/`) plus eBay ; si aucune de ces 8 sources ne renvoie de résultat exploitable, la grille est tout simplement omise du résultat.
- Ces 7 sites marchands sont scrapés sans API officielle, sur des pages dont la structure peut changer à tout moment : comme pour eBay, si l'un d'eux cesse de fonctionner suite à une refonte de son site, l'outil bascule silencieusement sur les autres sources disponibles, sans message d'erreur distinct.
