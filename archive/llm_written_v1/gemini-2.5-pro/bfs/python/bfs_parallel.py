import multiprocessing
from concurrent.futures import ProcessPoolExecutor
from typing import Dict, List, Set

# Threshold to switch from parallel to sequential execution for small frontiers.
# This avoids the overhead of process management for trivial work.
MIN_FRONTIER_SIZE_FOR_PARALLEL = 16
CPU_COUNT = multiprocessing.cpu_count()

class Graph:
    """
    A simple graph representation using an adjacency list.
    The graph is assumed to be undirected.
    """
    def __init__(self) -> None:
        self.vertices: Dict[int, List[int]] = {}
    
    def add_edge(self, from_vertex: int, to_vertex: int) -> None:
        if from_vertex not in self.vertices:
            self.vertices[from_vertex] = []
        if to_vertex not in self.vertices:
            self.vertices[to_vertex] = []
        self.vertices[from_vertex].append(to_vertex)
        self.vertices[to_vertex].append(from_vertex)

def _expand_frontier_chunk(
    chunk: List[int],
    graph_vertices: Dict[int, List[int]],
) -> List[int]:
    """
    Worker function to find all neighbors of a given chunk of nodes.
    This function is executed in a separate process.
    """
    neighbors = []
    for node in chunk:
        neighbors.extend(graph_vertices.get(node, []))
    return neighbors

def bfs(graph: Graph, start_vertex: int) -> List[int]:
    """
    Performs a parallel, level-synchronous Breadth-First Search (BFS).

    The traversal is deterministic because at each level, the next set of nodes
    to visit (the frontier) is sorted. This ensures a consistent traversal
    order regardless of the number of parallel workers or scheduling.

    For small frontiers, the expansion is done sequentially to avoid the
    overhead of process creation.
    """
    if start_vertex not in graph.vertices:
        return []
    
    visited: Set[int] = {start_vertex}
    result: List[int] = [start_vertex]
    frontier: List[int] = [start_vertex]
    
    # We use a shared executor instance for the entire BFS traversal
    with ProcessPoolExecutor(max_workers=CPU_COUNT) as executor:
        while frontier:
            # Small-input fast path: process small frontiers sequentially
            if len(frontier) < MIN_FRONTIER_SIZE_FOR_PARALLEL:
                next_level_candidates = []
                for node in frontier:
                    next_level_candidates.extend(graph.vertices.get(node, []))
            else:
                # Partition the frontier for parallel processing
                chunk_size = (len(frontier) + CPU_COUNT - 1) // CPU_COUNT
                chunks = [
                    frontier[i:i + chunk_size]
                    for i in range(0, len(frontier), chunk_size)
                ]
                
                # Submit tasks to the process pool
                futures = [
                    executor.submit(
                        _expand_frontier_chunk, chunk, graph.vertices
                    )
                    for chunk in chunks
                ]
                
                # Collect results
                next_level_candidates = []
                for future in futures:
                    next_level_candidates.extend(future.result())

            # Filter out visited nodes, find unique neighbors, and sort for determinism
            # This sorting step is critical for a deterministic output
            next_frontier = sorted(
                list(set(n for n in next_level_candidates if n not in visited))
            )
            
            if not next_frontier:
                break
                
            visited.update(next_frontier)
            result.extend(next_frontier)
            frontier = next_frontier
            
    return result
