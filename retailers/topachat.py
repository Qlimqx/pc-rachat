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


def search_prices(cpu_model, gpu_model):
    try:
        # Unlike LDLC (strict AND-matching, chokes on combined CPU+GPU
        # queries), TopAchat's search handles a combined query well: verified
        # live that "Ryzen 7 5700X RTX 4060" returned a "PC Gamer" category
        # where 13 of the first 15 sampled builds actually contain a Ryzen 7
        # 5700X, versus a GPU-only "PC gamer RTX 4060" query which mixed in
        # many unrelated CPUs (Ryzen 5 5500, Ryzen 7 7800X3D, Ryzen 7 9800X3D,
        # etc.). So, like PcComponentes, we keep both models in the query.
        query = f"{cpu_model} {gpu_model}"
        response = requests.get(
            SEARCH_URL, params={"terms": query}, headers=HEADERS, timeout=10
        )
        response.raise_for_status()
        data = response.json()

        prices = []
        categories = data["result"]["document"]["categories"]
        for category in categories:
            if category.get("label_category") != PC_CATEGORY_LABEL:
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
