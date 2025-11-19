from typing import Dict, List, Set

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

def bfs(graph: Graph, start_vertex: int) -> List[int]:
    """
    A deterministic, level-synchronous implementation of BFS.
    
    This version is used as a baseline for the parallel implementation. It ensures
    an identical, deterministic output by sorting the nodes that form the next
    frontier at each level of the traversal.
    """
    if start_vertex not in graph.vertices:
        return []
    
    visited: Set[int] = {start_vertex}
    result: List[int] = [start_vertex]
    frontier: List[int] = [start_vertex]
    
    while frontier:
        next_level_candidates = []
        for node in frontier:
            next_level_candidates.extend(graph.vertices.get(node, []))
        
        # Filter out visited nodes and sort the result to ensure a
        # deterministic traversal order, which is critical for testing.
        next_frontier = sorted([
            n for n in set(next_level_candidates) if n not in visited
        ])

        if not next_frontier:
            break
            
        visited.update(next_frontier)
        result.extend(next_frontier)
        frontier = next_frontier
        
    return result
