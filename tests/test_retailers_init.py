from retailers import ALL_SEARCH_FUNCTIONS


def test_all_search_functions_lists_seven_callables():
    assert len(ALL_SEARCH_FUNCTIONS) == 7
    assert all(callable(fn) for fn in ALL_SEARCH_FUNCTIONS)
