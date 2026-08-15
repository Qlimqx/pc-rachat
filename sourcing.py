import ebay_client
import retailers


def make_new_pc_search_fn(client_id, client_secret):
    def ebay_new_search(cpu_model, gpu_model):
        return ebay_client.search_new_pc_prices(cpu_model, gpu_model, client_id, client_secret)

    return [ebay_new_search] + retailers.ALL_SEARCH_FUNCTIONS


def make_ram_search_fn(client_id, client_secret):
    def ebay_ram_search(ram_go, ram_type):
        return ebay_client.search_ram_prices(ram_go, ram_type, client_id, client_secret)

    return [ebay_ram_search] + retailers.ALL_RAM_SEARCH_FUNCTIONS


def make_storage_search_fn(client_id, client_secret):
    def ebay_storage_search(storage_go, storage_type):
        return ebay_client.search_storage_prices(storage_go, storage_type, client_id, client_secret)

    return [ebay_storage_search] + retailers.ALL_STORAGE_SEARCH_FUNCTIONS
