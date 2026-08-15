import requests
from bs4 import BeautifulSoup

SEARCH_URL = "https://www.pccomponentes.fr/search?query={query}"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
}


def _search(query):
    try:
        url = SEARCH_URL.format(query=requests.utils.quote(query))
        response = requests.get(url, headers=HEADERS, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        prices = []
        # data-product-price is a marker attribute set only on real product
        # result links within the search grid (verified against the fixture:
        # 7 occurrences, exactly matching the 7 listed products), unlike the
        # data-testid="normal-link" attribute which is reused across many
        # unrelated UI elements (carousels, breadcrumbs, etc.) on the page.
        # It also carries the price itself as a clean, unlocalized string
        # (e.g. "1291.2"), so it can be read straight off the same element
        # without a second descendant lookup or any locale-aware parsing.
        for card in soup.select("a[data-product-price]"):
            raw_price = card.get("data-product-price")
            if raw_price is None:
                continue
            try:
                price = float(raw_price)
            except ValueError:
                continue
            prices.append(price)
        return prices
    except Exception:
        return []


def search_prices(cpu_model, gpu_model):
    # Unlike LDLC (whose search does strict AND-matching and chokes on
    # combined CPU+GPU queries), PcComponentes' search is Algolia-backed
    # and handles both terms together fine, returning highly relevant
    # complete-PC listings. Verified live: "Ryzen 7 5700X RTX 4060"
    # returned 7 matching PC builds that actually contain both parts,
    # versus a broader "PC gamer RTX 4060" query which returned PCs
    # with unrelated CPUs. So, unlike LDLC, we keep both models.
    return _search(f"{cpu_model} {gpu_model}")


def search_ram_prices(ram_go, ram_type):
    # "{go}Go {type}" (e.g. "16Go DDR4") was verified live against
    # pccomponentes.fr: all 40 first-page results were genuine RAM module
    # listings (Corsair, G.Skill, Patriot, Samsung, etc.) matching the
    # requested capacity and type, with no unrelated noise -- unlike LDLC,
    # no extra anchor term (e.g. a "RAM" prefix) was needed. ram_type is
    # passed through as-is; no case transform was verified to change
    # relevance.
    return _search(f"{ram_go}Go {ram_type}")


def search_storage_prices(storage_go, storage_type):
    # "{go}Go {type}" (e.g. "512Go SSD") was verified live against
    # pccomponentes.fr: the large majority of the 40 first-page results were
    # genuine standalone SSD listings (Lexar, Kingston, ADATA, Transcend,
    # etc.), with only a couple of pre-built PCs that happen to ship a
    # matching SSD slipping in -- the same tradeoff LDLC's storage search
    # has. storage_type is passed through as-is; no case transform was
    # verified to change relevance.
    return _search(f"{storage_go}Go {storage_type}")
