import requests
from bs4 import BeautifulSoup

SEARCH_URL = "https://www.grosbill.com/produit.aspx"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
}


def _search(query):
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
        # module cards, and standalone SSD cards alike -- verified live for
        # all three categories, no divergent markup to special-case.
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
