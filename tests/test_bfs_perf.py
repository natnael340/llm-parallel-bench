import timeit
from BFS.bfs_seq import bfs, Graph

def setup_graph():
    size = 10000
    graph = Graph()
    for i in range(1, size):
        for j in range(i+1, min(i + 10, size)):
            graph.add_edge(i, j)
    
    return graph

def run_bfs_performance_test(graph, start_vertex):
    result = bfs(graph, start_vertex)
    
    return result

if __name__ == "__main__":
    graph = setup_graph()
    execution_time = timeit.timeit(lambda: run_bfs_performance_test(graph, 1), number=100)

    print(f"Average BFS Performance Test Duration: {execution_time / 100} seconds")