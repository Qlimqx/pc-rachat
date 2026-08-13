import re

import requests
from bs4 import BeautifulSoup

SEARCH_URL = "https://www.pccomponentes.fr/search?query={query}"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
}


def _extract_price(text):
    match = re.search(r"[\d]+(?:[.,]\d+)?", text.replace("\xa0", "").replace(" ", ""))
    if not match:
        return None
    return float(match.group().replace(",", "."))


def _price_text(price_el):
    # PcComponentes renders prices in French/Spanish numeric format, e.g.
    # <span data-e2e="price-card">1.291,20€</span>: "." is the thousands
    # separator and "," is the decimal separator. _extract_price() only
    # understands a single separator character as the decimal point, so
    # "1.291,20" would be misparsed as 1.291 (dropping the ",20" cents).
    # Strip the thousands-separator dots first so only the decimal comma
    # remains for _extract_price to convert.
    return price_el.get_text(strip=True).replace(".", "")


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
        for card in soup.select("a[data-product-price]"):
            price_el = card.select_one('span[data-e2e="price-card"]')
            if price_el is None:
                continue
            price = _extract_price(_price_text(price_el))
            if price is not None:
                prices.append(price)
        return prices
    except Exception:
        return []
