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


def search_cpu_prices(cpu_model):
    # Unlike RAM/storage, a bare model name does NOT carry over cleanly here
    # -- verified live: bare "Ryzen 7 9800X3D" returned 33 results, but only
    # 2 were genuine standalone CPU listings; the other 31 were prebuilt PCs
    # that merely include this CPU (e.g. "PC de bureau PcCom Imperial AMD
    # Ryzen 7 9800X3D ... RTX 5070 Ti" at 2660.38EUR). Prefixing with
    # "Processeur" (e.g. "Processeur Ryzen 7 9800X3D") drops all 31 prebuilt
    # PCs, leaving only 3 results: the 2 genuine listings (446.18EUR,
    # 435EUR) plus 1 near-miss for the different "Ryzen 7 9850X3D" SKU
    # (485.85EUR) that PcComponentes' search doesn't distinguish from the
    # requested model -- verified live against pccomponentes.fr. That 1/3
    # (~33%) noise sits above the ~10% threshold where it's obviously safe
    # to ignore, so a median-invariance check was done: statistics.median of
    # all 3 prices is 446.18, versus 440.59 with the near-miss excluded --
    # only a 1.3% difference, so the median is effectively unaffected.
    return _search(f"Processeur {cpu_model}")


def search_gpu_prices(gpu_model):
    # A bare model name does NOT carry over cleanly here either -- verified
    # live: bare "RTX 5070 Ti" returned 40 results, but ~53% (21/40) were
    # laptops and prebuilt desktops that merely include this GPU (e.g.
    # "Ordinateur portable MSI Vector 16 HX AI ... RTX 5070 Ti"), far above
    # the noise-tolerance threshold. Prefixing with "Carte graphique" (e.g.
    # "Carte graphique RTX 5070 Ti") drops every laptop and desktop: all 33
    # results are genuine standalone RTX 5070 Ti graphics cards (PNY, Zotac,
    # MSI, Gigabyte, ASUS, Palit, Inno3D, etc.) -- verified live against
    # pccomponentes.fr, 0% noise, no median-invariance check needed.
    return _search(f"Carte graphique {gpu_model}")
