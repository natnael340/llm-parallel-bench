import java.io.*;
import java.util.*;
import static java.util.Collections.emptyList;


class Bfs {
    public static List<Integer> run(Graph graph, int start) {
        return Impl.run(graph, start); // staged adapter selects the implementation
    }
}

public class BfsTests {
    private static int passed = 0;
    private static int failed = 0;
    private static Bfs bfs = new Bfs();

    public static void main(String[] args) {
        System.out.println("Running BFS Tests...\n");

        // Basic Tests
        test("Empty graph returns empty list", BfsTests::testEmptyGraph);
        test("Single node with self-loop returns single node", BfsTests::testSingleNode);
        test("Linear graph returns nodes in order", BfsTests::testLinearGraph);

        // Graph Structure Tests
        test("Complete graph returns correct BFS order", BfsTests::testCompleteGraph);
        test("Star graph returns center then leaves", BfsTests::testStarGraph);
        test("Cycle is handled correctly", BfsTests::testCycle);
        test("Tree structure returns level order", BfsTests::testTreeStructure);
        test("Complex graph returns correct order", BfsTests::testComplexGraph);

        // Edge Cases
        test("Disconnected components only visits connected component", BfsTests::testDisconnectedComponents);
        test("Duplicate edges are handled correctly", BfsTests::testDuplicateEdges);
        test("Nonexistent start vertex returns empty list", BfsTests::testNonexistentStart);
        test("Negative vertex numbers work correctly", BfsTests::testNegativeVertices);
        test("Large vertex numbers work correctly", BfsTests::testLargeVertices);
        test("Single isolated node", BfsTests::testSingleIsolatedNode);
        test("Binary tree structure", BfsTests::testBinaryTree);
        test("Grid graph traversal", BfsTests::testGridGraph);
        test("Hub and spoke with chains", BfsTests::testHubAndSpoke);
        test("Multiple parallel edges between same nodes", BfsTests::testParallelEdges);

        // Consistency Tests
        test("Order consistency is maintained across runs", BfsTests::testOrderConsistency);
        test("Different starting vertices produce valid orderings", BfsTests::testDifferentStartVertices);
        test("Unordered edge insertion produces correct BFS", BfsTests::testReturnOrder);

        // Performance Tests
        test("Performance stress test with large linear graph", BfsTests::testLargeLinearGraph);
        test("Performance with wide graph (many neighbors)", BfsTests::testWideGraph);
        test("Performance with deep graph (long chain)", BfsTests::testDeepGraph);

        // Summary
        System.out.println("\n========================================");
        System.out.printf("Results: %d passed, %d failed, %d total%n", passed, failed, passed + failed);
        System.out.println("========================================");

        if (failed > 0) {
            System.exit(1);
        }

        // The timed benchmark writes BENCH_OUT, so it must run only after the
        // correctness gate above: a wrong implementation that exits non-zero
        // must not leave a publishable result behind.
        test("Performance speed test with complete graph", BfsTests::testPerformanceSpeedTest);
        if (failed > 0) {
            System.exit(1);
        }
    }

    private static void test(String name, Runnable testFn) {
        try {
            testFn.run();
            System.out.println("[PASS] " + name);
            passed++;
        } catch (AssertionError e) {
            System.out.println("[FAIL] " + name);
            System.out.println("       " + e.getMessage());
            failed++;
        } catch (Exception e) {
            System.out.println("[FAIL] " + name);
            System.out.println("       Exception: " + e.getMessage());
            failed++;
        }
    }

    private static void assertEquals(Object expected, Object actual) {
        if (!Objects.equals(expected, actual)) {
            throw new AssertionError("Expected " + expected + " but got " + actual);
        }
    }

    private static void assertEquals(int expected, int actual) {
        if (expected != actual) {
            throw new AssertionError("Expected " + expected + " but got " + actual);
        }
    }

    private static void assertTrue(boolean condition, String message) {
        if (!condition) {
            throw new AssertionError(message);
        }
    }

    // ==================== Basic Tests ====================

    private static void testEmptyGraph() {
        Graph graph = new Graph();
        List<Integer> result = Bfs.run(graph, 0);
        assertEquals(Collections.emptyList(), result);
    }

    private static void testSingleNode() {
        Graph graph = new Graph();
        graph.addEdge(1, 1);
        List<Integer> result = Bfs.run(graph, 1);
        assertEquals(List.of(1), result);
    }

    private static void testLinearGraph() {
        Graph graph = new Graph();
        graph.addEdge(1, 2);
        graph.addEdge(2, 3);
        graph.addEdge(3, 4);
        List<Integer> result = Bfs.run(graph, 1);
        assertEquals(List.of(1, 2, 3, 4), result);
    }

    // ==================== Graph Structure Tests ====================

    private static void testCompleteGraph() {
        Graph graph = new Graph();
        List<Integer> nodes = List.of(1, 2, 3, 4);
        for (int i : nodes) {
            for (int j : nodes) {
                if (i != j) {
                    graph.addEdge(i, j);
                }
            }
        }
        List<Integer> result = Bfs.run(graph, 3);
        assertEquals(List.of(3, 1, 2, 4), result);
    }

