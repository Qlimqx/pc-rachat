import re

import requests
from bs4 import BeautifulSoup

SEARCH_URL = "https://www.grosbill.com/produit.aspx"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
}


# Suffix qualifiers that, when they immediately follow a matched model
# number, mark a different, typically pricier variant rather than the base
# model -- e.g. a "RTX 5070 Ti Super" listing must not match a "RTX 5070 Ti"
# query. Same list as pccomponentes.py/materiel_net.py/rueducommerce.py/
# amazon.py's _title_matches_model.
_SUFFIX_QUALIFIERS = ("ti", "super", "xt", "xtx", "x3d")


def _title_matches_model(title, model):
    """Check whether a product's title (as rendered by Grosbill's own
    "libelle_produit" span) refers to `model`.

    Grosbill's card markup exposes a clean, structured title element right
    alongside the price -- same shape as PcComponentes' data-product-name --
    but unlike PcComponentes, Grosbill's own title text is inconsistent
    about the space between a model number and a trailing "Ti"/"Super"
    qualifier: verified against the GPU fixture, most cards render "RTX
    5070 Ti" (spaced) but two render "RTX 5070Ti" (no space) for the exact
    same product. A plain substring find on the spaced "RTX 5070 Ti" query
    would silently drop those two genuine cards. So, like
    rueducommerce.py/amazon.py's _title_matches_model, spaces in `model`
    are made optional (`\\s*`) in the match pattern to tolerate that.

    On top of that whitespace tolerance, two more checks apply:

    1. Suffix-boundary check (same as every other retailer module here): a
       match is rejected if the character right after it is alphanumeric
       with no separating space (a concatenated "RTX5070TiSuper"), or if
       the first word after it, once whitespace is skipped, is one of
       _SUFFIX_QUALIFIERS (e.g. "Ti", "Super") -- guards against a listing
       whose title starts with the requested model only to extend it into
       a different, pricier variant.
    2. Bundle exclusion: the GPU query returned one genuine
       substring/superset near-miss live -- a "Kit Upgrade PC" bundle
       titled "RTX 5070Ti WF OC SFF 16Go + RM850e 850W Gold 3.1" (a GPU +
       PSU kit, 1199,00EUR) whose title contains the full GPU model as a
       verbatim substring while being a different *product* (bundle, not a
       standalone card), the same danger pattern materiel_net.py's
       _title_matches_model calls out for its own kit bundles. Grosbill's
       own kit-naming convention joins components with " + ", which no
       standalone CPU/GPU listing in either fixture contains, so titles
       with " + " are rejected outright.
    """
    title_norm = title.lower()
    if " + " in title_norm:
        return False
    pattern = re.escape(model.lower().strip()).replace(r"\ ", r"\s*")
    match = re.search(pattern, title_norm)
    if match is None:
        return False
    tail = title_norm[match.end():]
    if tail and tail[0].isalnum():
        return False
    next_word = re.match(r"\s+([a-z0-9]+)", tail)
    if next_word and next_word.group(1) in _SUFFIX_QUALIFIERS:
        return False
    return True


def _search(query, title_filter=None):
    try:
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
        # This selector pair (card container + reference/price span) is
        # shared by the "PC Gamer" complete-build cards, standalone RAM
        # module cards, standalone SSD cards, and standalone CPU/GPU cards
        # alike -- verified live for all categories, no divergent markup to
        # special-case. title_filter is optional and only used by
        # search_cpu_prices/search_gpu_prices, which need per-card
        # title-relevance filtering that the other search_* functions here
        # don't (their category-anchored queries already came back
        # noise-free, verified live).
        for card in soup.select("div.grb__liste-produit__liste__produit"):
            if title_filter is not None:
                title_el = card.select_one(
                    ".grb__liste-produit__liste__produit__information"
                    "__libelle__libelle_produit"
                )
                if title_el is None or not title_filter(
                    title_el.get_text(strip=True)
                ):
                    continue
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


def search_prices(cpu_model, gpu_model):
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
    return _search(f"PC gamer {cpu_model}")


def search_ram_prices(ram_go, ram_type):
    # Tried a bare "{go}Go {type}" query first (e.g. "16Go DDR4"): it
    # returns 20 results but roughly 35% are laptops/PCs/motherboard-kits
    # whose spec sheet merely mentions "16Go" RAM, not standalone memory
    # modules -- verified live against grosbill.com. Prefixing with "RAM"
    # (e.g. "RAM 16Go DDR4") anchors the search to the RAM category: 13
    # results, all but one a genuine standalone memory module (the outlier
    # is a motherboard+RAM bundle kit that does contain matching DDR4 RAM,
    # so it's not really noise) -- verified live, ~8% noise, well under the
    # ~30% threshold that would justify adding a filter. Case doesn't
    # affect relevance -- "RAM 16Go ddr4" and "RAM 16Go DDR4" return the
    # same result set (verified live) -- so ram_type is passed through
    # as-is.
    return _search(f"RAM {ram_go}Go {ram_type}")


