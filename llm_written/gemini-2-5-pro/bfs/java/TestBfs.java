import java.util.*;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.nio.charset.StandardCharsets;

public class TestBfs {

    public static void main(String[] args) {
        if (args.length < 1) {
            System.err.println("Usage: java TestBfs <mode> [numVertices]");
            System.exit(1);
        }

        String mode = args[0];
        int numVertices = (args.length > 1) ? Integer.parseInt(args[1]) : 10000;
        int startVertex = 0;
        
        Graph graph = createGraph(numVertices);

        if ("correctness".equals(mode)) {
            runCorrectnessTest(graph, startVertex);
        } else if ("determinism".equals(mode)) {
            runDeterminismTest(graph, startVertex);
        } else if ("performance".equals(mode)) {
            runPerformanceTest(graph, startVertex);
        } else {
            System.err.println("Invalid mode. Use 'correctness', 'determinism', or 'performance'.");
            System.exit(1);
        }
    }

    private static Graph createGraph(int numVertices) {
        Graph graph = new Graph();
        Random rand = new Random(42);
        for (int i = 0; i < numVertices; i++) {
            graph.addVertex(i);
        }
        int numEdges = numVertices * 5;
        for (int i = 0; i < numEdges; i++) {
            int u = rand.nextInt(numVertices);
            int v = rand.nextInt(numVertices);
            if (u != v) {
                graph.addEdge(u, v);
            }
        }
        return graph;
    }

    private static void runCorrectnessTest(Graph graph, int startVertex) {
        System.out.println("Running correctness test...");

        List<Integer> sequentialResult = Bfs.run(graph, startVertex);
        List<Integer> parallelResult = BfsParallel.run(graph, startVertex);

        boolean match = sequentialResult.equals(parallelResult);
        System.out.println("Correctness check: " + (match ? "PASS" : "FAIL"));
        if (!match) {
             System.err.println("Sequential and parallel results do not match.");
             System.err.println("Sequential size: " + sequentialResult.size());
             System.err.println("Parallel size: " + parallelResult.size());
             System.exit(1);
        }
    }

    private static void runDeterminismTest(Graph graph, int startVertex) {
        System.out.println("Running determinism test...");
        
        List<Integer> run1 = BfsParallel.run(graph, startVertex);
        List<Integer> run2 = BfsParallel.run(graph, startVertex);
        List<Integer> run3 = BfsParallel.run(graph, startVertex);

        String hash1 = toSHA256(run1.toString());
        String hash2 = toSHA256(run2.toString());
        String hash3 = toSHA256(run3.toString());

        boolean deterministic = hash1.equals(hash2) && hash2.equals(hash3);
        System.out.println("Determinism check: " + (deterministic ? "PASS" : "FAIL"));
        System.out.println("Run 1 hash: " + hash1);
        System.out.println("Run 2 hash: " + hash2);
        System.out.println("Run 3 hash: " + hash3);
        
        if (!deterministic) {
            System.err.println("Parallel implementation is not deterministic.");
            System.exit(1);
        }
    }

    private static void runPerformanceTest(Graph graph, int startVertex) {
        System.out.println("Running performance test...");
        
        long startTimeSeq = System.nanoTime();
        Bfs.run(graph, startVertex);
        long endTimeSeq = System.nanoTime();
        double durationSeq = (endTimeSeq - startTimeSeq) / 1e9;
        
        long startTimePar = System.nanoTime();
        BfsParallel.run(graph, startVertex);
        long endTimePar = System.nanoTime();
        double durationPar = (endTimePar - startTimePar) / 1e9;
        
        System.out.printf("Sequential BFS took %.4f seconds.%n", durationSeq);
        System.out.printf("Parallel BFS took %.4f seconds.%n", durationPar);
        
        if (durationPar > 0) {
            System.out.printf("Speedup: %.2fx%n", durationSeq / durationPar);
        } else {
            System.out.println("Parallel execution was too fast to measure speedup.");
        }
    }
    
    private static String toSHA256(String data) {
        try {
            MessageDigest digest = MessageDigest.getInstance("SHA-256");
            byte[] hash = digest.digest(data.getBytes(StandardCharsets.UTF_8));
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
}
