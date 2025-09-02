import random
from llm_written.deprecated.algo_parallel import linear_search_parallel
from typing import List

def linear_search(arr: List[int], target: int) -> int:
    for i in range(len(arr)):
        if arr[i] == target:
            return i
    return -1

def test_linear_search():
    # Basic test cases
    assert linear_search_parallel([1, 2, 3, 4, 5], 3) == 2
    assert linear_search_parallel([1, 2, 3, 4, 5], 6) == -1
    assert linear_search_parallel([], 1) == -1
    assert linear_search_parallel([1, 1, 1, 1], 1) == 0  # First occurrence

    # Edge cases
    large_list = list(range(10000))
    random.shuffle(large_list)
    for target in (50, 999, 5000, 9999):
        assert linear_search_parallel(large_list, target) == linear_search(large_list, target)

    print("All tests passed.")

if __name__ == "__main__":
    test_linear_search()
