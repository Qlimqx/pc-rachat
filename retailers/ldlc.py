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


# Suffix qualifiers that, when they immediately follow a matched model number,
# mark a different, typically pricier variant rather than the base model --
# e.g. a "RTX 5070 Ti Super" listing must not match a "RTX 5070 Ti" query.
# Same list as materiel_net.py/pccomponentes.py's _title_matches_model.
_SUFFIX_QUALIFIERS = ("ti", "super", "xt", "xtx", "x3d")


def _title_matches_model(title, model):
    """Check whether a product's title genuinely refers to `model`.

    LDLC's search has no relevance filtering of its own -- verified live for
    two components not covered by this file's original noise research
    (Ryzen 7 9800X3D / RTX 5070 Ti): a "Carte graphique GTX 1650 Super" query
    returned wrong GPUs entirely (RTX 3070 Ti, RTX 4070 SUPER, even a
    5399,95EUR RTX 5090), several used ("Occasion") listings counted as if
    they were new, and non-GPU accessories (GPU brackets, vertical-mount
    kits) that merely live in the same site category. A "Processeur
    i5-10400F" query similarly returned a spread of unrelated i5 generations
    (i5-14600K, i5-12400F, i5-13600K, ...) and several "Reconditionné"
    laptops that happen to contain an i5 CPU. None of the RTX 5070 Ti/Ryzen
    7 9800X3D noise levels documented below generalize to every possible
    model a user might search, so every search_cpu_prices/search_gpu_prices
    result is now checked against this filter instead of trusting LDLC's
    own (apparently unranked/fuzzy) result set at face value.

    Mirrors materiel_net.py's version: LDLC's title lives in a clean,
    structured `h3.title-3` element (verified live -- consistent spacing,
    no "RTX5070Ti"-style collapse), so a plain substring check is enough,
    no whitespace-tolerant regex needed. A match is rejected if the title
    contains "occasion" (used listing, must not count as a new-market
    price), if the character right after the match is alphanumeric with no
    separating space (a concatenated suffix), or if the first word after it
    is one of _SUFFIX_QUALIFIERS (e.g. "Ti", "Super") -- otherwise accepted.
    """
    title_norm = title.lower()
    if "occasion" in title_norm:
        return False
    model_norm = model.lower().strip()
    start = title_norm.find(model_norm)
    if start == -1:
        return False
    end = start + len(model_norm)
    tail = title_norm[end:]
    if tail and tail[0].isalnum():
        return False
    next_word = re.match(r"\s+([a-z0-9]+)", tail)
    if next_word and next_word.group(1) in _SUFFIX_QUALIFIERS:
        return False
    return True


def _search(query, title_filter=None):
    try:
        url = SEARCH_URL.format(query=requests.utils.quote(query))
        response = requests.get(url, headers=HEADERS, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        prices = []
        for card in soup.select("li.pdt-item"):
            if title_filter is not None:
                title_el = card.select_one("h3.title-3")
                if title_el is None or not title_filter(title_el.get_text(strip=True)):
                    continue
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


def search_cpu_prices(cpu_model):
    # Tried a bare model name first (e.g. "Ryzen 7 9800X3D"): alongside 3
    # genuine standalone CPU listings, it also pulled in 2 whole prebuilt
    # PCs ("LDLC PC11 BBBG" at 3949,95EUR, "LDLC PC BBBG" at 3699,95EUR) that
    # merely include this CPU -- verified live against ldlc.com, and those
    # two outliers would badly skew a median computed over only 5 results.
    # Prefixing with "Processeur" (e.g. "Processeur Ryzen 7 9800X3D") drops
    # both prebuilt PCs and returns only the 3 genuine standalone CPU
    # listings -- verified live against ldlc.com.
    #
    # The "Processeur" anchor alone isn't enough for every model, though --
    # see _title_matches_model's docstring for a second, unrelated CPU
    # (i5-10400F) where LDLC's own search returned a spread of wrong i5
    # generations and reconditioned laptops instead of raising "no results".
    # title_filter catches that regardless of which CPU is searched.
    return _search(f"Processeur {cpu_model}", title_filter=lambda title: _title_matches_model(title, cpu_model))


def search_gpu_prices(gpu_model):
    # Tried a bare model name first (e.g. "RTX 5070 Ti"): alongside genuine
    # standalone GPU listings, ~43% of results were laptops that merely
    # include this GPU (e.g. "ASUS ROG Zephyrus G14 GA403WR-DR4W", "MSI
    # Vector 16 HX AI A2XWHG-472FR") -- verified live against ldlc.com.
    # Prefixing with "Carte graphique" (e.g. "Carte graphique RTX 5070 Ti")
    # drops all laptops; the remaining noise for THIS model was low enough
    # (~22%, 6/27 near-miss non-Ti "RTX 5070" cards) that the median wasn't
    # affected -- but see _title_matches_model's docstring for a different
    # GPU (GTX 1650 Super) where the same query pattern returned wrong GPUs
    # entirely, used listings, and non-GPU accessories, which a bare noise
    # percentage judgment on one model can't catch. title_filter is applied
    # to every query regardless, not just the ones where noise was observed.
    return _search(f"Carte graphique {gpu_model}", title_filter=lambda title: _title_matches_model(title, gpu_model))
