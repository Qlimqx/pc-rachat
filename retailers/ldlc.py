import re

import requests
from bs4 import BeautifulSoup

SEARCH_URL = "https://www.ldlc.com/recherche/{query}/"
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
    # LDLC renders prices as e.g. <div class="price">1&nbsp;349€<sup>96</sup></div>
    # i.e. euros and cents with no separating punctuation between them once the
    # tags are stripped, so get_text() alone would drop the cents (yielding
    # "1349" instead of "1349.96"). Pull the cents out of <sup> separately and
    # rebuild a "<euros>,<cents>" string that _extract_price can parse cleanly.
    sup = price_el.find("sup")
    cents = sup.get_text(strip=True) if sup else "00"
    if sup is not None:
        sup.extract()
    euro_digits = re.sub(r"\D", "", price_el.get_text())
    return f"{euro_digits},{cents}"


def search_prices(cpu_model, gpu_model):
    try:
        query = f"{cpu_model} {gpu_model}"
        url = SEARCH_URL.format(query=requests.utils.quote(query))
        response = requests.get(url, headers=HEADERS, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        prices = []
        for card in soup.select("li.pdt-item"):
            price_el = card.select_one(".price .price")
            if price_el is None:
                continue
            price = _extract_price(_price_text(price_el))
            if price is not None:
                prices.append(price)
        return prices
    except Exception:
        return []
