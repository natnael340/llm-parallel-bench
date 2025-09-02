from concurrent.futures import ProcessPoolExecutor, as_completed
from multiprocessing import Manager
from collections import deque
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

def explore_neighbors(current, graph, visited, lock):
    new_neighbors = []
    for neighbor in sorted(graph.vertices.get(current, [])):  # Sort for deterministic order
        with lock:
            if neighbor not in visited:
                visited.add(neighbor)
                new_neighbors.append(neighbor)
    return new_neighbors

def bfs(graph: Graph, start_vertex: int) -> list[int]:
    if start_vertex not in graph.vertices:
        return []

    # Sequential fast path for small graphs
    if len(graph.vertices) <= 10:
        visited = set()
        result = []
        queue = deque([start_vertex])
        while queue:
            current = queue.popleft()
            if current not in visited:
                visited.add(current)
                result.append(current)
                for neighbor in sorted(graph.vertices.get(current, [])):  # Sort for deterministic order
                    if neighbor not in visited:
                        queue.append(neighbor)
        return result

    # Parallel BFS for larger graphs
    manager = Manager()
    visited = manager.set()  # Use a set for O(1) membership checks
    lock = manager.Lock()
    result = []
    queue = deque([start_vertex])
    visited.add(start_vertex)

    while queue:
        next_level = deque()
        with ProcessPoolExecutor(max_workers=os.cpu_count()) as executor:
            futures = {executor.submit(explore_neighbors, node, graph, visited, lock): node for node in queue}
            for future in as_completed(futures):
                new_neighbors = future.result()
                next_level.extend(new_neighbors)

        # Sort next_level to maintain order
        result.extend(sorted(queue))
        queue = deque(sorted(next_level))

    return result

# Ensure the code runs correctly when executed as a script
if __name__ == "__main__":
    g = Graph()
    g.add_edge(0, 1)
    g.add_edge(0, 2)
    g.add_edge(1, 3)
    g.add_edge(2, 3)
    g.add_edge(3, 4)

    # Call bfs inside the main block
    result = bfs(g, 0)
    print(result)