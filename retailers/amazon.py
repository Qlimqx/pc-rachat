import re

import requests
from bs4 import BeautifulSoup

# Amazon.fr's search is a classic server-rendered `/s?k=...` page (no
# separate JSON API involved), with no product-level JSON-LD block -- so,
# like Grosbill/Rue du Commerce, this scrapes plain HTML.
#
# KEY DIFFERENCE from the other 6 retailers in this module: verified live
# that Amazon sits behind an AWS WAF bot challenge. A plain `requests.get()`
# with a browser User-Agent (exactly what this module sends -- no cookies,
# no JS execution) got back an HTTP 202 with `x-amzn-waf-action: challenge`
# and a body that's just a JS challenge page (window.gokuProps / challenge.js
# / "we need to verify that you're not a robot" noscript fallback) -- no
# product data at all. A real browser (full JS engine, cookies) sailed
# through to real results on the same query, which is exactly what confirms
# this is anti-bot gating, not a broken selector. That challenge page is
# what's saved as tests/fixtures/amazon_search.html.
#
# This is an ACCEPTED, expected outcome for this scraper (per the design
# spec) -- not a bug to work around. No CAPTCHA-solving or bot-evasion logic
# is added here; the module is structured identically to the other 6 and
# simply yields [] when the WAF blocks it, same as it would for any other
# unparseable page. The selectors below (`div[data-component-type=
# "s-search-result"]`, title in `h2 span`, price in `.a-price .a-offscreen`)
# are Amazon's real search-result markup, verified live via a full browser
# render for whenever a request does get through (residential IPs, a
# logged-in session, etc. -- outside this module's control).
SEARCH_URL = "https://www.amazon.fr/s"
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
    """Check whether a product title refers to `model`, the same
    substring-with-boundary check used by rueducommerce.py: spaces in
    `model` become optional (so "RTX 4060" also matches title text
    "RTX4060"), and a match is rejected in two cases: (1) the character
    right after it is alphanumeric with no separating space at all, e.g.
    inside "RTX4060Ti" -- any concatenated alphanumeric suffix is treated
    as extending the model number, since there's no space to prove
    otherwise; or (2) the first word after the match, once any whitespace
    is skipped, is one of a small known list of GPU/CPU suffix qualifiers
    (`_SUFFIX_QUALIFIERS`, e.g. "Ti", "Super", "XT"), so "RTX 4060" also
    doesn't match inside "RTX 4060 Ti" (Ti is a different, more expensive
    card and should not count as a match for a plain "RTX 4060" search).
    Anything else after a space -- e.g. "RTX 4060 16GB" -- is treated as
    unrelated trailing product text and still counts as a match.

    Needed here for the same reason it was needed for Rue du Commerce:
    verified live that Amazon's combined "Ryzen 7 5700X RTX 4060" query
    returns plenty of near-miss builds -- of the 56 results on the first
    results page, 45 mention "5700X" but *zero* mention "4060" at all (the
    listed builds pair this CPU with newer cards instead: RTX 5060, RTX 5060
    Ti, RTX 5070, RTX 3050, RX 9060 XT, etc.). Including those prices
    unfiltered would represent the wrong GPU entirely, not just a skew, so
    both the CPU and GPU title checks are required before a price counts.
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
    """Run an Amazon.fr search for `query` and return the parsed result
    page.

    Amazon.fr's search is a classic server-rendered `/s?k=...` page --
    verified live via network inspection, no separate JSON API involved.
    Raises on network failure or a non-2xx response -- callers are expected
    to catch that and translate it into an empty price list, matching every
    other retailer module's contract. Note a 202 (the AWS WAF bot-challenge
    response documented at the top of this module) does not raise here --
    `raise_for_status()` only raises on 4xx/5xx -- so a blocked request
    falls through to soup-parsing an unparseable challenge page, which
    naturally yields zero cards and an empty price list.
    """
    response = requests.get(
        SEARCH_URL, params={"k": query}, headers=HEADERS, timeout=10
    )
    response.raise_for_status()
    return BeautifulSoup(response.text, "html.parser")


def _extract_card_price(card):
    """Extract the float price from a single search-result card (a
    `div[data-component-type="s-search-result"]`), or None if no usable
    price is present. Price text lives in `.a-price .a-offscreen` and uses
    a non-breaking space as the thousands separator, a comma as the decimal
    separator, and a trailing euro sign (e.g. "1\xa0399,90€").
    """
    price_el = card.select_one(".a-price .a-offscreen")
    if price_el is None:
        return None
    raw_price = (
        price_el.get_text(strip=True)
        .replace("\xa0", "")
        .replace(" ", "")
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
        # Kept both models in the query, same as PcComponentes/TopAchat/Rue
        # du Commerce -- Amazon's search doesn't reject the combined query
        # (unlike LDLC/Materiel.net/Grosbill's strict AND-matching, which
        # returns zero results for a combined CPU+GPU search). It just ranks
        # loosely, hence the title-relevance filter below.
        query = f"{cpu_model} {gpu_model}"
        soup = _fetch_soup(query)

        prices = []
        for card in soup.select('div[data-component-type="s-search-result"]'):
            title_el = card.select_one("h2 span")
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
        # Live-researched (2026-08-15) against https://www.amazon.fr/s for
        # "16Go DDR4" and "512Go SSD" (see search_storage_prices below for
        # the latter): both requests were blocked by Amazon's anti-bot
        # protection before any product data was returned -- this time an
        # Akamai Bot Manager "bm-verify" interstitial (HTTP 200, a
        # `<meta http-equiv="refresh">` redirect loop plus a JS
        # proof-of-work challenge, no `s-search-result` cards at all),
        # rather than the AWS WAF challenge documented at the top of this
        # module for the CPU+GPU query -- Amazon appears to front different
        # bot-mitigation vendors/paths depending on the query, IP
        # reputation, or request rate. Either way it's the same accepted,
        # expected outcome: no real product data, no CAPTCHA-solving or
        # bot-evasion added. That response is saved verbatim as
        # tests/fixtures/amazon_ram_search.html. Since no real results ever
        # came back, there's no live noise data to justify a
        # title-relevance filter one way or the other -- mirroring Rue du
        # Commerce's Task 9 default, no filter is applied here.
        soup = _fetch_soup(f"{ram_go}Go {ram_type}")

        prices = []
        for card in soup.select('div[data-component-type="s-search-result"]'):
            price = _extract_card_price(card)
            if price is not None:
                prices.append(price)
        return prices
    except Exception:
        return []


def search_storage_prices(storage_go, storage_type):
    try:
        # Live-researched (2026-08-15) against https://www.amazon.fr/s for
        # "512Go SSD" -- same outcome and same Akamai "bm-verify"
        # interstitial response as search_ram_prices above, saved verbatim
        # as tests/fixtures/amazon_storage_search.html. No real product
        # data came back, so -- same reasoning as search_ram_prices -- no
        # title-relevance filter is applied here either, mirroring Rue du
        # Commerce's Task 9 default.
        soup = _fetch_soup(f"{storage_go}Go {storage_type}")

        prices = []
        for card in soup.select('div[data-component-type="s-search-result"]'):
            price = _extract_card_price(card)
            if price is not None:
                prices.append(price)
        return prices
    except Exception:
        return []
