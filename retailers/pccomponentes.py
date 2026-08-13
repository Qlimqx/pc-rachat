import requests
from bs4 import BeautifulSoup

SEARCH_URL = "https://www.pccomponentes.fr/search?query={query}"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
}


def search_prices(cpu_model, gpu_model):
    try:
        # Unlike LDLC (whose search does strict AND-matching and chokes on
        # combined CPU+GPU queries), PcComponentes' search is Algolia-backed
        # and handles both terms together fine, returning highly relevant
        # complete-PC listings. Verified live: "Ryzen 7 5700X RTX 4060"
        # returned 7 matching PC builds that actually contain both parts,
        # versus a broader "PC gamer RTX 4060" query which returned PCs
        # with unrelated CPUs. So, unlike LDLC, we keep both models.
        query = f"{cpu_model} {gpu_model}"
        url = SEARCH_URL.format(query=requests.utils.quote(query))
        response = requests.get(url, headers=HEADERS, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        prices = []
        # data-product-price is a marker attribute set only on real product
        # result links within the search grid (verified against the fixture:
        # 7 occurrences, exactly matching the 7 listed products), unlike the
        # data-testid="normal-link" attribute which is reused across many
        # unrelated UI elements (carousels, breadcrumbs, etc.) on the page.
        # It also carries the price itself as a clean, unlocalized string
        # (e.g. "1291.2"), so it can be read straight off the same element
        # without a second descendant lookup or any locale-aware parsing.
        for card in soup.select("a[data-product-price]"):
            raw_price = card.get("data-product-price")
            if raw_price is None:
                continue
            try:
                price = float(raw_price)
            except ValueError:
                continue
            prices.append(price)
        return prices
    except Exception:
        return []
