from collections import deque
from concurrent.futures import ProcessPoolExecutor
import multiprocessing
import os

class Graph:
    def __init__(self) -> None:
        self.vertices: dict[int, list[int]] = {}
    
    def add_edge(self, from_vertex: int, to_vertex: int) -> None:
        if from_vertex not in self.vertices:
            self.vertices[from_vertex] = []
        if to_vertex not in self.vertices:
            self.vertices[to_vertex] = []
        self.vertices[from_vertex].append(to_vertex)
        self.vertices[to_vertex].append(from_vertex)


def _explore_vertices_batch(vertices: list[int], graph_vertices: dict[int, list[int]], visited: set[int]) -> list[int]:
    """Explore neighbors of a batch of vertices, return unvisited neighbors."""
    result = []
    for vertex in vertices:
        neighbors = graph_vertices.get(vertex, [])
        for n in neighbors:
            if n not in visited:
                result.append(n)
    return result


def bfs_parallel(graph: Graph, start_vertex: int) -> list[int]:
    """
    Level-synchronous parallel BFS.
    Processes each level in parallel, maintaining deterministic order within levels.
    """
    if start_vertex not in graph.vertices:
        return []
    
    # Determine worker count
    max_workers = min(multiprocessing.cpu_count(), 
                      int(os.environ.get('BFS_MAX_WORKERS', multiprocessing.cpu_count())))
    
    visited = set()
    result = []
    current_level = [start_vertex]
    
    while current_level:
        # Sort current level for deterministic processing order
        current_level = sorted(current_level)
        
        # Mark all vertices in current level as visited and add to result
        new_visited = []
        for vertex in current_level:
            if vertex not in visited:
                visited.add(vertex)
                new_visited.append(vertex)
        
        result.extend(new_visited)
        
        # Sequential fallback for small levels
        if len(new_visited) <= 100:
            next_level_set = set()
            for vertex in new_visited:
                for neighbor in graph.vertices.get(vertex, []):
                    if neighbor not in visited and neighbor not in next_level_set:
                        next_level_set.add(neighbor)
            current_level = sorted(next_level_set)
        else:
            # Parallel exploration of neighbors with batching
            next_level_set = set()
            
            # Divide vertices into chunks for parallel processing
            chunk_size = max(1, len(new_visited) // (max_workers * 4))
            chunks = [new_visited[i:i+chunk_size] for i in range(0, len(new_visited), chunk_size)]
            
            with ProcessPoolExecutor(max_workers=max_workers) as executor:
                # Submit chunk tasks
                futures = []
                for chunk in chunks:
                    future = executor.submit(_explore_vertices_batch, chunk, graph.vertices, visited)
                    futures.append(future)
                
                # Collect results in submission order (deterministic)
                for future in futures:
                    neighbors = future.result()
                    for neighbor in neighbors:
                        if neighbor not in next_level_set:
                            next_level_set.add(neighbor)
            
            current_level = sorted(next_level_set)
    
    return result


# Alias for standard interface
def bfs(graph: Graph, start_vertex: int) -> list[int]:
    return bfs_parallel(graph, start_vertex)
