import re

import requests
from bs4 import BeautifulSoup

SEARCH_URL = "https://www.materiel.net/recherche/{query}/"
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
    # Materiel.net (same corporate group / platform as LDLC) renders prices as
    # e.g. <span class="o-product__price">1&nbsp;349€<sup>96</sup></span>, i.e.
    # euros and cents with no separating punctuation between them once tags
    # are stripped, so get_text() alone would drop the cents (yielding "1349"
    # instead of "1349.96"). Pull the cents out of <sup> separately and
    # rebuild a "<euros>,<cents>" string that _extract_price can parse cleanly.
    sup = price_el.find("sup")
    cents = sup.get_text(strip=True) if sup else "00"
    if sup is not None:
        sup.extract()
    euro_digits = re.sub(r"\D", "", price_el.get_text())
    return f"{euro_digits},{cents}"


def search_prices(cpu_model, gpu_model):
    try:
        # Verified live: Materiel.net's search does strict AND-matching, just
        # like LDLC (both are part of the LDLC Group and share the same
        # search platform). Combining the CPU and GPU model returns almost
        # nothing ("Ryzen 7 5700X RTX 4060" -> 3 unrelated products: an
        # adapter cable and a motherboard). Searching by GPU model alone is
        # too narrow too (only 2 exact-match products). "PC gamer {gpu}"
        # returns a full page of complete gaming-PC listings (208 results),
        # mirroring the query shape already validated for LDLC, so we reuse
        # it here and never leak the CPU model into the query.
        query = f"PC gamer {gpu_model}"
        url = SEARCH_URL.format(query=requests.utils.quote(query))
        response = requests.get(url, headers=HEADERS, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        prices = []
        for card in soup.select("li.c-products-list__item"):
            # No structured price attribute or JSON-LD block exists on this
            # page (verified live via DOM inspection), so we fall back to
            # parsing the display text. Promo items render two price spans
            # inside .c-product__prices: the struck-through original price
            # (class o-product__cut-price) and the current discounted price
            # (class o-product__price--promo). Non-promo items render just
            # one plain .o-product__price span. Excluding .o-product__cut-price
            # picks the right one in both cases with a single selector.
            price_el = card.select_one(".o-product__price:not(.o-product__cut-price)")
            if price_el is None:
                continue
            price = _extract_price(_price_text(price_el))
            if price is not None:
                prices.append(price)
        return prices
    except Exception:
        return []
