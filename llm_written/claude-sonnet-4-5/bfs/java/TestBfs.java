import java.util.*;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;

public class TestBfs {
    private static final int NUM_DETERMINISM_RUNS = 3;
    
    public static void main(String[] args) {
        TestBfs tester = new TestBfs();
        boolean allPassed = true;

        System.out.println("=== BFS Differential Testing ===\n");

        // Edge cases
        allPassed &= tester.testEmptyGraph();
        allPassed &= tester.testSingleVertex();
        allPassed &= tester.testDisconnectedGraph();
        allPassed &= tester.testInvalidStartVertex();

        // Small cases
        allPassed &= tester.testLinearChain(10);
        allPassed &= tester.testCompleteBinaryTree(7);
        allPassed &= tester.testCycle(5);

        // Medium cases
        allPassed &= tester.testGrid(10, 10);
        allPassed &= tester.testRandomGraph(50, 100);

        // Large cases
        allPassed &= tester.testGrid(50, 50);
        allPassed &= tester.testRandomGraph(1000, 5000);
        allPassed &= tester.testCompleteBinaryTree(1023);

        System.out.println("\n=== Summary ===");
        if (allPassed) {
            System.out.println("✓ All tests PASSED");
            System.exit(0);
        } else {
            System.out.println("✗ Some tests FAILED");
            System.exit(1);
        }
    }

    private boolean testEmptyGraph() {
        System.out.println("Test: Empty Graph");
        Graph g = new Graph();
        return runTest("EmptyGraph", g, 0);
    }

    private boolean testSingleVertex() {
        System.out.println("Test: Single Vertex");
        Graph g = new Graph();
        g.getVertices().put(0, new ArrayList<>());
        return runTest("SingleVertex", g, 0);
    }

    private boolean testDisconnectedGraph() {
        System.out.println("Test: Disconnected Graph");
        Graph g = new Graph();
        g.addEdge(0, 1);
        g.addEdge(1, 2);
        g.addEdge(3, 4);
        g.addEdge(4, 5);
        return runTest("DisconnectedGraph", g, 0);
    }

    private boolean testInvalidStartVertex() {
        System.out.println("Test: Invalid Start Vertex");
        Graph g = new Graph();
        g.addEdge(0, 1);
        g.addEdge(1, 2);
        return runTest("InvalidStartVertex", g, 99);
    }

    private boolean testLinearChain(int length) {
        System.out.println("Test: Linear Chain (length=" + length + ")");
        Graph g = new Graph();
        for (int i = 0; i < length - 1; i++) {
            g.addEdge(i, i + 1);
        }
        return runTest("LinearChain_" + length, g, 0);
    }

    private boolean testCycle(int size) {
        System.out.println("Test: Cycle (size=" + size + ")");
        Graph g = new Graph();
        for (int i = 0; i < size; i++) {
            g.addEdge(i, (i + 1) % size);
        }
        return runTest("Cycle_" + size, g, 0);
    }

    private boolean testCompleteBinaryTree(int numVertices) {
        System.out.println("Test: Complete Binary Tree (vertices=" + numVertices + ")");
        Graph g = new Graph();
        for (int i = 0; i < numVertices; i++) {
            int left = 2 * i + 1;
            int right = 2 * i + 2;
            if (left < numVertices) {
                g.addEdge(i, left);
            }
            if (right < numVertices) {
                g.addEdge(i, right);
            }
        }
        return runTest("BinaryTree_" + numVertices, g, 0);
    }

    private boolean testGrid(int rows, int cols) {
        System.out.println("Test: Grid (rows=" + rows + ", cols=" + cols + ")");
        Graph g = new Graph();
        for (int r = 0; r < rows; r++) {
            for (int c = 0; c < cols; c++) {
                int v = r * cols + c;
                if (c < cols - 1) {
                    g.addEdge(v, v + 1);
                }
                if (r < rows - 1) {
                    g.addEdge(v, v + cols);
                }
            }
        }
        return runTest("Grid_" + rows + "x" + cols, g, 0);
    }

    private boolean testRandomGraph(int vertices, int edges) {
        System.out.println("Test: Random Graph (V=" + vertices + ", E=" + edges + ")");
        Graph g = new Graph();
        Random rand = new Random(42); // Fixed seed for reproducibility
        
        // Ensure all vertices exist
        for (int i = 0; i < vertices; i++) {
            g.getVertices().putIfAbsent(i, new ArrayList<>());
        }
        
        // Add random edges
        Set<String> addedEdges = new HashSet<>();
        int edgeCount = 0;
        while (edgeCount < edges) {
            int u = rand.nextInt(vertices);
            int v = rand.nextInt(vertices);
            if (u != v) {
                String edge = Math.min(u, v) + "-" + Math.max(u, v);
                if (!addedEdges.contains(edge)) {
                    g.addEdge(u, v);
                    addedEdges.add(edge);
                    edgeCount++;
                }
            }
        }
        
        return runTest("RandomGraph_V" + vertices + "_E" + edges, g, 0);
    }

    private boolean runTest(String testName, Graph graph, int startVertex) {
        try {
            // Run sequential baseline
            List<Integer> seqResult = BfsSequential.run(graph, startVertex);
            String seqHash = hashList(seqResult);

            // Run parallel version multiple times for determinism check
            BfsParallel bfsParallel = new BfsParallel();
            List<String> parHashes = new ArrayList<>();
            List<Integer> firstParResult = null;

            for (int i = 0; i < NUM_DETERMINISM_RUNS; i++) {
                List<Integer> parResult = bfsParallel.run(graph, startVertex);
                if (i == 0) {
                    firstParResult = parResult;
                }
                parHashes.add(hashList(parResult));
            }
            bfsParallel.shutdown();

            // Check correctness (parallel matches sequential)
            boolean correctness = seqHash.equals(parHashes.get(0));
            
            // Check determinism (all parallel runs match)
            boolean determinism = parHashes.stream().allMatch(h -> h.equals(parHashes.get(0)));

            if (correctness && determinism) {
                System.out.println("  ✓ PASS - Correctness: YES, Determinism: YES");
                System.out.println("    Sequential hash: " + seqHash);
                System.out.println("    Parallel hash:   " + parHashes.get(0));
                return true;
            } else {
                System.out.println("  ✗ FAIL");
                if (!correctness) {
                    System.out.println("    Correctness FAILED:");
                    System.out.println("      Sequential: " + seqResult);
                    System.out.println("      Parallel:   " + firstParResult);
                    System.out.println("      Seq hash: " + seqHash);
                    System.out.println("      Par hash: " + parHashes.get(0));
                }
                if (!determinism) {
                    System.out.println("    Determinism FAILED:");
                    for (int i = 0; i < parHashes.size(); i++) {
                        System.out.println("      Run " + (i + 1) + ": " + parHashes.get(i));
                    }
                }
                return false;
            }
        } catch (Exception e) {
            System.out.println("  ✗ EXCEPTION: " + e.getMessage());
            e.printStackTrace();
            return false;
        }
    }

    private String hashList(List<Integer> list) {
        try {
            MessageDigest md = MessageDigest.getInstance("SHA-256");
            String str = list.toString();
            byte[] hash = md.digest(str.getBytes());
            StringBuilder hexString = new StringBuilder();
            for (byte b : hash) {
                String hex = Integer.toHexString(0xff & b);
                if (hex.length() == 1) hexString.append('0');
                hexString.append(hex);
            }
            return hexString.toString().substring(0, 16);
        } catch (NoSuchAlgorithmException e) {
            throw new RuntimeException(e);
        }
    }
}
