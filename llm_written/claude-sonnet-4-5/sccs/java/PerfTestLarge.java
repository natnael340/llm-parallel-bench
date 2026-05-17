import java.util.*;

public class PerfTestLarge {
    
    private static void warmup() {
        System.out.println("Warming up JVM...");
        for (int i = 0; i < 3; i++) {
            Graph g = new Graph(100);
            for (int j = 0; j < 100; j++) {
                g.addEdge(j, (j + 1) % 100);
            }
            g.reduceEdges();
        }
        System.out.println("Warmup complete.\n");
    }
    
    private static long measureSequential(Graph g) {
        long start = System.nanoTime();
        g.reduceEdges();
        long end = System.nanoTime();
        return end - start;
    }
    
    private static long measureParallel(GraphParallel g) {
        long start = System.nanoTime();
        g.reduceEdges();
        long end = System.nanoTime();
        return end - start;
    }
    
    public static void main(String[] args) {
        System.out.println("╔════════════════════════════════════════════════════╗");
        System.out.println("║    Graph SCC - Large Performance Benchmark         ║");
        System.out.println("╚════════════════════════════════════════════════════╝\n");
        
        warmup();
        
        int cores = Runtime.getRuntime().availableProcessors();
        System.out.println("Available processors: " + cores + "\n");
        
        // Test configuration: many large SCCs to benefit from parallelism
        int numSCCs = 100;
        int nodesPerSCC = 100;
        int totalNodes = numSCCs * nodesPerSCC;
        
        System.out.println("Test Configuration:");
        System.out.println("  Total nodes: " + totalNodes);
        System.out.println("  Number of SCCs: " + numSCCs);
        System.out.println("  Nodes per SCC: " + nodesPerSCC);
        System.out.println();
        
        System.out.println("Building graphs...");
        
        // Build identical graphs
        Graph gSeq = new Graph(totalNodes);
        GraphParallel gPar = new GraphParallel(totalNodes);
        
        for (int scc = 0; scc < numSCCs; scc++) {
            int base = scc * nodesPerSCC;
            // Create a more complex SCC structure
            for (int i = 0; i < nodesPerSCC; i++) {
                int from = base + i;
                int to = base + ((i + 1) % nodesPerSCC);
                gSeq.addEdge(from, to);
                gPar.addEdge(from, to);
            }
            // Add cross edges for complexity
            for (int i = 0; i < nodesPerSCC / 2; i++) {
                int from = base + i;
                int to = base + ((i + nodesPerSCC / 3) % nodesPerSCC);
                gSeq.addEdge(from, to);
                gPar.addEdge(from, to);
            }
            // Add more cross edges
            for (int i = 0; i < nodesPerSCC / 3; i++) {
                int from = base + i;
                int to = base + ((i + nodesPerSCC / 2) % nodesPerSCC);
                gSeq.addEdge(from, to);
                gPar.addEdge(from, to);
            }
        }
        
        System.out.println("Running benchmarks (5 iterations each)...\n");
        
        // Run multiple iterations
        int iterations = 5;
        long[] seqTimes = new long[iterations];
        long[] parTimes = new long[iterations];
        
        for (int i = 0; i < iterations; i++) {
            // Rebuild graphs for each iteration
            Graph gSeqIter = new Graph(totalNodes);
            GraphParallel gParIter = new GraphParallel(totalNodes);
            
            for (int scc = 0; scc < numSCCs; scc++) {
                int base = scc * nodesPerSCC;
                for (int j = 0; j < nodesPerSCC; j++) {
                    int from = base + j;
                    int to = base + ((j + 1) % nodesPerSCC);
                    gSeqIter.addEdge(from, to);
                    gParIter.addEdge(from, to);
                }
                for (int j = 0; j < nodesPerSCC / 2; j++) {
                    int from = base + j;
                    int to = base + ((j + nodesPerSCC / 3) % nodesPerSCC);
                    gSeqIter.addEdge(from, to);
                    gParIter.addEdge(from, to);
                }
                for (int j = 0; j < nodesPerSCC / 3; j++) {
                    int from = base + j;
                    int to = base + ((j + nodesPerSCC / 2) % nodesPerSCC);
                    gSeqIter.addEdge(from, to);
                    gParIter.addEdge(from, to);
                }
            }
            
            seqTimes[i] = measureSequential(gSeqIter);
            parTimes[i] = measureParallel(gParIter);
            
            System.out.println("Iteration " + (i + 1) + ":");
            System.out.println("  Sequential: " + String.format("%.2f", seqTimes[i] / 1_000_000.0) + " ms");
            System.out.println("  Parallel:   " + String.format("%.2f", parTimes[i] / 1_000_000.0) + " ms");
        }
        
        // Calculate statistics
        long seqMedian = calculateMedian(seqTimes);
        long parMedian = calculateMedian(parTimes);
        
        double seqMs = seqMedian / 1_000_000.0;
        double parMs = parMedian / 1_000_000.0;
        double speedup = (double) seqMedian / parMedian;
        double efficiency = speedup / cores * 100.0;
        
        System.out.println("\n╔════════════════════════════════════════════════════╗");
        System.out.println("║                     RESULTS                        ║");
        System.out.println("╚════════════════════════════════════════════════════╝");
        System.out.println("Sequential (median): " + String.format("%.2f", seqMs) + " ms");
        System.out.println("Parallel (median):   " + String.format("%.2f", parMs) + " ms");
        System.out.println("Speedup:             " + String.format("%.2f", speedup) + "x");
        System.out.println("Parallel Efficiency: " + String.format("%.1f", efficiency) + "%");
        System.out.println("Cores used:          " + cores);
        
        // Append results to file
        try {
            java.io.PrintWriter writer = new java.io.PrintWriter(
                new java.io.FileWriter("perf.txt", true));
            writer.println();
            writer.println("Large Graph Test:");
            writer.println("  Total nodes: " + totalNodes);
            writer.println("  Number of SCCs: " + numSCCs);
            writer.println("  Nodes per SCC: " + nodesPerSCC);
            writer.println("  Sequential time: " + String.format("%.2f", seqMs) + " ms");
            writer.println("  Parallel time:   " + String.format("%.2f", parMs) + " ms");
            writer.println("  Speedup:         " + String.format("%.2f", speedup) + "x");
            writer.println("  Efficiency:      " + String.format("%.1f", efficiency) + "%");
            writer.close();
            System.out.println("\nResults appended to perf.txt");
        } catch (Exception e) {
            System.err.println("Failed to write perf.txt: " + e.getMessage());
        }
    }
    
    private static long calculateMedian(long[] values) {
        long[] sorted = values.clone();
        Arrays.sort(sorted);
        int mid = sorted.length / 2;
        if (sorted.length % 2 == 0) {
            return (sorted[mid - 1] + sorted[mid]) / 2;
        } else {
            return sorted[mid];
        }
    }
}
