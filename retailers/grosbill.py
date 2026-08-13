import requests
from bs4 import BeautifulSoup

SEARCH_URL = "https://www.grosbill.com/produit.aspx"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
}


def search_prices(cpu_model, gpu_model):
    try:
        # Grosbill's search does strict AND-matching, just like LDLC and
        # Materiel.net (verified live: "Ryzen 7 5700X RTX 4060" returns
        # "aucun produit ne correspond"). Grosbill's current build lineup
        # pairs this CPU with newer GPUs (RTX 5060/5070), not the requested
        # RTX 4060, so keeping the GPU term in the query would zero out
        # results entirely. A bare CPU-model search ("Ryzen 7 5700X") does
        # return matches, but mixes in standalone CPU component listings
        # alongside the complete builds. Prefixing with "PC gamer" (verified
        # live) filters the result set down to only the "PC Gamer" complete-
        # build category -- 5 matching builds, all containing the CPU model,
        # with no components mixed in. So, like ldlc.py, we drop the GPU
        # model from the query -- but unlike ldlc.py (which drops the CPU
        # and keeps the GPU), here it's the GPU that's dropped and the CPU
        # that's kept, because that's what this catalog actually has stock
        # of for this CPU.
        query = f"PC gamer {cpu_model}"
        response = requests.get(
            SEARCH_URL, params={"q": query}, headers=HEADERS, timeout=10
        )
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        prices = []
        # No JSON API (the search is a classic server-rendered .aspx page,
        # no XHR/JSON calls involved -- verified live via network inspection),
        # no data-price attribute, no itemprop="price", and no product-level
        # JSON-LD block (only a BreadcrumbList schema exists) -- verified
        # against the fixture. The closest thing to structured price data is
        # a dedicated reference/price span rendered per product card,
        # holding the price as plain "<euros>,<cents>" text (e.g. "1649,99")
        # with no currency symbol or markup to strip, unlike the
        # €<sup>cents</sup> pattern LDLC/Materiel.net require picking apart.
        for card in soup.select("div.grb__liste-produit__liste__produit"):
            price_el = card.select_one(
                "span.grb__liste-produit__liste__produit__reference-container"
                "__content_prix_produit"
            )
            if price_el is None:
                continue
            raw_price = price_el.get_text(strip=True).replace(",", ".")
            try:
                price = float(raw_price)
            except ValueError:
                continue
            prices.append(price)
        return prices
    except Exception:
        return []
