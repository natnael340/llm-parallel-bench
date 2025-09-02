from typing import List
from concurrent.futures import ProcessPoolExecutor, as_completed

def chunked_search(chunk: List[int], target: int, offset: int) -> int:
    for i, value in enumerate(chunk):
        if value == target:
            return i + offset  # Return the index adjusted to the original list
    return -1

def parallel_linear_search(arr: List[int], target: int) -> int:
    if len(arr) < 1000:  # Fallback to sequential search for small arrays
        for i in range(len(arr)):
            if arr[i] == target:
                return i
        return -1

    num_workers = min(8, len(arr))  # Limit the number of workers
    chunk_size = (len(arr) + num_workers - 1) // num_workers

    with ProcessPoolExecutor(max_workers=num_workers) as executor:
        futures = [executor.submit(chunked_search, arr[i:i + chunk_size], target, i)
                   for i in range(0, len(arr), chunk_size)]

        for future in as_completed(futures):
            result = future.result()
            if result != -1:
                return result

    return -1
