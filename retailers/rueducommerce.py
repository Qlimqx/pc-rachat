import re

import requests
from bs4 import BeautifulSoup

# Rue du Commerce's search is a path-based, server-rendered page (the query
# is a URL path segment, not a query-string param) -- verified live via
# network inspection: submitting the header search box navigates to
# /recherche/{query}/ and the full result list is present in the initial
# HTML response itself, no separate XHR/JSON API call involved (unlike
# TopAchat). There's also an internal Algolia-backed autocomplete endpoint
# (/t/fr-fr/search/autocomplete/...), but it only returns suggestion
# fragments, not priced listings, so it's not useful here.
SEARCH_URL = "https://www.rueducommerce.fr/recherche/{query}/"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
}


# Suffix qualifiers that, when they immediately follow a matched model
# number (whether concatenated or separated by whitespace), mark a
# different, typically pricier variant rather than the base model -- e.g.
# "RTX4060Ti" and "RTX 4060 Ti" are both a different card than "RTX 4060"
# and must both be rejected. This is a deliberately narrow, known list
# rather than a blanket "reject any alphanumeric token after the match"
# rule: a blanket rule would also reject legitimate matches where the
# model is simply followed by unrelated product text that happens to
# start with a letter/digit, e.g. "RTX 4060 16GB" (the "16gb" RAM spec is
# not a suffix extending the model number, so it must still count as a
# match).
_SUFFIX_QUALIFIERS = ("ti", "super", "xt", "xtx", "x3d")


def _title_matches_model(title, model):
    """Check whether a product title refers to `model`, tolerating the
    retailer's inconsistent spacing (titles render some models as "RTX4060"
    with no space and others as "NVIDIA RTX 5060" with one) while still
    rejecting near-miss variants such as "RTX4060Ti" or "RTX 4060 Ti" for a
    search of "RTX 4060".

    Verified against the real fixture: RdC's titles are plain text with no
    machine-readable model field, so this is a substring check, not fuzzy
    matching -- spaces in `model` become optional (\\s*) so "RTX 4060"
    matches title text "RTX4060". A match is rejected in two cases: (1) the
    character right after it is alphanumeric with no separating space at
    all, e.g. inside "RTX4060Ti" -- any concatenated alphanumeric suffix is
    treated as extending the model number, since there's no space to prove
    otherwise; or (2) the first word after the match, once any whitespace
    is skipped, is one of a small known list of GPU/CPU suffix qualifiers
    (`_SUFFIX_QUALIFIERS`, e.g. "Ti", "Super", "XT"), e.g. "RTX 4060 Ti".
    Anything else after a space -- e.g. "RTX 4060 16GB" -- is treated as
    unrelated trailing product text and still counts as a match.
    """
    title_norm = title.lower()
    pattern = re.escape(model.lower().strip()).replace(r"\ ", r"\s*")
    match = re.search(pattern, title_norm)
    if match is None:
        return False
    end = match.end()
    tail = title_norm[end:]
    if tail and tail[0].isalnum():
        return False
    next_word = re.match(r"\s+([a-z0-9]+)", tail)
    if next_word and next_word.group(1) in _SUFFIX_QUALIFIERS:
        return False
    return True


def _fetch_soup(query):
    """Run a Rue du Commerce search for `query` and return the parsed
    result page.

    Rue du Commerce's search is a path-based, server-rendered page (the
    query is a URL path segment, not a query-string param) -- verified live
    via network inspection: submitting the header search box navigates to
    /recherche/{query}/ and the full result list is present in the initial
    HTML response itself, no separate XHR/JSON API call involved (unlike
    TopAchat). Raises on network failure or a non-2xx response -- callers
    are expected to catch that and translate it into an empty price list,
    matching every other retailer module's contract.
    """
    url = SEARCH_URL.format(query=requests.utils.quote(query))
    response = requests.get(url, headers=HEADERS, timeout=10)
    response.raise_for_status()
    return BeautifulSoup(response.text, "html.parser")


def _extract_card_price(card):
    """Extract the float price from a single "li.pdt-item" result card, or
    None if no usable price is present.

    No JSON API, no data-price attribute, no itemprop="price", and no
    product-level JSON-LD block -- verified against the fixtures (only
    plain-text prices inside "div.price" containers). A discounted product
    renders <div class="price"><div class="old-price">...</div>
    <div class="new-price">...</div></div> (old-price is the
    struck-through original, new-price is the current price to use); a
    non-discounted product just renders a plain nested
    <div class="price"><div class="price">1 299,00€</div></div>.
    Both variants also carry a "sr-only" label span ("Nouveau prix :") that
    must be stripped before reading the text, and the price text itself
    uses a narrow no-break space as the thousands separator and a comma as
    the decimal separator (e.g. "1 639,90€").
    """
    price_container = card.select_one("div.price")
    if price_container is None:
        return None
    target = (
        price_container.select_one("div.new-price")
        or price_container.select_one("div.price")
        or price_container
    )
    for sr_only in target.select(".sr-only"):
        sr_only.decompose()
    raw_price = target.get_text(strip=True)
    raw_price = (
        raw_price.replace("\xa0", "")
        .replace(" ", "")
        .replace("€", "")
        .replace(",", ".")
        .strip()
    )
    try:
        return float(raw_price)
    except ValueError:
        return None


