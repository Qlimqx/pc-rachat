import ebay_client
import retailers


def make_new_pc_search_fn(client_id, client_secret):
    def ebay_new_search(cpu_model, gpu_model):
        return ebay_client.search_new_pc_prices(cpu_model, gpu_model, client_id, client_secret)

    return [ebay_new_search] + retailers.ALL_SEARCH_FUNCTIONS
