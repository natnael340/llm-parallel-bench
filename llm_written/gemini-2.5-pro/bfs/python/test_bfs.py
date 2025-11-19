import unittest
import random
import sys
from typing import Callable, List

# Add the directory to the path to allow imports
sys.path.append('.')

# Import the Graph class and the BFS functions to be tested
from bfs_baseline import Graph as BaselineGraph
from bfs_baseline import bfs as bfs_baseline
from bfs_parallel import Graph as ParallelGraph
from bfs_parallel import bfs as bfs_parallel

class TestBFS(unittest.TestCase):

    def run_comparison_test(
        self,
        graph_builder: Callable[[], BaselineGraph],
        start_vertex: int,
        test_name: str
    ):
        """
        Helper function to run a differential test between baseline and parallel BFS.
        It builds the graph, runs both BFS implementations, and asserts that their
        outputs are identical.
        """
        # Create two separate graph instances for the baseline and parallel versions
        baseline_graph = graph_builder()
        parallel_graph = ParallelGraph()
        parallel_graph.vertices = baseline_graph.vertices

        # Run both implementations
        baseline_result = bfs_baseline(baseline_graph, start_vertex)
        parallel_result = bfs_parallel(parallel_graph, start_vertex)

        # Assert that the results are identical
        self.assertEqual(
            baseline_result,
            parallel_result,
            f"Test failed for: {test_name}. "
            f"Baseline result: {baseline_result}, Parallel result: {parallel_result}"
        )
        print(f"PASSED: {test_name}")

    def test_empty_graph(self):
        def build_graph():
            return BaselineGraph()
        self.run_comparison_test(build_graph, 0, "Empty Graph")

    def test_single_node(self):
        def build_graph():
            g = BaselineGraph()
            g.add_edge(0, 0) # Self-loop
            return g
        self.run_comparison_test(build_graph, 0, "Single Node Graph")

    def test_simple_path(self):
        def build_graph():
            g = BaselineGraph()
            g.add_edge(0, 1)
            g.add_edge(1, 2)
            g.add_edge(2, 3)
            return g
        self.run_comparison_test(build_graph, 0, "Simple Path Graph")

    def test_disconnected_component(self):
        def build_graph():
            g = BaselineGraph()
            # Component 1
            g.add_edge(0, 1)
            g.add_edge(1, 2)
            # Component 2
            g.add_edge(10, 11)
            g.add_edge(11, 12)
            return g
        self.run_comparison_test(build_graph, 0, "Disconnected Graph (starting in component 1)")
        self.run_comparison_test(build_graph, 11, "Disconnected Graph (starting in component 2)")

    def test_star_graph(self):
        def build_graph():
            g = BaselineGraph()
            for i in range(1, 101):
                g.add_edge(0, i)
            return g
        self.run_comparison_test(build_graph, 0, "Star Graph (center start)")
        self.run_comparison_test(build_graph, 50, "Star Graph (leaf start)")

    def test_complete_graph(self):
        def build_graph():
            g = BaselineGraph()
            nodes = list(range(50))
            for i in range(len(nodes)):
                for j in range(i + 1, len(nodes)):
                    g.add_edge(nodes[i], nodes[j])
            return g
        self.run_comparison_test(build_graph, 25, "Complete Graph")
        
    def test_nonexistent_start_node(self):
        def build_graph():
            g = BaselineGraph()
            g.add_edge(0, 1)
            return g
        self.run_comparison_test(build_graph, 99, "Nonexistent Start Node")

    def test_large_random_graph(self):
        """
        Tests a larger graph with random connections to simulate a more complex workload.
        The random seed is fixed to ensure the test is reproducible.
        """
        def build_graph():
            g = BaselineGraph()
            num_vertices = 500
            random.seed(42)
            for _ in range(num_vertices * 2):
                u, v = random.randint(0, num_vertices - 1), random.randint(0, num_vertices - 1)
                if u != v:
                    g.add_edge(u, v)
            return g
        self.run_comparison_test(build_graph, 0, "Large Random Graph (seed 42)")

if __name__ == "__main__":
    # The Graph class in bfs_parallel is identical to the one in bfs_baseline.
    # We create a temporary alias to satisfy the type hint for the test helper.
    BaselineGraph = ParallelGraph
    unittest.main()