def search_prices(cpu_model, gpu_model):
    try:
        # Unlike LDLC/Materiel.net/Grosbill (strict AND-matching, choke on
        # combined CPU+GPU queries), Rue du Commerce's search handles a
        # combined query well: verified live that "Ryzen 7 5700X RTX 4060"
        # returned 48 listings in the "PC" category. Verified against the
        # real fixture: only 33/48 titles actually contain "5700X" (15 are
        # Ryzen 7 9700X or 7700X builds -- a different CPU generation, not a
        # near-miss), and only 22/48 contain exact "4060" (43/48 contain
        # "4060" as part of a family match, but the rest of those are 4060
        # Ti, which is a different, more expensive card). Both models are
        # kept together in the query since RdC's combined search still
        # returns useful results overall, similar to TopAchat/PcComponentes
        # -- but see the title-relevance filter below, which is what keeps
        # the wrong-generation/wrong-card noise out of the returned prices.
        soup = _fetch_soup(f"{cpu_model} {gpu_model}")

        prices = []
        for card in soup.select("li.pdt-item"):
            # Skip cards whose title doesn't actually reference both the
            # requested CPU and GPU -- the combined query returns plenty of
            # wrong-generation CPUs and wrong-tier GPUs (see comment above),
            # and including their prices measurably skews the result (the
            # wrong-CPU-generation subset has a median ~45% higher than the
            # correctly matched subset). Titles live in "h3.title-3".
            title_el = card.select_one("h3.title-3")
            title = title_el.get_text(strip=True) if title_el else ""
            if not (
                _title_matches_model(title, cpu_model)
                and _title_matches_model(title, gpu_model)
            ):
                continue
            price = _extract_card_price(card)
            if price is not None:
                prices.append(price)
        return prices
    except Exception:
        return []


def search_ram_prices(ram_go, ram_type):
    try:
        # Tried a bare "{go}Go {type}" query first (e.g. "16Go DDR4"):
        # verified live it returns 48 results but 100% are noise --
        # laptops/office PCs/NAS appliances whose spec sheet merely mentions
        # "16Go DDR4" RAM, not one single standalone memory module.
        # Prefixing with just "RAM" (e.g. "RAM 16Go DDR4") barely helps --
        # verified live, still only ~10/48 (~21%) genuine RAM modules, the
        # rest still whole machines. Prefixing with "Barrette RAM" instead
        # (e.g. "Barrette RAM 16Go DDR4") anchors the search to the
        # standalone-memory-module category: verified live and against the
        # real fixture, 48/48 results are genuine RAM modules (Corsair,
        # Kingston, G.Skill, Transcend, etc.), with 48/48 containing "DDR4"
        # and 47/48 containing "16 Go"/"16Go" (the one exception is a
        # "4 x 16 Go" kit phrasing, still a correct 16Go module count) --
        # 0% category noise, well under the ~30% threshold that would
        # justify a title-relevance filter, so none is applied here (unlike
        # search_prices above). Case doesn't affect relevance -- verified
        # live, "barrette ram 16go ddr4" and "Barrette RAM 16Go DDR4"
        # return identical result sets -- so ram_type is passed through
        # as-is.
        soup = _fetch_soup(f"Barrette RAM {ram_go}Go {ram_type}")
        prices = []
        for card in soup.select("li.pdt-item"):
            price = _extract_card_price(card)
            if price is not None:
                prices.append(price)
        return prices
    except Exception:
        return []


def search_storage_prices(storage_go, storage_type):
    try:
        # Tried a bare "{go}Go {type}" query first (e.g. "512Go SSD"):
        # verified live, 48/48 results are laptops/office PCs that merely
        # ship with a 512Go SSD, not standalone drives. "Disque {type}
        # {go}Go" and "Disque {type} {go}" (the pattern that works on
        # LDLC/Grosbill) both still carry substantial whole-machine
        # pollution here -- verified live, ~5/12 (~42%) and ~6/13 (~46%)
        # respectively are laptops, not standalone drives. Anchoring with
        # "{type} interne {go}Go" instead (e.g. "SSD interne 512Go") fixes
        # it: verified live and against the real fixture, 15/15 results are
        # genuine standalone SSD listings (Verbatim, Hikvision, Sandisk,
        # Transcend, Kingston, etc.), zero laptop/PC pollution -- and the
        # same pattern held for a larger size too ("SSD interne 1To": 41/41
        # genuine drives, verified live). 0% category noise, well under the
        # ~30% threshold that would justify a title-relevance filter, so
        # none is applied here. Case doesn't affect relevance either
        # (verified live: "ssd interne 512go" and "SSD interne 512Go"
        # return identical result sets), so storage_type is passed through
        # as-is.
        soup = _fetch_soup(f"{storage_type} interne {storage_go}Go")
        prices = []
        for card in soup.select("li.pdt-item"):
            price = _extract_card_price(card)
            if price is not None:
                prices.append(price)
        return prices
    except Exception:
        return []
