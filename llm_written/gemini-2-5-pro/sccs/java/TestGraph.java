import java.util.*;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.stream.Collectors;

public class TestGraph {

    public static void main(String[] args) {
        System.out.println("Running correctness and determinism tests...");

        boolean allTestsPassed = true;
        allTestsPassed &= testEdgeCases();
        allTestsPassed &= testSmallGraph();
        allTestsPassed &= testMediumGraph();
        allTestsPassed &= testLargeGraph();

        if (allTestsPassed) {
            System.out.println("\n✅ All tests passed successfully!");
            writeSummary("SUCCESS: All tests passed.", true);
        } else {
            System.out.println("\n❌ Some tests failed.");
            writeSummary("FAILURE: Some tests failed.", false);
            System.exit(1);
        }
    }

    private static boolean testEdgeCases() {
        System.out.println("\n--- Testing Edge Cases ---");
        // Test 1: Empty graph
        Graph g1_seq = new Graph(0);
        Graph_parallel g1_par = new Graph_parallel(0);
        boolean pass1 = runAndCompare("Empty Graph (V=0)", g1_seq, g1_par);

        // Test 2: Graph with no edges
        Graph g2_seq = new Graph(5);
        Graph_parallel g2_par = new Graph_parallel(5);
        boolean pass2 = runAndCompare("No Edges (V=5)", g2_seq, g2_par);

        // Test 3: Single node
        Graph g3_seq = new Graph(1);
        Graph_parallel g3_par = new Graph_parallel(1);
        boolean pass3 = runAndCompare("Single Node (V=1)", g3_seq, g3_par);

        return pass1 && pass2 && pass3;
    }

    private static boolean testSmallGraph() {
        System.out.println("\n--- Testing Small Graph ---");
        Graph g_seq = new Graph(4);
        g_seq.addEdge(0, 1);
        g_seq.addEdge(1, 2);
        g_seq.addEdge(2, 0);
        g_seq.addEdge(2, 3);
        g_seq.addEdge(3, 3);

        Graph_parallel g_par = new Graph_parallel(4);
        g_par.addEdge(0, 1);
        g_par.addEdge(1, 2);
        g_par.addEdge(2, 0);
        g_par.addEdge(2, 3);
        g_par.addEdge(3, 3);

        return runAndCompare("Small Graph", g_seq, g_par);
    }

    private static boolean testMediumGraph() {
        System.out.println("\n--- Testing Medium Graph ---");
        int V = 50;
        Graph g_seq = new Graph(V);
        Graph_parallel g_par = new Graph_parallel(V);
        Random rand = new Random(42);
        for (int i = 0; i < V * 2; i++) {
            int u = rand.nextInt(V);
            int v = rand.nextInt(V);
            g_seq.addEdge(u, v);
            g_par.addEdge(u, v);
        }
        return runAndCompare("Medium Graph (V=50, E=100)", g_seq, g_par);
    }

    private static boolean testLargeGraph() {
        System.out.println("\n--- Testing Large Graph ---");
        int V = 1000;
        int E = 5000;
        Graph g_seq = new Graph(V);
        Graph_parallel g_par = new Graph_parallel(V);
        Random rand = new Random(42); // Fixed seed for reproducibility
        for (int i = 0; i < E; i++) {
            int u = rand.nextInt(V);
            int v = rand.nextInt(V);
            g_seq.addEdge(u, v);
            g_par.addEdge(u, v);
        }
        return runAndCompare("Large Graph (V=1000, E=5000)", g_seq, g_par);
    }

    private static boolean runAndCompare(String testName, Graph seqGraph, Graph_parallel parGraph) {
        System.out.println("Test: " + testName);

        // Run sequential version
        long startTimeSeq = System.nanoTime();
        List<int[]> seqResult = seqGraph.reduceEdges();
        long durationSeq = System.nanoTime() - startTimeSeq;
        String seqHash = hashResult(seqResult);
        System.out.printf("  Sequential: %d edges, hash: %s, time: %.2f ms\n", seqResult.size(), seqHash, durationSeq / 1e6);

        // Run parallel version multiple times for determinism check
        List<String> parHashes = new ArrayList<>();
        boolean determinismPassed = true;
        long totalParDuration = 0;

        for (int i = 0; i < 3; i++) {
            long startTimePar = System.nanoTime();
            List<int[]> parResult = parGraph.reduceEdges();
            long durationPar = System.nanoTime() - startTimePar;
            totalParDuration += durationPar;
            String parHash = hashResult(parResult);
            parHashes.add(parHash);
            System.out.printf("  Parallel (run %d): %d edges, hash: %s, time: %.2f ms\n", i + 1, parResult.size(), parHash, durationPar / 1e6);
        }

        // Check for determinism
        for (int i = 1; i < parHashes.size(); i++) {
            if (!parHashes.get(0).equals(parHashes.get(i))) {
                determinismPassed = false;
                break;
            }
        }

        if (determinismPassed) {
            System.out.println("  ✅ Determinism test passed.");
        } else {
            System.out.println("  ❌ Determinism test failed. Hashes do not match across runs.");
        }

        // Check for correctness
        boolean correctnessPassed = seqHash.equals(parHashes.get(0));
        if (correctnessPassed) {
            System.out.println("  ✅ Correctness test passed (hashes match sequential).");
        } else {
            System.out.println("  ❌ Correctness test failed. Hash does not match sequential.");
        }

        if(testName.contains("Large")){
             writePerf(String.format("Sequential time: %.2f ms\nParallel time: %.2f ms\n", durationSeq / 1e6, (totalParDuration / 3.0) / 1e6));
        }


        return determinismPassed && correctnessPassed;
    }

    private static String hashResult(List<int[]> edges) {
        if (edges == null || edges.isEmpty()) {
            return "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"; // SHA-256 of empty string
        }
        // Sort edges to ensure canonical representation for hashing
        List<String> edgeStrings = edges.stream()
                .map(edge -> edge[0] + "->" + edge[1])
                .sorted()
                .collect(Collectors.toList());

        try {
            MessageDigest digest = MessageDigest.getInstance("SHA-256");
            for (String s : edgeStrings) {
                digest.update(s.getBytes());
            }
            byte[] hash = digest.digest();
            StringBuilder hexString = new StringBuilder();
            for (byte b : hash) {
                String hex = Integer.toHexString(0xff & b);
                if (hex.length() == 1) hexString.append('0');
                hexString.append(hex);
            }
            return hexString.toString();
        } catch (NoSuchAlgorithmException e) {
            throw new RuntimeException(e);
        }
    }

    private static void writeSummary(String content, boolean success) {
        try (java.io.FileWriter writer = new java.io.FileWriter("run_summary.txt")) {
            writer.write(content + "\n");
        } catch (java.io.IOException e) {
            e.printStackTrace();
        }
    }

    private static void writePerf(String content) {
        try (java.io.FileWriter writer = new java.io.FileWriter("perf.txt")) {
            writer.write(content + "\n");
        } catch (java.io.IOException e) {
            e.printStackTrace();
        }
    }
}
