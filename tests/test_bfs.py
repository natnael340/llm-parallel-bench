import unittest
from BFS.bfs_seq import Graph, bfs

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
    