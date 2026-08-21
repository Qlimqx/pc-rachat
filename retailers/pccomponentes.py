import re

import requests
from bs4 import BeautifulSoup

SEARCH_URL = "https://www.pccomponentes.fr/search?query={query}"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
}


# Same list as rueducommerce.py/amazon.py's _title_matches_model: suffix
# qualifiers that, when they immediately follow a matched model number, mark
# a different, typically pricier variant rather than the base model -- e.g.
# a "RTX 5070 Ti Super" listing must not match a "RTX 5070 Ti" query, the
# same way NVIDIA previously shipped a "RTX 4070 Ti Super" alongside the
# plain "RTX 4070 Ti". Checked against the real CPU/GPU fixtures: none of
# their data-product-name values contain a "Ti Super"-style near-miss, so
# this doesn't change any fixture-based test outcome -- it's protection
# against a variant PcComponentes' search doesn't currently return but
# plausibly could.
_SUFFIX_QUALIFIERS = ("ti", "super", "xt", "xtx", "x3d")


def _title_matches_model(title, model):
    """Check whether a product's data-product-name refers to `model`.

    Unlike rueducommerce.py/amazon.py's _title_matches_model, PcComponentes
    exposes a clean, structured data-product-name attribute right alongside
    data-product-price. Verified against the CPU and GPU fixtures: model
    names appear as exact, consistently-spaced substrings (e.g. "Ryzen 7
    9800X3D", "RTX 5070 Ti"), with no "RTX4060" vs "RTX 4060" style spacing
    collapse -- so, unlike those two files, this doesn't need a
    whitespace-tolerant regex to line up the match itself; a plain
    case-insensitive substring find is enough for that part.

    But finding the substring isn't enough on its own: a plain substring
    check would also match a listing that starts with the requested model
    only to extend it into a different, pricier variant, e.g. "RTX 5070 Ti"
    is literally a substring of "RTX 5070 Ti Super". So, same as the other
    two retailer modules, a match is rejected in two cases: (1) the
    character right after it is alphanumeric with no separating space at
    all, e.g. a concatenated "RTX5070TiSuper"; or (2) the first word after
    the match, once any whitespace is skipped, is one of a small known list
    of GPU/CPU suffix qualifiers (`_SUFFIX_QUALIFIERS`, e.g. "Ti", "Super",
    "XT"), e.g. "RTX 5070 Ti Super". Anything else after a space -- e.g.
    "RTX 5070 Ti 16Go GDDR7" -- is unrelated trailing product text and
    still counts as a match.
    """
    title_norm = title.lower()
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
        # data-product-price is a marker attribute set only on real product
        # result links within the search grid (verified against the fixture:
        # 7 occurrences, exactly matching the 7 listed products), unlike the
        # data-testid="normal-link" attribute which is reused across many
        # unrelated UI elements (carousels, breadcrumbs, etc.) on the page.
        # It also carries the price itself as a clean, unlocalized string
        # (e.g. "1291.2"), so it can be read straight off the same element
        # without a second descendant lookup or any locale-aware parsing.
        for card in soup.select("a[data-product-price]"):
            if title_filter is not None:
                product_name = card.get("data-product-name")
                if product_name is None or not title_filter(product_name):
                    continue
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
    #
    # That "highly relevant" finding doesn't generalize, though (same
    # pattern found elsewhere this session): verified live for
    # "i5-10400F GTX 1650 Super", this query returns 40 results of which
    # only 1 is even close (a plain "GTX 1650", not the requested Super
    # variant), the other 39 spanning unrelated CPUs (i5-11400F,
    # i5-12400F, Ryzen 5 5500, i3-10100F, i5-14600KF...), unrelated GPUs
    # (RTX 3050/3060/4060 Ti/5060/5070, GT 1030), refurbished laptops with
    # a completely different CPU (i5-10310U), and even a single bare CPU
    # listing (315EUR, not a PC at all). No relevance filtering was applied
    # here even though this file already has _title_matches_model (used by
    # search_cpu_prices/search_gpu_prices) -- requiring BOTH models to
    # genuinely appear in data-product-name fixes it, mirroring
    # amazon.py/rueducommerce.py's AND-filtered search_prices.
    return _search(
        f"{cpu_model} {gpu_model}",
        title_filter=lambda name: (
            _title_matches_model(name, cpu_model) and _title_matches_model(name, gpu_model)
        ),
    )


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
    # requested model -- verified live against pccomponentes.fr.
    #
    # That near-miss is a different CPU SKU, not statistical noise: at a
    # plausible N=1 or N=2 result count for some other model, a wrong-SKU
    # price wouldn't be diluted by a median at all -- it would BE the
    # reported price. So it's filtered out directly via data-product-name
    # (a clean, structured attribute PcComponentes exposes right alongside
    # data-product-price) rather than tolerated: title_filter drops any
    # card whose product name doesn't contain cpu_model, which excludes the
    # "9850X3D" listing while keeping both genuine "9800X3D" ones.
    return _search(
        f"Processeur {cpu_model}",
        title_filter=lambda name: _title_matches_model(name, cpu_model),
    )


def search_gpu_prices(gpu_model):
    # A bare model name does NOT carry over cleanly here either -- verified
    # live: bare "RTX 5070 Ti" returned 40 results, but ~53% (21/40) were
    # laptops and prebuilt desktops that merely include this GPU (e.g.
    # "Ordinateur portable MSI Vector 16 HX AI ... RTX 5070 Ti"), far above
    # the noise-tolerance threshold. Prefixing with "Carte graphique" (e.g.
    # "Carte graphique RTX 5070 Ti") drops every laptop and desktop: all 33
    # results are genuine standalone RTX 5070 Ti graphics cards (PNY, Zotac,
    # MSI, Gigabyte, ASUS, Palit, Inno3D, etc.) -- verified live against
    # pccomponentes.fr, 0% noise against the fixture.
    #
    # A title_filter is still applied here as cheap insurance and for
    # consistency with search_cpu_prices: it costs nothing when there's no
    # noise (confirmed against the fixture -- all 33 genuine cards contain
    # "RTX 5070 Ti" in data-product-name, so none are dropped), and it
    # guards against a wrong-SKU listing (e.g. a "RTX 5070" or "RTX 5070 Ti
    # Super" near-miss) slipping through on some future query/page.
    return _search(
        f"Carte graphique {gpu_model}",
        title_filter=lambda name: _title_matches_model(name, gpu_model),
    )
