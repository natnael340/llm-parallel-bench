from concurrent.futures import ProcessPoolExecutor
from typing import List, Tuple

def _search_in_chunk(chunk: Tuple[int, List[int]], target: int) -> int:
    chunk_start, sub_array = chunk
    for i, value in enumerate(sub_array):
        if value == target:
            return chunk_start + i
    return -1

def linear_search_parallel(arr: List[int], target: int) -> int:
    if len(arr) == 0:
        return -1
    
    num_workers = min(4, len(arr))  # Using 4 as an arbitrary small number

    # Quickly return using sequential path for small inputs (threshold size can be tuned)
    if len(arr) < 20:
        for i in range(len(arr)):
            if arr[i] == target:
                return i
        return -1

    chunk_size = (len(arr) + num_workers - 1) // num_workers
    chunks = [
        (i * chunk_size, arr[i * chunk_size : (i + 1) * chunk_size]) 
        for i in range(num_workers)
    ]

    with ProcessPoolExecutor() as executor:
        futures = [
            executor.submit(_search_in_chunk, chunk, target) for chunk in chunks
        ]
        # Iterate through completed futures
        for future in futures:
            result = future.result()
            if result != -1:
                return result
    return -1
