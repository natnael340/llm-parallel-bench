from typing import List
from concurrent.futures import ProcessPoolExecutor, as_completed
import os


def worker(arr_slice: List[int], target: int, base_index: int) -> int:
    for i, value in enumerate(arr_slice):
        if value == target:
            return base_index + i
    return -1


def linear_search_parallel(arr: List[int], target: int) -> int:
    if len(arr) <= 1:  # Small input fast path
        return linear_search(arr, target)

    num_workers = min(os.cpu_count() or 1, len(arr))
    chunk_size = (len(arr) + num_workers - 1) // num_workers  # Ceiling division to split tasks

    with ProcessPoolExecutor(max_workers=num_workers) as executor:
        futures = {
            executor.submit(worker, arr[i:i + chunk_size], target, i): i
            for i in range(0, len(arr), chunk_size)
        }

        for future in as_completed(futures):
            result = future.result()
            if result != -1:
                # Cancel other futures as soon as we found the target
                for f in futures:
                    f.cancel()
                return result

    return -1


def linear_search(arr: List[int], target: int) -> int:
    for i in range(len(arr)):
        if arr[i] == target:
            return i
    return -1


if __name__ == "__main__":
    import sys
    try:
        arr = list(map(int, sys.argv[1:-1]))
        target = int(sys.argv[-1])
        print("Result (Parallel):", linear_search_parallel(arr, target))
    except Exception as e:
        print("Error:", e)
