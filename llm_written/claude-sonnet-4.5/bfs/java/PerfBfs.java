import java.util.*;

public class PerfBfs {
    public static void main(String[] args) {
        System.out.println("=== BFS Performance Testing ===\n");
        
        int cores = Runtime.getRuntime().availableProcessors();
        System.out.println("Available processors: " + cores);
        System.out.println();
        
        // Test on large grid
        testLargeGrid(100, 100, cores);
        testLargeGrid(200, 200, cores);
        
        // Test on random graph
        testRandomGraph(5000, 25000, cores);
        testRandomGraph(10000, 50000, cores);
    }
    
    private static void testLargeGrid(int rows, int cols, int cores) {
        System.out.println("Test: Grid " + rows + "x" + cols + " (V=" + (rows*cols) + ")");
        
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
        
        // Warmup
        for (int i = 0; i < 3; i++) {
            BfsSequential.run(g, 0);
        }
        
        // Sequential timing
        long seqStart = System.nanoTime();
        List<Integer> seqResult = BfsSequential.run(g, 0);
        long seqEnd = System.nanoTime();
        double seqTime = (seqEnd - seqStart) / 1_000_000.0;
        
        // Parallel timing (warmup)
        BfsParallel bfsParallel = new BfsParallel(cores);
        for (int i = 0; i < 3; i++) {
            bfsParallel.run(g, 0);
        }
        
        // Parallel timing (measured)
        long parStart = System.nanoTime();
        List<Integer> parResult = bfsParallel.run(g, 0);
        long parEnd = System.nanoTime();
        double parTime = (parEnd - parStart) / 1_000_000.0;
        
        bfsParallel.shutdown();
        
        // Verify correctness
        boolean correct = seqResult.equals(parResult);
        
        double speedup = seqTime / parTime;
        double efficiency = speedup / cores * 100.0;
        
        System.out.println("  Sequential time: " + String.format("%.2f", seqTime) + " ms");
        System.out.println("  Parallel time:   " + String.format("%.2f", parTime) + " ms");
        System.out.println("  Speedup:         " + String.format("%.2f", speedup) + "x");
        System.out.println("  Efficiency:      " + String.format("%.1f", efficiency) + "%");
        System.out.println("  Correctness:     " + (correct ? "PASS" : "FAIL"));
        System.out.println();
    }
    
    private static void testRandomGraph(int vertices, int edges, int cores) {
        System.out.println("Test: Random Graph (V=" + vertices + ", E=" + edges + ")");
        
        Graph g = new Graph();
        Random rand = new Random(42);
        
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
        
        // Warmup
        for (int i = 0; i < 3; i++) {
            BfsSequential.run(g, 0);
        }
        
        // Sequential timing
        long seqStart = System.nanoTime();
        List<Integer> seqResult = BfsSequential.run(g, 0);
        long seqEnd = System.nanoTime();
        double seqTime = (seqEnd - seqStart) / 1_000_000.0;
        
        // Parallel timing (warmup)
        BfsParallel bfsParallel = new BfsParallel(cores);
        for (int i = 0; i < 3; i++) {
            bfsParallel.run(g, 0);
        }
        
        // Parallel timing (measured)
        long parStart = System.nanoTime();
        List<Integer> parResult = bfsParallel.run(g, 0);
        long parEnd = System.nanoTime();
        double parTime = (parEnd - parStart) / 1_000_000.0;
        
        bfsParallel.shutdown();
        
        // Verify correctness
        boolean correct = seqResult.equals(parResult);
        
        double speedup = seqTime / parTime;
        double efficiency = speedup / cores * 100.0;
        
        System.out.println("  Sequential time: " + String.format("%.2f", seqTime) + " ms");
        System.out.println("  Parallel time:   " + String.format("%.2f", parTime) + " ms");
        System.out.println("  Speedup:         " + String.format("%.2f", speedup) + "x");
        System.out.println("  Efficiency:      " + String.format("%.1f", efficiency) + "%");
        System.out.println("  Correctness:     " + (correct ? "PASS" : "FAIL"));
        System.out.println();
    }
}
