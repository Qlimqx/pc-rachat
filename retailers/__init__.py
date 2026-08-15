from retailers.ldlc import search_prices as ldlc_search
from retailers.ldlc import search_ram_prices as ldlc_ram_search
from retailers.ldlc import search_storage_prices as ldlc_storage_search
from retailers.ldlc import search_cpu_prices as ldlc_cpu_search
from retailers.ldlc import search_gpu_prices as ldlc_gpu_search
from retailers.pccomponentes import search_prices as pccomponentes_search
from retailers.pccomponentes import search_ram_prices as pccomponentes_ram_search
from retailers.pccomponentes import search_storage_prices as pccomponentes_storage_search
from retailers.pccomponentes import search_cpu_prices as pccomponentes_cpu_search
from retailers.pccomponentes import search_gpu_prices as pccomponentes_gpu_search
from retailers.materiel_net import search_prices as materiel_net_search
from retailers.materiel_net import search_ram_prices as materiel_net_ram_search
from retailers.materiel_net import search_storage_prices as materiel_net_storage_search
from retailers.materiel_net import search_cpu_prices as materiel_net_cpu_search
from retailers.materiel_net import search_gpu_prices as materiel_net_gpu_search
from retailers.topachat import search_prices as topachat_search
from retailers.topachat import search_ram_prices as topachat_ram_search
from retailers.topachat import search_storage_prices as topachat_storage_search
from retailers.topachat import search_cpu_prices as topachat_cpu_search
from retailers.topachat import search_gpu_prices as topachat_gpu_search
from retailers.grosbill import search_prices as grosbill_search
from retailers.grosbill import search_ram_prices as grosbill_ram_search
from retailers.grosbill import search_storage_prices as grosbill_storage_search
from retailers.grosbill import search_cpu_prices as grosbill_cpu_search
from retailers.grosbill import search_gpu_prices as grosbill_gpu_search
from retailers.rueducommerce import search_prices as rueducommerce_search
from retailers.rueducommerce import search_ram_prices as rueducommerce_ram_search
from retailers.rueducommerce import search_storage_prices as rueducommerce_storage_search
from retailers.rueducommerce import search_cpu_prices as rueducommerce_cpu_search
from retailers.rueducommerce import search_gpu_prices as rueducommerce_gpu_search
from retailers.amazon import search_prices as amazon_search
from retailers.amazon import search_ram_prices as amazon_ram_search
from retailers.amazon import search_storage_prices as amazon_storage_search
from retailers.amazon import search_cpu_prices as amazon_cpu_search
from retailers.amazon import search_gpu_prices as amazon_gpu_search

ALL_SEARCH_FUNCTIONS = [
    ldlc_search,
    pccomponentes_search,
    materiel_net_search,
    topachat_search,
    grosbill_search,
    rueducommerce_search,
    amazon_search,
]

ALL_RAM_SEARCH_FUNCTIONS = [
    ldlc_ram_search,
    pccomponentes_ram_search,
    materiel_net_ram_search,
    topachat_ram_search,
    grosbill_ram_search,
    rueducommerce_ram_search,
    amazon_ram_search,
]

ALL_STORAGE_SEARCH_FUNCTIONS = [
    ldlc_storage_search,
    pccomponentes_storage_search,
    materiel_net_storage_search,
    topachat_storage_search,
    grosbill_storage_search,
    rueducommerce_storage_search,
    amazon_storage_search,
]

ALL_CPU_SEARCH_FUNCTIONS = [
    ldlc_cpu_search,
    pccomponentes_cpu_search,
    materiel_net_cpu_search,
    topachat_cpu_search,
    grosbill_cpu_search,
    rueducommerce_cpu_search,
    amazon_cpu_search,
]

ALL_GPU_SEARCH_FUNCTIONS = [
    ldlc_gpu_search,
    pccomponentes_gpu_search,
    materiel_net_gpu_search,
    topachat_gpu_search,
    grosbill_gpu_search,
    rueducommerce_gpu_search,
    amazon_gpu_search,
]
