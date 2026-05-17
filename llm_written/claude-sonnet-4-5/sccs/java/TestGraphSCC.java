import java.util.*;
import java.security.MessageDigest;
import java.nio.charset.StandardCharsets;

public class TestGraphSCC {
    
    // Helper to compute hash of edge list for determinism checking
    private static String computeHash(List<int[]> edges) {
        try {
            MessageDigest md = MessageDigest.getInstance("SHA-256");
            
            // Sort edges for consistent hashing
            List<String> edgeStrings = new ArrayList<>();
            for (int[] edge : edges) {
                edgeStrings.add(edge[0] + "," + edge[1]);
            }
            Collections.sort(edgeStrings);
            
            String combined = String.join(";", edgeStrings);
            byte[] hash = md.digest(combined.getBytes(StandardCharsets.UTF_8));
            
            StringBuilder hexString = new StringBuilder();
            for (byte b : hash) {
                String hex = Integer.toHexString(0xff & b);
                if (hex.length() == 1) hexString.append('0');
                hexString.append(hex);
            }
            return hexString.toString();
        } catch (Exception e) {
            throw new RuntimeException("Hash computation failed", e);
        }
    }
    
    // Helper to compare edge lists
    private static boolean edgeListsEqual(List<int[]> list1, List<int[]> list2) {
        if (list1.size() != list2.size()) return false;
        
        Set<String> set1 = new HashSet<>();
        Set<String> set2 = new HashSet<>();
        
        for (int[] edge : list1) {
            set1.add(edge[0] + "," + edge[1]);
        }
        for (int[] edge : list2) {
            set2.add(edge[0] + "," + edge[1]);
        }
        
        return set1.equals(set2);
    }
    
    // Test case 1: Simple cycle
    private static boolean testSimpleCycle() {
        System.out.println("\n=== Test 1: Simple Cycle (3 nodes) ===");
        Graph g1 = new Graph(3);
        GraphParallel g2 = new GraphParallel(3);
        
        // 0 -> 1 -> 2 -> 0
        g1.addEdge(0, 1);
        g1.addEdge(1, 2);
        g1.addEdge(2, 0);
        
        g2.addEdge(0, 1);
        g2.addEdge(1, 2);
        g2.addEdge(2, 0);
        
        List<int[]> seq = g1.reduceEdges();
        List<int[]> par = g2.reduceEdges();
        
        boolean match = edgeListsEqual(seq, par);
        System.out.println("Sequential edges: " + seq.size());
        System.out.println("Parallel edges: " + par.size());
        System.out.println("Match: " + match);
        
        return match;
    }
    
    // Test case 2: Multiple SCCs
    private static boolean testMultipleSCCs() {
        System.out.println("\n=== Test 2: Multiple SCCs (6 nodes, 2 SCCs) ===");
        Graph g1 = new Graph(6);
        GraphParallel g2 = new GraphParallel(6);
        
        // SCC 1: 0 -> 1 -> 2 -> 0
        g1.addEdge(0, 1);
        g1.addEdge(1, 2);
        g1.addEdge(2, 0);
        
        // SCC 2: 3 -> 4 -> 5 -> 3
        g1.addEdge(3, 4);
        g1.addEdge(4, 5);
        g1.addEdge(5, 3);
        
        g2.addEdge(0, 1);
        g2.addEdge(1, 2);
        g2.addEdge(2, 0);
        g2.addEdge(3, 4);
        g2.addEdge(4, 5);
        g2.addEdge(5, 3);
        
        List<int[]> seq = g1.reduceEdges();
        List<int[]> par = g2.reduceEdges();
        
        boolean match = edgeListsEqual(seq, par);
        System.out.println("Sequential edges: " + seq.size());
        System.out.println("Parallel edges: " + par.size());
        System.out.println("Match: " + match);
        
        return match;
    }
    
    // Test case 3: Single node
    private static boolean testSingleNode() {
        System.out.println("\n=== Test 3: Single Node ===");
        Graph g1 = new Graph(1);
        GraphParallel g2 = new GraphParallel(1);
        
        List<int[]> seq = g1.reduceEdges();
        List<int[]> par = g2.reduceEdges();
        
        boolean match = edgeListsEqual(seq, par);
        System.out.println("Sequential edges: " + seq.size());
        System.out.println("Parallel edges: " + par.size());
        System.out.println("Match: " + match);
        
        return match;
    }
    
    // Test case 4: Disconnected graph
    private static boolean testDisconnected() {
        System.out.println("\n=== Test 4: Disconnected Graph (4 isolated nodes) ===");
        Graph g1 = new Graph(4);
        GraphParallel g2 = new GraphParallel(4);
        
        List<int[]> seq = g1.reduceEdges();
        List<int[]> par = g2.reduceEdges();
        
        boolean match = edgeListsEqual(seq, par);
        System.out.println("Sequential edges: " + seq.size());
        System.out.println("Parallel edges: " + par.size());
        System.out.println("Match: " + match);
        
        return match;
    }
    
