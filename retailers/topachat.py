import requests

# TopAchat's storefront (a SvelteKit app) renders search results client-side,
# but it's backed by a public JSON search API that the page itself calls on
# load (visible in the SSR payload's `page_requests`). That API returns
# clean, already-numeric prices (price_final, in cents) grouped by category,
# so there's no HTML/CSS to scrape and no €<sup>cents</sup> text-parsing
# needed at all -- verified live before writing any parsing logic.
SEARCH_URL = "https://www.topachat.com/api/search/search.main.php"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
}

# The only category that contains complete desktop PC builds. The same
# search also returns "PC DIY (kit à monter)", "Kit d'évolution", loose
# "Processeur" listings, and laptop categories ("PC Portable Gamer",
# "PC Portable"), which are not complete-PC prices and would skew the
# result, so they're filtered out.
PC_CATEGORY_LABEL = "PC Gamer"


def _search(query, category_label):
    try:
        response = requests.get(
            SEARCH_URL, params={"terms": query}, headers=HEADERS, timeout=10
        )
        response.raise_for_status()
        data = response.json()

        prices = []
        categories = data["result"]["document"]["categories"]
        for category in categories:
            # Compared case-insensitively (both sides upper-cased) so that
            # search_ram_prices/search_storage_prices can pass ram_type /
            # storage_type straight through as the category label (they
            # arrive lower-cased, e.g. "ddr4", "ssd", while TopAchat's real
            # category labels are upper-cased, e.g. "DDR4", "SSD" -- verified
            # live, see below). Doing the transform here, inside this
            # try/except, keeps it from ever raising outside the guarded
            # block regardless of what gets passed in.
            actual_label = category.get("label_category")
            if not actual_label or actual_label.upper() != category_label.upper():
                continue
            for product in category.get("product", []):
                offer = product.get("offer")
                if not offer or "price_final" not in offer:
                    continue
                # price_final is an integer number of cents (e.g. 144999 for
                # 1449.99 €).
                prices.append(round(offer["price_final"] / 100, 2))
        return prices
    except Exception:
        return []


def search_prices(cpu_model, gpu_model):
    # Unlike LDLC (strict AND-matching, chokes on combined CPU+GPU queries),
    # TopAchat's search handles a combined query well: verified live that
    # "Ryzen 7 5700X RTX 4060" returned a "PC Gamer" category where 13 of the
    # first 15 sampled builds actually contain a Ryzen 7 5700X, versus a
    # GPU-only "PC gamer RTX 4060" query which mixed in many unrelated CPUs
    # (Ryzen 5 5500, Ryzen 7 7800X3D, Ryzen 7 9800X3D, etc.). So, like
    # PcComponentes, we keep both models in the query.
    query = f"{cpu_model} {gpu_model}"
    return _search(query, PC_CATEGORY_LABEL)


def search_ram_prices(ram_go, ram_type):
    # Verified live against the real API (GET with params={"terms": "16Go
    # ddr4"}, and cross-checked with "8Go ddr3" / "32Go ddr5"): the plan's
    # guessed static "Mémoire" category label does not exist at all in the
    # real response. TopAchat instead groups RAM results into a category
    # literally named after the DDR generation -- "DDR3", "DDR4", "DDR5" --
    # alongside noise categories that are NOT what we want ("SoDimm" laptop
    # RAM modules, "Kit d'évolution" CPU+motherboard+RAM bundles, and
    # "PC Portable"/"PC Portable Gamer" laptops that merely mention a
    # matching RAM size). Every one of the 15 sampled "DDR4" results for
    # "16Go ddr4" was a genuine standalone RAM module (Textorm, Kingston
    # Fury, Corsair, etc.), so no extra noise filtering is needed once
    # correctly scoped to that category. Since the category label tracks
    # ram_type directly (not a fixed constant), it's passed straight through
    # to _search, which upper-cases both sides before comparing.
    query = f"{ram_go}Go {ram_type}"
    return _search(query, ram_type)


def search_storage_prices(storage_go, storage_type):
    # Verified live against the real API (GET with params={"terms": "512Go
    # ssd"}): the plan's guessed static "Disque dur / SSD" category label
    # does not exist either. TopAchat groups standalone SSD listings under a
    # category simply named "SSD" (all 5 first-page results for "512Go ssd"
    # were genuine standalone drives -- Patriot, Kingston -- including M.2
    # NVMe models, which TopAchat files under "SSD" too rather than a
    # separate "NVMe" category). The query is dominated by noise outside
    # that category -- laptops and MacBooks that merely ship a matching SSD
    # ("PC Portable" 34 refs, "PC Portable Gamer" 17, "Portable Mac" 25, vs.
    # only 5 for the real "SSD" category) -- but since we filter to the
    # exact category label, that noise never reaches the result.
    # NOTE: only the "ssd" case was live-verified end to end. "hdd" was
    # tried too ("500Go hdd") and did NOT map cleanly to a matching
    # category label (TopAchat's real internal-drive category is named
    # "Disque Dur SATA 3.5\"", not "HDD", and the English term "hdd" in the
    # query confusingly pulled in "SSD" results instead). This is a known
    # gap for the "hdd" storage type: it will currently return an empty
    # list from this retailer (degrading gracefully, since _search catches
    # the no-match case) rather than real hard-drive prices. Flagging this
    # loudly rather than silently mismatching -- fix separately if HDD
    # pricing from TopAchat is needed.
    query = f"{storage_go}Go {storage_type}"
    return _search(query, storage_type)
