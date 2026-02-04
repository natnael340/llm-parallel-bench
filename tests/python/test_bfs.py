import logging
import os
import timeit, gc, statistics as stats
from typing import Callable

import unittest
from BFS.python.bfs_seq import Graph, bfs as sbfs

#--------------------------------BFS PARALLEL -------------------#
import multiprocessing
from concurrent.futures import ProcessPoolExecutor
from typing import Dict, List, Set

# Threshold to switch from parallel to sequential execution for small frontiers.
# This avoids the overhead of process management for trivial work.
MIN_FRONTIER_SIZE_FOR_PARALLEL = 16
CPU_COUNT = multiprocessing.cpu_count()

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

def pbfs(graph: Graph, start_vertex: int) -> List[int]:
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


#--------------------------------BFS PARALLEL -------------------#


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

ALGOS = {"seq": sbfs, "par": pbfs}
ALGO_CHOICE = os.environ.get("ALGO_CHOICE", "seq")
bfs: Callable = ALGOS[ALGO_CHOICE]

logger.info(f"Using BFS algorithm: {ALGO_CHOICE}")


class TestBFS(unittest.TestCase):
    def setUp(self):
        self.graph = Graph()

    def test_bfs_empty_graph(self):
        
        result = bfs(self.graph, 0)
        self.assertEqual(result, [])

    def test_bfs_single_node(self):
        self.graph.add_edge(1, 1)
        result = bfs(self.graph, 1)
        self.assertEqual(result, [1])

    def test_bfs_linear_edge(self):
        self.graph.add_edge(1, 2)
        self.graph.add_edge(2, 3)
        self.graph.add_edge(3, 4)

        result = bfs(self.graph, 1)
        self.assertEqual(result, [1, 2, 3, 4])

    def test_bfs_complete_graph(self):
        expected = [1, 2, 3, 4]
        for i in expected:
             for j in expected:
                if i != j:
                    self.graph.add_edge(i, j)

        result = bfs(self.graph, 3)
        self.assertEqual(result, [3, 1, 2, 4])

    def test_bfs_star_graph(self):
        """Test BFS on star graph (one central vertex connected to all others)."""
        center = 1
        leaves = [2, 3, 4, 5]
        for leaf in leaves:
            self.graph.add_edge(center, leaf)
        
        result = bfs(self.graph, center)
        self.assertEqual(result, [center] + leaves)

    def test_bfs_cycle(self):
        """Test BFS on cyclic graph."""
        edges = [(1, 2), (2, 3), (3, 4), (4, 1)]
        for from_v, to_v in edges:
            self.graph.add_edge(from_v, to_v)
        
        result = bfs(self.graph, 1)
        self.assertEqual(result, [1, 2, 4, 3])
    
    def test_bfs_tree_structure(self):
        """Test BFS on tree structure."""
        # Create binary tree: 1 as root, 2,3 as children of 1, 4,5 children of 2, 6,7 children of 3
        edges = [(1, 2), (1, 3), (2, 4), (2, 5), (3, 6), (3, 7)]
        for from_v, to_v in edges:
            self.graph.add_edge(from_v, to_v)
        
        result = bfs(self.graph, 1)
        self.assertEqual(result, [1, 2, 3, 4, 5, 6, 7])

    def test_bfs_disconnected_components(self):
        """Test BFS on graph with multiple disconnected components."""
        # Component 1: 1-2-3
        self.graph.add_edge(1, 2)
        self.graph.add_edge(2, 3)
        # Component 2: 4-5 (disconnected)
        self.graph.add_edge(4, 5)
        self.graph.add_edge(4, 6)
        
        result = bfs(self.graph, 1)
        self.assertEqual(result, [1, 2, 3])  # Should only visit connected component
        
        result2 = bfs(self.graph, 4)
        self.assertEqual(result2, [4, 5, 6])

    def test_bfs_duplicate_edges(self):
        """Test BFS with duplicate edges (multiple edges between same vertices)."""
        self.graph.add_edge(1, 2)
        self.graph.add_edge(1, 2)  # Duplicate
        self.graph.add_edge(2, 3)
        
        result = bfs(self.graph, 1)
        self.assertEqual(result, [1, 2, 3])

    def test_bfs_nonexistent_start_vertex(self):
        """Test BFS starting from vertex that doesn't exist in graph."""
        self.graph.add_edge(1, 2)
        
        result = bfs(self.graph, 999)
        self.assertEqual(result, [])

    def test_bfs_complex_graph(self):
        """Test BFS on complex graph with multiple paths and cycles."""
        # Create a more complex graph
        edges = [
            (1, 2), (1, 3), (2, 4), (3, 4), (4, 5), 
            (5, 6), (6, 7), (5, 7), (7, 8), (3, 8)
        ]
        for from_v, to_v in edges:
            self.graph.add_edge(from_v, to_v)
        
        result = bfs(self.graph, 1)

        self.assertEqual(result, [1, 2, 3, 4, 8, 5, 7, 6])

    def test_bfs_order_consistency(self):
        """Test that BFS maintains consistent order for same-level vertices."""
        # Create graph where order matters for testing consistency
        self.graph.add_edge(1, 3)
        self.graph.add_edge(1, 2)  # Added after 3, should still be processed consistently
        
        # Run multiple times to check consistency
        results = [bfs(self.graph, 1) for _ in range(5)]

        for result in results:
            self.assertEqual(results[0], result)
        
    
    def test_bfs_performance_stress_test(self):
        """Test BFS on larger graph for basic performance validation."""
        # Create a larger connected graph (linear chain)
        size = 1000
        for i in range(1, size):
            self.graph.add_edge(i, i + 1)
        
        result = bfs(self.graph, 1)
        self.assertEqual(len(result), size)
        self.assertEqual(result[0], 1)
        self.assertEqual(result[-1], size)

    def test_bfs_performance_speed_test(self):
        # Create a larger connected graph 
        size = 2000
        for i in range(1, size+1):
            for j in range(i+1, size+1):
                self.graph.add_edge(i, j)
                self.graph.add_edge(j, i)
    
        #warm-up
        bfs(self.graph, 1)

        reps=5
        iters = 20

        results = timeit.repeat(lambda: bfs(self.graph, 1), repeat=reps, number=iters)
        
        
        per_run_ms = [(t / iters) * 1000 for t in results]
        avg = stats.mean(per_run_ms)
        sd = stats.pstdev(per_run_ms)
    
        print(f"BFS complete graph | nodes={size}, undirected edges≈{size*(size-1)//2:,} "
          f"(directed≈{size*(size-1):,}) | {avg:.2f} ms/run ± {sd:.2f} (n={reps})")

    