    private static void testStarGraph() {
        Graph graph = new Graph();
        int center = 1;
        List<Integer> leaves = List.of(2, 3, 4, 5);
        for (int leaf : leaves) {
            graph.addEdge(center, leaf);
        }
        List<Integer> result = Bfs.run(graph, center);
        List<Integer> expected = new ArrayList<>();
        expected.add(center);
        expected.addAll(leaves);
        assertEquals(expected, result);
    }

    private static void testCycle() {
        Graph graph = new Graph();
        int[][] edges = {{1, 2}, {2, 3}, {3, 4}, {4, 1}};
        for (int[] edge : edges) {
            graph.addEdge(edge[0], edge[1]);
        }
        List<Integer> result = Bfs.run(graph, 1);
        assertEquals(List.of(1, 2, 4, 3), result);
    }

    private static void testTreeStructure() {
        Graph graph = new Graph();
        int[][] edges = {{1, 2}, {1, 3}, {2, 4}, {2, 5}, {3, 6}, {3, 7}};
        for (int[] edge : edges) {
            graph.addEdge(edge[0], edge[1]);
        }
        List<Integer> result = Bfs.run(graph, 1);
        assertEquals(List.of(1, 2, 3, 4, 5, 6, 7), result);
    }

    private static void testComplexGraph() {
        Graph graph = new Graph();
        int[][] edges = {
            {1, 2}, {1, 3}, {2, 4}, {3, 4}, {4, 5},
            {5, 6}, {6, 7}, {5, 7}, {7, 8}, {3, 8}
        };
        for (int[] edge : edges) {
            graph.addEdge(edge[0], edge[1]);
        }
        List<Integer> result = Bfs.run(graph, 1);
        assertEquals(List.of(1, 2, 3, 4, 8, 5, 7, 6), result);
    }

    // ==================== Edge Cases ====================

    private static void testDisconnectedComponents() {
        Graph graph = new Graph();
        graph.addEdge(1, 2);
        graph.addEdge(2, 3);
        graph.addEdge(4, 5);
        graph.addEdge(4, 6);

        List<Integer> result1 = Bfs.run(graph, 1);
        assertEquals(List.of(1, 2, 3), result1);

        List<Integer> result2 = Bfs.run(graph, 4);
        assertEquals(List.of(4, 5, 6), result2);
    }

    private static void testDuplicateEdges() {
        Graph graph = new Graph();
        graph.addEdge(1, 2);
        graph.addEdge(1, 2);
        graph.addEdge(2, 3);
        List<Integer> result = Bfs.run(graph, 1);
        assertEquals(List.of(1, 2, 3), result);
    }

    private static void testNonexistentStart() {
        Graph graph = new Graph();
        graph.addEdge(1, 2);
        List<Integer> result = Bfs.run(graph, 999);
        assertEquals(Collections.emptyList(), result);
    }

    private static void testNegativeVertices() {
        Graph graph = new Graph();
        graph.addEdge(-1, -2);
        graph.addEdge(-2, -3);
        graph.addEdge(-1, 0);
        List<Integer> result = Bfs.run(graph, -1);
        assertEquals(List.of(-1, -2, 0, -3), result);
    }

    private static void testLargeVertices() {
        Graph graph = new Graph();
        graph.addEdge(Integer.MAX_VALUE - 1, Integer.MAX_VALUE);
        graph.addEdge(Integer.MAX_VALUE, 0);
        List<Integer> result = Bfs.run(graph, Integer.MAX_VALUE - 1);
        assertEquals(List.of(Integer.MAX_VALUE - 1, Integer.MAX_VALUE, 0), result);
    }

    private static void testSingleIsolatedNode() {
        Graph graph = new Graph();
        graph.addEdge(42, 42);
        List<Integer> result = Bfs.run(graph, 42);
        assertEquals(List.of(42), result);
    }

    private static void testBinaryTree() {
        Graph graph = new Graph();
        graph.addEdge(1, 2);
        graph.addEdge(1, 3);
        graph.addEdge(2, 4);
        graph.addEdge(2, 5);
        graph.addEdge(3, 6);
        graph.addEdge(3, 7);
        List<Integer> result = Bfs.run(graph, 1);
        assertEquals(List.of(1, 2, 3, 4, 5, 6, 7), result);
    }

    private static void testGridGraph() {
        Graph graph = new Graph();
        graph.addEdge(1, 2);
        graph.addEdge(1, 3);
        graph.addEdge(2, 4);
        graph.addEdge(3, 4);
        List<Integer> result = Bfs.run(graph, 1);
        assertEquals(4, result.size());
        assertEquals((Integer) 1, result.get(0));
        assertTrue(result.subList(1, 3).containsAll(List.of(2, 3)), "Level 1 should contain 2 and 3");
        assertEquals((Integer) 4, result.get(3));
    }

