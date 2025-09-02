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


def bfs(graph: Graph, start_vertex: int) -> list[int]:
    if start_vertex not in graph.vertices:
        return []
    
    visited = set()
    result = []
    queue = [start_vertex]
    while queue:
        current = queue.pop(0)
        if current not in visited:
            visited.add(current)
            result.append(current)
            for neighbor in graph.vertices.get(current, []):
                if neighbor not in visited:
                    queue.append(neighbor)

    return result