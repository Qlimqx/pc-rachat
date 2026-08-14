from retailers.ldlc import search_prices as ldlc_search
from retailers.pccomponentes import search_prices as pccomponentes_search
from retailers.materiel_net import search_prices as materiel_net_search
from retailers.topachat import search_prices as topachat_search
from retailers.grosbill import search_prices as grosbill_search
from retailers.rueducommerce import search_prices as rueducommerce_search
from retailers.amazon import search_prices as amazon_search

ALL_SEARCH_FUNCTIONS = [
    ldlc_search,
    pccomponentes_search,
    materiel_net_search,
    topachat_search,
    grosbill_search,
    rueducommerce_search,
    amazon_search,
]
