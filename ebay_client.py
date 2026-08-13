import requests

TOKEN_URL = "https://api.ebay.com/identity/v1/oauth2/token"
BROWSE_SEARCH_URL = "https://api.ebay.com/buy/browse/v1/item_summary/search"


def get_access_token(client_id, client_secret):
    response = requests.post(
        TOKEN_URL,
        auth=(client_id, client_secret),
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        data={
            "grant_type": "client_credentials",
            "scope": "https://api.ebay.com/oauth/api_scope",
        },
        timeout=10,
    )
    response.raise_for_status()
    return response.json()["access_token"]


USED_CONDITION_IDS = "3000|4000|5000|6000"
NEW_CONDITION_IDS = "1000"


def _search_by_condition(query, token, condition_ids, limit=20):
    response = requests.get(
        BROWSE_SEARCH_URL,
        headers={
            "Authorization": f"Bearer {token}",
            "X-EBAY-C-MARKETPLACE-ID": "EBAY_FR",
        },
        params={
            "q": query,
            "filter": f"conditionIds:{{{condition_ids}}}",
            "limit": limit,
        },
        timeout=10,
    )
    response.raise_for_status()
    data = response.json()
    return [float(item["price"]["value"]) for item in data.get("itemSummaries", [])]


def search_used_prices(query, token, limit=20):
    return _search_by_condition(query, token, USED_CONDITION_IDS, limit)


def search_new_prices(query, token, limit=20):
    return _search_by_condition(query, token, NEW_CONDITION_IDS, limit)


def search_component_price(model, category, client_id, client_secret):
    try:
        token = get_access_token(client_id, client_secret)
        return search_used_prices(f"{model} {category}", token)
    except Exception:
        return None


def search_new_pc_prices(cpu_model, gpu_model, client_id, client_secret):
    try:
        token = get_access_token(client_id, client_secret)
        return search_new_prices(f"{cpu_model} {gpu_model} PC", token)
    except Exception:
        return []
