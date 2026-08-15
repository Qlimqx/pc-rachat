from retailers import (
    ALL_SEARCH_FUNCTIONS,
    ALL_RAM_SEARCH_FUNCTIONS,
    ALL_STORAGE_SEARCH_FUNCTIONS,
    ALL_CPU_SEARCH_FUNCTIONS,
    ALL_GPU_SEARCH_FUNCTIONS,
)


def test_all_search_functions_lists_seven_callables():
    assert len(ALL_SEARCH_FUNCTIONS) == 7
    assert all(callable(fn) for fn in ALL_SEARCH_FUNCTIONS)


def test_all_ram_search_functions_lists_seven_callables():
    assert len(ALL_RAM_SEARCH_FUNCTIONS) == 7
    assert all(callable(fn) for fn in ALL_RAM_SEARCH_FUNCTIONS)


def test_all_storage_search_functions_lists_seven_callables():
    assert len(ALL_STORAGE_SEARCH_FUNCTIONS) == 7
    assert all(callable(fn) for fn in ALL_STORAGE_SEARCH_FUNCTIONS)


def test_all_cpu_search_functions_lists_seven_callables():
    assert len(ALL_CPU_SEARCH_FUNCTIONS) == 7
    assert all(callable(fn) for fn in ALL_CPU_SEARCH_FUNCTIONS)


def test_all_gpu_search_functions_lists_seven_callables():
    assert len(ALL_GPU_SEARCH_FUNCTIONS) == 7
    assert all(callable(fn) for fn in ALL_GPU_SEARCH_FUNCTIONS)
