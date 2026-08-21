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


# Suffix qualifiers that, when they immediately follow a matched model number,
# mark a different, typically pricier variant rather than the base model --
# e.g. a "RTX 5070 Ti Super" listing must not match a "RTX 5070 Ti" query.
# Same list as pccomponentes.py/rueducommerce.py/amazon.py's
# _title_matches_model. Not exercised by either captured fixture (the GPU
# near-miss found live was the opposite direction -- plain "RTX 5070" cards
# missing "Ti", already rejected because the substring itself isn't found --
# see _title_matches_model docstring), but kept for the same reason
# pccomponentes.py keeps it: cheap insurance against a future query/page
# where a real superset variant does show up.
_SUFFIX_QUALIFIERS = ("ti", "super", "xt", "xtx", "x3d")


def _title_matches_model(title, model):
    """Check whether a product's title refers to `model`.

    Materiel.net's card markup exposes a clean, structured title via
    <h2 class="c-product__title"> right alongside the price -- same shape as
    PcComponentes' data-product-name, so this mirrors
    pccomponentes.py's _title_matches_model rather than
    rueducommerce.py/amazon.py's whitespace-tolerant regex version (verified
    against both fixtures: model names appear as exact, consistently-spaced
    substrings, no "RTX5070Ti" vs "RTX 5070 Ti" spacing collapse).

    Two kinds of noise were found live, verified against the CPU and GPU
    fixtures, that a plain substring match alone would NOT reject:

    1. Bundle/kit listings. The CPU query for "Ryzen 7 9800X3D" returned a
       "MSI MAG B850 TOMAHAWK MAX WIFI + AMD Ryzen 7 9800X3D (Version tray)"
       kit at 739,90EUR (a motherboard+CPU bundle, category "Kit upgrade PC")
       whose title contains the full requested CPU model as a verbatim,
       unextended substring -- so this is a genuine substring/superset
       relationship (a different *product*, not just a different model),
       not caught by the suffix-qualifier check below. Materiel.net's own
       kit-naming convention always joins components with " + ", which no
       standalone CPU/GPU listing in either fixture contains, so titles
       with " + " are rejected outright.
    2. Used listings. Both the CPU and GPU queries returned genuine
       same-model listings suffixed "- Occasion" (e.g. "AMD Ryzen 7 9800X3D
       (4.7 GHz) - Version tray - Occasion" at 431,95EUR; 4 of the GPU
       query's 21 genuine RTX 5070 Ti results were "- Occasion"). This
       function backs search_cpu_prices/search_gpu_prices specifically,
       which exist to source *new* market prices ahead of the eBay occasion
       fallback (see estimator.py) -- letting used listings leak in here
       would undermine that new/occasion split, so titles containing the
       word "occasion" are rejected too.

    On top of those two, the same suffix-boundary logic as
    pccomponentes.py's _title_matches_model still applies: a match is
    rejected if the character right after it is alphanumeric with no
    separating space (a concatenated "RTX5070TiSuper"), or if the first word
    after it, once whitespace is skipped, is one of _SUFFIX_QUALIFIERS (e.g.
    "Ti", "Super"). Anything else after a space is unrelated trailing product
    text and still counts as a match.
    """
    title_norm = title.lower()
    if " + " in title_norm:
        return False
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
        for card in soup.select("li.c-products-list__item"):
            if title_filter is not None:
                title_el = card.select_one(".c-product__title")
                if title_el is None or not title_filter(title_el.get_text(strip=True)):
                    continue
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


def _is_complete_new_pc(title, desc):
    # Distinguishes a genuine complete, ready-to-use PC (desktop tower or
    # laptop) from a standalone GPU card that leaked into the same "PC gamer
    # {gpu}" result set (see search_prices below). Verified live against a
    # real "PC gamer RTX 5070 Ti" response: every one of the complete-PC
    # cards (desktop "PC Gamer <name>" builds and gaming laptops from
    # MSI/Gigabyte/Asus/Acer alike) mentions "Win11"/"Windows 11" in its
    # <.c-product__description> spec blurb, while every standalone-card
    # entry that also matched the GPU model (e.g. "Gainward GeForce RTX 5070
    # Ti Phoenix-S") describes only the card's own specs ("GeForce RTX 5070
    # Ti, PCI-Express 16x, 16 Go GDDR7, ...") with no OS mention at all -- a
    # clean split, same pattern as ldlc.py (shared platform, same behavior).
    if not title or "occasion" in title.lower():
        return False
    if not desc:
        return False
    desc_lower = desc.lower()
    return "win" in desc_lower and "sans win" not in desc_lower


