from typing import List, Optional


def linear_search_sublist(sublist: List[int], target: int, start_index: int) -> Optional[int]:
    """
    Performs a linear search on a sublist of integers.

    :param sublist: The list of integers to search.
    :param target: The integer value to search for.
    :param start_index: The starting index of the sublist in the original list.
    :return: The index in the original list if the target is found; None otherwise.
    """
    for i, value in enumerate(sublist):
        if value == target:
            return start_index + i
    return None


def main():
    sublist = [10, 20, 30, 40, 50]
    target = 30
    start_index = 5
    result = linear_search_sublist(sublist, target, start_index)
    if result is not None:
        print(f"Target {target} found at index {result} in the original list.")
    else:
        print(f"Target {target} not found in the sublist.")


if __name__ == "__main__":
    main()