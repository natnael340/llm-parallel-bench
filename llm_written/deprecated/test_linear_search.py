import random
from linear_search_sequential import linear_search as linear_search_sequential
from linear_search_parallel import linear_search_parallel

def test_linear_search():
    # Test cases: edge cases and representative inputs
    test_cases = [
        ([], 5),         # Empty list
        ([5], 5),        # Single-element match
        ([5], 3),        # Single-element no match
        ([1, 2, 3, 4, 5], 3),  # Multiple elements
        ([1, 2, 3, 4, 5], 6),  # No match in multiple elements
    ]
    for arr, target in test_cases:
        assert linear_search_parallel(arr, target) == linear_search_sequential(arr, target)

    # Larger list, target at the end
    large_list = list(range(1000))
    assert linear_search_parallel(large_list, 999) == linear_search_sequential(large_list, 999)

    # Randomized tests
    random.seed(42)
    for _ in range(10):  # Multiple deterministic random tests
        arr = random.sample(range(10000), 1000)  # Unique random numbers
        target = random.choice(arr)
        assert linear_search_parallel(arr, target) == linear_search_sequential(arr, target)

    print("All tests passed.")

if __name__ == "__main__":
    test_linear_search()