def search_prices(cpu_model, gpu_model):
    # Verified live: Materiel.net's search does strict AND-matching, just
    # like LDLC (both are part of the LDLC Group and share the same
    # search platform). Combining the CPU and GPU model returns almost
    # nothing ("Ryzen 7 5700X RTX 4060" -> 3 unrelated products: an
    # adapter cable and a motherboard). Searching by GPU model alone is
    # too narrow too (only 2 exact-match products). "PC gamer {gpu}"
    # returns a full page of complete gaming-PC listings (208 results),
    # mirroring the query shape already validated for LDLC, so we reuse
    # it here and never leak the CPU model into the query.
    #
    # Real coherence bugs found live, all with the same root cause -- this
    # query had no relevance filtering of its own. With no GPU given, "PC
    # gamer {gpu}" collapses to an unanchored "PC gamer " query (verified
    # live for "i7-8700" + no GPU: 48 unrelated prices, 348,99EUR-3449,95EUR
    # range); a CPU-anchored "PC gamer i7-8700" doesn't help either (verified
    # live: all 48 results were "Reconditionné" refurbished office desktops
    # with cryptic model-code titles, no real CPU verification possible).
    # With an old/discontinued GPU given, the same loose-ranking noise shows
    # up (verified live for "GTX 1650 Super": 18 scattered prices from
    # 19,95EUR to 899,95EUR).
    #
    # Titles never contain the GPU model for the complete-PC listings here
    # either (e.g. "PC Gamer Werewolf - Win11 installé (version d'essai)"),
    # so like ldlc.py the model check runs against the description instead,
    # which spells it out in full ("NVIDIA GeForce RTX 5070 Ti, AMD Ryzen 7
    # 9800X3D, ..."). _is_complete_new_pc additionally keeps standalone GPU
    # cards (which DO name the GPU in their own title) from being counted as
    # if they were a whole PC's price.
    if not gpu_model:
        return []
    try:
        url = SEARCH_URL.format(query=requests.utils.quote(f"PC gamer {gpu_model}"))
        response = requests.get(url, headers=HEADERS, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        prices = []
        for card in soup.select("li.c-products-list__item"):
            title_el = card.select_one(".c-product__title")
            title = title_el.get_text(strip=True) if title_el else ""
            desc_el = card.select_one(".c-product__description")
            desc = desc_el.get_text(strip=True) if desc_el else ""
            if not _is_complete_new_pc(title, desc):
                continue
            if not _title_matches_model(desc, gpu_model):
                continue
            price_el = card.select_one(".o-product__price:not(.o-product__cut-price)")
            if price_el is None:
                continue
            price = _extract_price(_price_text(price_el))
            if price is not None:
                prices.append(price)
        return prices
    except Exception:
        return []


def search_ram_prices(ram_go, ram_type):
    # Tried "RAM {go}Go {type}" (LDLC's exact pattern, no space before "Go")
    # first: on materiel.net this auto-redirects straight to a single
    # unrelated product page (a CPU+motherboard+RAM "upgrade kit" whose
    # title happens to contain "RAM 16Go DDR4" verbatim) instead of
    # returning a search results page at all -- verified live, and the same
    # dead end was hit with "16Go DDR4", "DDR4 16Go" and "Barrette RAM 16Go
    # DDR4". Inserting a space before "Go" (e.g. "RAM 16 Go DDR4") avoids
    # that single-exact-match redirect and returns a full results page: 48
    # products, every one a genuine RAM module across a spread of
    # capacities/speeds -- verified live against materiel.net, zero
    # category pollution. Case doesn't affect relevance either (verified
    # live -- "RAM 16 Go ddr4" and "RAM 16 Go DDR4" return byte-identical
    # result sets), so ram_type is passed through as-is.
    return _search(f"RAM {ram_go} Go {ram_type}")


def search_storage_prices(storage_go, storage_type):
    # Tried "Disque {type} {go}Go" (LDLC's exact pattern) and "Disque {type}
    # {go} Go" first: both return results pages, but on materiel.net SSD
    # storage is so common across whole computers (iMacs, MacBooks, laptops)
    # that any query combining "SSD"/"Disque" with "{go} Go" gets swamped --
    # verified live, e.g. "Disque SSD 512 Go" returned 35 results of which
    # only 5 were standalone drives, the rest Apple iMacs/MacBooks that
    # merely ship with a 512 Go SSD (~85% noise, far past the ~30% level
    # that justifies filtering). Adding qualifiers like "interne", "NVMe",
    # "M.2" or "SATA" made no difference -- byte-identical polluted result
    # sets, verified live. Dropping the "Go" suffix entirely (e.g. "Disque
    # SSD 512", bare number) fixes it: verified live, this returns a small
    # but perfectly clean set of standalone SSD listings only (6/6 genuine
    # drives for the 512 case), because it stops matching the "X Go" phrase
    # that whole-computer spec sheets also contain. Case doesn't affect
    # relevance (verified live), so storage_type is passed through as-is.
    return _search(f"Disque {storage_type} {storage_go}")


def search_cpu_prices(cpu_model):
    # Do NOT copy LDLC's Task 4 query blindly despite the shared LDLC-Group
    # platform -- verified live, independently, against materiel.net.
    # Tried a bare model name first (e.g. "Ryzen 7 9800X3D"): 22 results,
    # almost entirely "PC Gamer <name>" prebuilt listings that merely
    # include this CPU (17/22), plus one motherboard+RAM kit bundle whose
    # title doesn't even contain the word "processeur" -- only 2 genuine
    # standalone CPU listings. Prefixing with "Processeur" (e.g. "Processeur
    # Ryzen 7 9800X3D", same shape as LDLC's query) drops every prebuilt PC:
    # 5 results left (verified live) -- 3 genuine standalone CPU listings
    # (2 new + 1 used), 1 unrelated motherboard (title doesn't mention the
    # CPU model at all, so a plain substring check already excludes it), and
    # 1 "MSI MAG B850 TOMAHAWK MAX WIFI + AMD Ryzen 7 9800X3D (Version tray)"
    # motherboard+CPU kit whose title DOES contain the full CPU model as a
    # verbatim substring (739,90EUR, well above the standalone CPU prices) --
    # a genuine substring/superset case a plain substring check would miss.
    # _title_matches_model rejects that kit via its " + " bundle check, and
    # separately rejects the one used ("- Occasion") listing so this
    # new-price search doesn't leak a used price into the "market neuf" step
    # ahead of the eBay occasion fallback (see estimator.py). Net: 2 genuine
    # new standalone CPU listings, 0% noise against the fixture.
    return _search(
        f"Processeur {cpu_model}",
        title_filter=lambda title: _title_matches_model(title, cpu_model),
    )


def search_gpu_prices(gpu_model):
    # Do NOT copy LDLC's Task 4 query blindly despite the shared LDLC-Group
    # platform -- verified live, independently, against materiel.net.
    # Tried a bare model name first (e.g. "RTX 5070 Ti"): 50 results, heavily
    # polluted by "PC Gamer <name>" prebuilts and gaming laptops that merely
    # include this GPU. Prefixing with "Carte graphique" (e.g. "Carte
    # graphique RTX 5070 Ti", same shape as LDLC's query) drops every
    # prebuilt/laptop: 27 results left (verified live), of which 21 are
    # genuine RTX 5070 Ti cards (confirmed via the page's own "Chipset
    # graphique" facet counts: "NVIDIA GeForce RTX 5070 Ti (21)") and 6 are
    # plain non-Ti "RTX 5070" cards -- Materiel.net's search doesn't do exact
    # phrase matching on "Ti", the same behavior already seen on LDLC.
    # Unlike LDLC's GPU search, that near-miss doesn't need special handling:
    # "RTX 5070 Ti" is not a substring of "RTX 5070", so a plain substring
    # check on the title already rejects all 6 (verified against the
    # fixture). Of the 21 genuine RTX 5070 Ti results, 4 are used ("-
    # Occasion") listings -- _title_matches_model rejects those too, for the
    # same "market neuf" reason as search_cpu_prices. Net: 17 genuine new
    # RTX 5070 Ti listings, 0% noise against the fixture. The suffix-boundary
    # check in _title_matches_model (rejecting a "Ti Super"-style superset)
    # isn't exercised by this fixture -- no such variant was returned live --
    # but is kept as the same cheap insurance pccomponentes.py keeps it for.
    return _search(
        f"Carte graphique {gpu_model}",
        title_filter=lambda title: _title_matches_model(title, gpu_model),
    )
