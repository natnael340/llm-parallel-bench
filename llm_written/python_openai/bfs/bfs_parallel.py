from typing import List, Dict, Iterable, Tuple, Deque
import os
from collections import deque
from concurrent.futures import ProcessPoolExecutor

class Graph:
    def __init__(self) -> None:
        self.vertices: Dict[int, list[int]] = {}
    
    def add_edge(self, from_vertex: int, to_vertex: int) -> None:
        if from_vertex not in self.vertices:
            self.vertices[from_vertex] = []
        if to_vertex not in self.vertices:
            self.vertices[to_vertex] = []
        self.vertices[from_vertex].append(to_vertex)
        self.vertices[to_vertex].append(from_vertex)


def _filter_neighbors_chunk(args: Tuple[list[int], frozenset[int]]) -> list[int]:
    chunk, visited_frozen = args
    # Preserve original order within the chunk
    return [n for n in chunk if n not in visited_frozen]


def _partition(lst: list[int], parts: int) -> list[list[int]]:
    if parts <= 1 or len(lst) == 0:
        return [lst]
    n = len(lst)
    # Balanced contiguous chunks to preserve global order after concatenation
    base, rem = divmod(n, parts)
    chunks = []
    start = 0
    for i in range(parts):
        size = base + (1 if i < rem else 0)
        if size == 0:
            continue
        end = start + size
        chunks.append(lst[start:end])
        start = end
    return chunks


def bfs(graph: Graph, start_vertex: int) -> list[int]:
    if start_vertex not in graph.vertices:
        return []

    visited = set()
    result: list[int] = []
    queue: Deque[int] = deque([start_vertex])

    # Parallelism controls
    max_workers = max(1, min((os.cpu_count() or 1), 32))
    parallel_threshold = 1024  # only parallelize very large adjacency scans

    # Create a single executor per BFS call to amortize startup costs
    executor: ProcessPoolExecutor | None = None
    if max_workers > 1:
        executor = ProcessPoolExecutor(max_workers=max_workers)
    
    try:
        while queue:
            current = queue.popleft()
            if current not in visited:
                visited.add(current)
                result.append(current)
                neighbors = graph.vertices.get(current, [])

                # Small-input fast path or no parallel resources
                if executor is None or len(neighbors) < parallel_threshold:
                    for neighbor in neighbors:
                        if neighbor not in visited:
                            queue.append(neighbor)
                else:
                    # Partition neighbors into contiguous chunks and filter in parallel
                    chunks = _partition(neighbors, max_workers)
                    visited_frozen = frozenset(visited)
                    # Submit all chunks and collect results in the same order to preserve determinism
                    futures_args = [(chunk, visited_frozen) for chunk in chunks]
                    mapped = executor.map(_filter_neighbors_chunk, futures_args)
                    # Concatenate in chunk order
                    for filtered in mapped:
                        if filtered:
                            queue.extend(filtered)
    finally:
        if executor is not None:
            executor.shutdown(wait=True, cancel_futures=False)

    return result
