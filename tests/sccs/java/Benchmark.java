// Swap the line below to switch between sequential and parallel implementations.
import seq.Graph;
//import par.Graph;

import java.io.*;
import java.util.*;

public class Benchmark {

    static void ringSCC(int start, int end, Graph g) {
        for (int i = start; i < end; i++) {
            int v = (i + 1) % end;
            if (v == 0) {
                v = start;
            }
            if (i == v) {
                continue;
            }
            g.addEdge(i, v);
        }
    }

    static Graph buildGraph(int graphSize, int clusterSize, int noClusterInGroup) {
        Graph g = new Graph(graphSize);
        Random rand = new Random(43);

        for (int i = 0; i < graphSize; i += clusterSize) {
            ringSCC(i, Math.min(i + clusterSize, graphSize), g);

            int currentCluster = (i / clusterSize);
            if (currentCluster / noClusterInGroup == (currentCluster + 1) / noClusterInGroup) {
                if ((i + clusterSize) < graphSize) {
                    int endA = Math.min(i + clusterSize, graphSize);
                    int endB = Math.min(i + 2 * clusterSize, graphSize);

                    int u = i + rand.nextInt(endA - i);
                    int v = endA + rand.nextInt(endB - endA);
                    g.addEdge(u, v);
                }
            }
        }
        return g;
    }

    static void benchmarkReduceEdges(String filename) {
        int graphSize = 100000;
        int clusterSize = 300;
        int noClusterInGroup = 3;

        Graph g = buildGraph(graphSize, clusterSize, noClusterInGroup);

        final int reps = 5;
        final int iters = 20;

        // warmup
        g.reduceEdges();

        double[] perRepeatMs = new double[reps];

        for (int r = 0; r < reps; r++) {
            long start = System.nanoTime();
            for (int i = 0; i < iters; i++) {
                g.reduceEdges();
            }
            long end = System.nanoTime();
            perRepeatMs[r] = (end - start) / 1_000_000.0 / iters;
        }

        double mean = 0.0;
        for (double t : perRepeatMs) mean += t;
        mean /= reps;

        double sqSum = 0.0;
        for (double t : perRepeatMs) sqSum += (t - mean) * (t - mean);
        double stddev = Math.sqrt(sqSum / reps);

        StringBuilder json = new StringBuilder();
        json.append("{\n");
        json.append("  \"elapsed_ms\": [");
        for (int i = 0; i < reps; i++) {
            if (i > 0) json.append(", ");
            json.append(perRepeatMs[i]);
        }
        json.append("],\n");
        json.append("  \"mean\": ").append(mean).append(",\n");
        json.append("  \"sd\": ").append(stddev).append(",\n");
        json.append("  \"iterations\": ").append(reps).append("\n");
        json.append("}\n");

        try (FileWriter fw = new FileWriter(filename)) {
            fw.write(json.toString());
        } catch (IOException ex) {
            System.err.println("Error writing JSON to file: " + filename + "\n" + ex.getMessage());
        }

        System.out.println("SCC ReduceEdges | graph_size=" + graphSize + " | " + mean + " ms/run ± " + stddev + " (n=" + reps + ")");
    }

    static Map<String, String> parseArgs(String[] args) {
        Map<String, String> dict = new HashMap<>();
        for (int i = 0; i < args.length - 1; i++) {
            if (args[i].startsWith("--")) {
                String key = args[i].substring(2);
                String value = args[i + 1];
                dict.put(key, value);
                i++;
            }
        }
        return dict;
    }

    public static void main(String[] args) {
        Map<String, String> argDict = parseArgs(args);

        String filename;
        if (argDict.containsKey("out")) {
            filename = argDict.get("out");
        } else {
            System.err.println("Error: Output file not specified. Use --out <filename>");
            return;
        }

        System.out.println("Starting BenchmarkReduceEdges...");
        benchmarkReduceEdges(filename);
    }
}
