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


def search_prices(cpu_model, gpu_model):
    try:
        # Unlike LDLC/Materiel.net/Grosbill (strict AND-matching, choke on
        # combined CPU+GPU queries), Rue du Commerce's search handles a
        # combined query well: verified live that "Ryzen 7 5700X RTX 4060"
        # returned 48 listings in the "PC" category, the large majority of
        # which are complete PC builds actually containing both parts (with
        # some near-miss noise -- RTX 4060 Ti, Ryzen 7 9700X -- typical of
        # this marketplace's fuzzy relevance ranking, similar to TopAchat/
        # PcComponentes). So, like those two, both models are kept together.
        query = f"{cpu_model} {gpu_model}"
        url = SEARCH_URL.format(query=requests.utils.quote(query))
        response = requests.get(url, headers=HEADERS, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        prices = []
        # No JSON API, no data-price attribute, no itemprop="price", and no
        # product-level JSON-LD block -- verified against the fixture (only
        # plain-text prices inside "div.price" containers). Each result is a
        # "li.pdt-item" card. A discounted product renders
        # <div class="price"><div class="old-price">...</div>
        # <div class="new-price">...</div></div> (old-price is the
        # struck-through original, new-price is the current price to use);
        # a non-discounted product just renders a plain nested
        # <div class="price"><div class="price">1&nbsp;299,00€</div></div>.
        # Both variants also carry a "sr-only" label span ("Nouveau prix :")
        # that must be stripped before reading the text, and the price text
        # itself uses a non-breaking space as the thousands separator and a
        # comma as the decimal separator (e.g. "1 639,90€").
        for card in soup.select("li.pdt-item"):
            price_container = card.select_one("div.price")
            if price_container is None:
                continue
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
                price = float(raw_price)
            except ValueError:
                continue
            prices.append(price)
        return prices
    except Exception:
        return []