    private static void testHubAndSpoke() {
        Graph graph = new Graph();
        graph.addEdge(0, 1);
        graph.addEdge(0, 2);
        graph.addEdge(0, 3);
        graph.addEdge(1, 4);
        graph.addEdge(2, 5);
        graph.addEdge(3, 6);
        List<Integer> result = Bfs.run(graph, 0);
        assertEquals(7, result.size());
        assertEquals((Integer) 0, result.get(0));
        assertTrue(result.subList(1, 4).containsAll(List.of(1, 2, 3)), "Level 1 should contain 1, 2, 3");
        assertTrue(result.subList(4, 7).containsAll(List.of(4, 5, 6)), "Level 2 should contain 4, 5, 6");
    }

    private static void testParallelEdges() {
        Graph graph = new Graph();
        graph.addEdge(1, 2);
        graph.addEdge(1, 2);
        graph.addEdge(1, 2);
        graph.addEdge(2, 3);
        List<Integer> result = Bfs.run(graph, 1);
        assertEquals(List.of(1, 2, 3), result);
    }

    // ==================== Consistency Tests ====================

    private static void testOrderConsistency() {
        Graph graph = new Graph();
        graph.addEdge(1, 3);
        graph.addEdge(1, 2);

        List<Integer> first = Bfs.run(graph, 1);
        for (int i = 0; i < 5; i++) {
            List<Integer> result = Bfs.run(graph, 1);
            assertEquals(first, result);
        }
    }

    private static void testDifferentStartVertices() {
        Graph graph = new Graph();
        graph.addEdge(1, 2);
        graph.addEdge(2, 3);
        graph.addEdge(3, 4);
        graph.addEdge(4, 5);

        assertEquals(List.of(1, 2, 3, 4, 5), Bfs.run(graph, 1));
        assertEquals(List.of(3, 2, 4, 1, 5), Bfs.run(graph, 3));
        assertEquals(List.of(5, 4, 3, 2, 1), Bfs.run(graph, 5));
    }

    private static void testReturnOrder() {
        // Edges added in non-sorted, scrambled order
        Graph graph = new Graph();
        graph.addEdge(5, 6);
        graph.addEdge(1, 4);
        graph.addEdge(3, 5);
        graph.addEdge(1, 2);
        graph.addEdge(2, 3);
        graph.addEdge(1, 3);
        graph.addEdge(4, 5);

        // BFS from node 1 should still produce valid level-order traversal
        
        List<Integer> result = Bfs.run(graph, 1);
        assertEquals(List.of(1, 4, 2, 3, 5, 6), result);
    }

    // ==================== Performance Tests ====================

    private static void testLargeLinearGraph() {
        Graph graph = new Graph();
        int size = 1000;
        for (int i = 1; i < size; i++) {
            graph.addEdge(i, i + 1);
        }
        List<Integer> result = Bfs.run(graph, 1);
        assertEquals(size, result.size());
        assertEquals((Integer) 1, result.get(0));
        assertEquals((Integer) size, result.get(result.size() - 1));
    }

    private static void testWideGraph() {
        Graph graph = new Graph();
        int center = 0;
        int numNeighbors = 5000;
        for (int i = 1; i <= numNeighbors; i++) {
            graph.addEdge(center, i);
        }

        long startTime = System.nanoTime();
        List<Integer> result = Bfs.run(graph, center);
        long endTime = System.nanoTime();

        assertEquals(numNeighbors + 1, result.size());
        assertEquals((Integer) center, result.get(0));

        double timeMs = (endTime - startTime) / 1_000_000.0;
        System.out.printf("       (Wide graph: center + %d neighbors in %.2f ms)%n", numNeighbors, timeMs);
    }

    private static void testDeepGraph() {
        Graph graph = new Graph();
        int depth = 10000;
        for (int i = 0; i < depth - 1; i++) {
            graph.addEdge(i, i + 1);
        }

        long startTime = System.nanoTime();
        List<Integer> result = Bfs.run(graph, 0);
        long endTime = System.nanoTime();

        assertEquals(depth, result.size());
        assertEquals((Integer) 0, result.get(0));
        assertEquals((Integer) (depth - 1), result.get(result.size() - 1));

        double timeMs = (endTime - startTime) / 1_000_000.0;
        System.out.printf("       (Deep graph: depth=%d in %.2f ms)%n", depth, timeMs);
    }

    private static void testPerformanceSpeedTest() {
        Graph graph = new Graph();
        int size = 2000;
        for (int i = 1; i <= size; i++) {
            for (int j = i + 1; j <= size; j++) {
                graph.addEdge(i, j);
                graph.addEdge(j, i);
            }
        }

        int reps = Bench.reps(5);
        int iters = Bench.iters(20);

        Bench.Result r = Bench.run(() -> Bfs.run(graph, 1), reps, iters, 1);

        long directedEdges = (long) size * (size - 1);
        String label = String.format("BFS complete graph | nodes=%d, undirected edges≈%,d (directed≈%,d)",
                                     size, directedEdges / 2, directedEdges);
        System.out.println("       (" + Bench.format(label, r) + ")");

        String params = String.format("{\"graph_size\": %d, \"graph_kind\": \"complete\"}", size);
        Bench.writeResult(Bench.out(), r, "bfs", Bench.impl(), params);
    }
}