    // Test case 5: Large graph with many SCCs
    private static boolean testLargeGraph() {
        System.out.println("\n=== Test 5: Large Graph (100 nodes, 20 SCCs) ===");
        int numSCCs = 20;
        int nodesPerSCC = 5;
        int totalNodes = numSCCs * nodesPerSCC;
        
        Graph g1 = new Graph(totalNodes);
        GraphParallel g2 = new GraphParallel(totalNodes);
        
        // Create 20 SCCs, each with 5 nodes in a cycle
        for (int scc = 0; scc < numSCCs; scc++) {
            int base = scc * nodesPerSCC;
            for (int i = 0; i < nodesPerSCC; i++) {
                int from = base + i;
                int to = base + ((i + 1) % nodesPerSCC);
                g1.addEdge(from, to);
                g2.addEdge(from, to);
            }
        }
        
        List<int[]> seq = g1.reduceEdges();
        List<int[]> par = g2.reduceEdges();
        
        boolean match = edgeListsEqual(seq, par);
        System.out.println("Sequential edges: " + seq.size());
        System.out.println("Parallel edges: " + par.size());
        System.out.println("Match: " + match);
        
        return match;
    }
    
    // Test case 6: Complex graph with inter-SCC edges
    private static boolean testComplexGraph() {
        System.out.println("\n=== Test 6: Complex Graph with Inter-SCC Edges ===");
        Graph g1 = new Graph(9);
        GraphParallel g2 = new GraphParallel(9);
        
        // SCC 1: 0 -> 1 -> 2 -> 0
        g1.addEdge(0, 1);
        g1.addEdge(1, 2);
        g1.addEdge(2, 0);
        
        // SCC 2: 3 -> 4 -> 3
        g1.addEdge(3, 4);
        g1.addEdge(4, 3);
        
        // SCC 3: 5 -> 6 -> 7 -> 8 -> 5
        g1.addEdge(5, 6);
        g1.addEdge(6, 7);
        g1.addEdge(7, 8);
        g1.addEdge(8, 5);
        
        // Inter-SCC edges (not part of any SCC)
        g1.addEdge(2, 3);
        g1.addEdge(4, 5);
        
        g2.addEdge(0, 1);
        g2.addEdge(1, 2);
        g2.addEdge(2, 0);
        g2.addEdge(3, 4);
        g2.addEdge(4, 3);
        g2.addEdge(5, 6);
        g2.addEdge(6, 7);
        g2.addEdge(7, 8);
        g2.addEdge(8, 5);
        g2.addEdge(2, 3);
        g2.addEdge(4, 5);
        
        List<int[]> seq = g1.reduceEdges();
        List<int[]> par = g2.reduceEdges();
        
        boolean match = edgeListsEqual(seq, par);
        System.out.println("Sequential edges: " + seq.size());
        System.out.println("Parallel edges: " + par.size());
        System.out.println("Match: " + match);
        
        return match;
    }
    
    // Determinism test: run parallel version 3 times
    private static boolean testDeterminism() {
        System.out.println("\n=== Test 7: Determinism Check (3 runs) ===");
        int numSCCs = 15;
        int nodesPerSCC = 4;
        int totalNodes = numSCCs * nodesPerSCC;
        
        GraphParallel g1 = new GraphParallel(totalNodes);
        GraphParallel g2 = new GraphParallel(totalNodes);
        GraphParallel g3 = new GraphParallel(totalNodes);
        
        // Create identical graphs
        for (int scc = 0; scc < numSCCs; scc++) {
            int base = scc * nodesPerSCC;
            for (int i = 0; i < nodesPerSCC; i++) {
                int from = base + i;
                int to = base + ((i + 1) % nodesPerSCC);
                g1.addEdge(from, to);
                g2.addEdge(from, to);
                g3.addEdge(from, to);
            }
        }
        
        List<int[]> run1 = g1.reduceEdges();
        List<int[]> run2 = g2.reduceEdges();
        List<int[]> run3 = g3.reduceEdges();
        
        String hash1 = computeHash(run1);
        String hash2 = computeHash(run2);
        String hash3 = computeHash(run3);
        
        System.out.println("Run 1 hash: " + hash1);
        System.out.println("Run 2 hash: " + hash2);
        System.out.println("Run 3 hash: " + hash3);
        
        boolean deterministic = hash1.equals(hash2) && hash2.equals(hash3);
        System.out.println("Deterministic: " + deterministic);
        
        return deterministic;
    }
    
    public static void main(String[] args) {
        System.out.println("╔════════════════════════════════════════════════════╗");
        System.out.println("║  Graph SCC Edge Reduction - Differential Tests    ║");
        System.out.println("╚════════════════════════════════════════════════════╝");
        
        List<Boolean> results = new ArrayList<>();
        
        results.add(testSimpleCycle());
        results.add(testMultipleSCCs());
        results.add(testSingleNode());
        results.add(testDisconnected());
        results.add(testLargeGraph());
        results.add(testComplexGraph());
        results.add(testDeterminism());
        
        System.out.println("\n╔════════════════════════════════════════════════════╗");
        System.out.println("║                   TEST SUMMARY                     ║");
        System.out.println("╚════════════════════════════════════════════════════╝");
        
        int passed = 0;
        for (int i = 0; i < results.size(); i++) {
            String status = results.get(i) ? "✓ PASS" : "✗ FAIL";
            System.out.println("Test " + (i + 1) + ": " + status);
            if (results.get(i)) passed++;
        }
        
        System.out.println("\nTotal: " + passed + "/" + results.size() + " passed");
        
        if (passed == results.size()) {
            System.out.println("\n🎉 All tests passed!");
            System.exit(0);
        } else {
            System.out.println("\n❌ Some tests failed!");
            System.exit(1);
        }
    }
}
