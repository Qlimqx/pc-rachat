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


def _search(query):
    try:
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


def search_prices(cpu_model, gpu_model):
    # LDLC's search does strict AND-matching; including both CPU and GPU model
    # returns almost nothing (verified during research), so we search by GPU
    # + a generic "PC gamer" term instead
    return _search(f"PC gamer {gpu_model}")


def search_ram_prices(ram_go, ram_type):
    # Tried "{go}Go {type}" (e.g. "16Go DDR4") first: it returns real RAM
    # listings but mixed with unrelated matches (DDR3 sticks, NAS appliances,
    # refurbished laptops that merely mention "16 Go" RAM in their specs) --
    # verified live against ldlc.com. Prefixing with "RAM" (e.g.
    # "RAM 16Go DDR4") keeps the search anchored to RAM products only --
    # every result on the first page is an actual memory module, though not
    # all match the exact capacity/speed, same tradeoff as the GPU search
    # above. Case doesn't affect relevance -- "RAM 16Go ddr4" and
    # "RAM 16Go DDR4" return byte-identical result sets, verified live
    # against ldlc.com -- so ram_type is passed through as-is.
    return _search(f"RAM {ram_go}Go {ram_type}")


def search_storage_prices(storage_go, storage_type):
    # Tried "{go}Go {type}" (e.g. "512Go SSD") first: on ldlc.com this
    # returns almost exclusively refurbished laptops/desktops that happen to
    # ship with a 512Go SSD, not standalone drives -- useless for pricing a
    # storage upgrade. "SSD {go}Go" gave the identical result (LDLC's search
    # appears order-insensitive). Switching to "Disque SSD {go}Go" (e.g.
    # "Disque SSD 512Go") returns genuine standalone SSD listings (Samsung,
    # Kingston, Crucial, WD, Patriot, etc.) across a range of capacities --
    # verified live against ldlc.com. Case doesn't affect relevance either
    # (verified live), so storage_type is passed through as-is.
    return _search(f"Disque {storage_type} {storage_go}Go")