def search_storage_prices(storage_go, storage_type):
    # Tried "{go}Go {type}" (e.g. "512Go SSD") first: 100% noise, every
    # result a laptop that merely ships with a 512Go SSD -- verified live
    # against grosbill.com. Adding a "Disque" prefix with the "Go" suffix
    # kept ("Disque SSD 512Go") fixes the laptop pollution but is so narrow
    # it returns only 1 result. Dropping the "Go" suffix entirely (e.g.
    # "Disque SSD 512", bare number) keeps the same zero-pollution
    # precision while widening the match: 3 results, all genuine standalone
    # SSD listings -- verified live, matching the same "Go" -> whole-machine
    # spec-sheet pollution pattern found on Materiel.net, and the same fix
    # (materiel_net.py's search_storage_prices uses the identical bare-
    # number pattern). Case doesn't affect relevance either (verified live:
    # "Disque ssd 512" and "Disque SSD 512" return the same result set), so
    # storage_type is passed through as-is.
    return _search(f"Disque {storage_type} {storage_go}")


def search_cpu_prices(cpu_model):
    # A bare model query (e.g. "Ryzen 7 9800X3D") is NOT precise enough on
    # its own -- verified live: 7 results, only 2 genuine standalone
    # "Processeur" listings, the other 5 all "PC Gamer" complete-build
    # cards that merely contain this CPU (~71% noise, far past the ~30%
    # threshold that would tolerate leaving it unanchored). Prefixing with
    # "Processeur" (e.g. "Processeur Ryzen 7 9800X3D") -- same category-
    # anchor idea as RAM's "RAM" prefix and storage's "Disque" prefix above
    # -- drops every prebuilt PC: 2 results left (verified live), both
    # genuine standalone CPU listings ("AMD Ryzen 7 9800X3D" and "AMD Ryzen
    # 7 9800X3D Tray"), 0% noise against the fixture. No dangerous
    # substring/superset noise (bundle, used/"occasion" listing, or suffix
    # mismatch) turned up for this query, but title_filter is still applied
    # -- cheap insurance against a future query/page where one does show up,
    # same reasoning materiel_net.py's search_cpu_prices keeps it for.
    return _search(
        f"Processeur {cpu_model}",
        title_filter=lambda title: _title_matches_model(title, cpu_model),
    )


def search_gpu_prices(gpu_model):
    # A bare model query (e.g. "RTX 5070 Ti") is NOT precise enough on its
    # own -- verified live: 20 results, 13 genuine standalone "Carte
    # graphique" listings mixed with 7 pollution items (a "PC Bureautique"
    # prebuilt, 3 gaming laptops, a "PC Gamer" prebuilt, and a GPU+PSU kit
    # bundle -- 35% noise). Prefixing with "Carte graphique" (same
    # category-anchor idea as search_cpu_prices' "Processeur" prefix)
    # drops every prebuilt/laptop entirely: 15 results left (verified
    # live), 12 genuine standalone cards plus 2 more genuine cards whose
    # titles omit the space before "Ti" ("ROG Strix GeForce RTX 5070Ti
    # 16GB GDDR7 OC Edition" and "RTX 5070Ti 16GB Overclocked Triple Fan
    # V1" -- both caught by _title_matches_model's whitespace-tolerant
    # match), and 1 dangerous near-miss: a "Kit Upgrade PC" bundle
    # titled "RTX 5070Ti WF OC SFF 16Go + RM850e 850W Gold 3.1" (a GPU+PSU
    # kit at 1199,00EUR) whose title contains the full GPU model as a
    # verbatim substring -- a genuine substring/superset case (different
    # *product*, not just a different model variant), the same danger
    # pattern materiel_net.py/pccomponentes.py call out, so it's filtered
    # even though it's only 1/15 (~7%) of results -- the SAFE ~5-10% noise
    # tolerance applies to genuinely unrelated products, not to a
    # substring/superset match like this one. _title_matches_model rejects
    # it via its " + " bundle check. No used/"occasion" listings leaked
    # into the result set (verified against the fixture: the page's only
    # "occasion" mention is an unrelated nav link to the reconditioned-
    # goods landing page), so unlike materiel_net.py's search_gpu_prices no
    # occasion exclusion was needed. Net: 14 genuine new RTX 5070 Ti
    # listings, 1 bundle correctly filtered out.
    return _search(
        f"Carte graphique {gpu_model}",
        title_filter=lambda title: _title_matches_model(title, gpu_model),
    )
