// Swap the line below to switch between sequential and parallel implementations.
import seq.Graph;
//import par.Graph;

import java.io.*;
import java.util.*;
import java.util.Arrays;

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

        double med = median(perRepeatMs);
        double spread = iqr(perRepeatMs);

        writeResult(filename, "sccs", "java", System.getenv("IMPL"),
                    perRepeatMs, med, spread, reps, iters);

        System.out.printf("SCC ReduceEdges | graph_size=%d | %.2f ms/run ± %.2f IQR (n=%d)%n",
                          graphSize, med, spread, reps);
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

    static double median(double[] values) {
        double[] s = values.clone();
        Arrays.sort(s);
        int n = s.length;
        return (n % 2 == 0) ? (s[n / 2 - 1] + s[n / 2]) / 2.0 : s[n / 2];
    }

    static double iqr(double[] values) {
        double[] s = values.clone();
        Arrays.sort(s);
        int n = s.length;
        double q1 = s[(int) ((n - 1) * 0.25)];
        double q3 = s[(int) ((n - 1) * 0.75)];
        return q3 - q1;
    }

    static void writeResult(String path, String algo, String lang, String impl,
                            double[] elapsedMs, double med, double spread,
                            int reps, int itersPerRep) {
        if (path == null || path.isEmpty()) return;
        if (impl == null) impl = "";
        StringBuilder sb = new StringBuilder();
        sb.append("{\n");
        sb.append("  \"algo\": \"").append(algo).append("\",\n");
        sb.append("  \"lang\": \"").append(lang).append("\",\n");
        sb.append("  \"impl\": \"").append(impl).append("\",\n");
        sb.append("  \"elapsed_ms\": [");
        for (int i = 0; i < elapsedMs.length; i++) {
            if (i > 0) sb.append(", ");
            sb.append(elapsedMs[i]);
        }
        sb.append("],\n");
        sb.append("  \"median\": ").append(med).append(",\n");
        sb.append("  \"iqr\": ").append(spread).append(",\n");
        sb.append("  \"reps\": ").append(reps).append(",\n");
        sb.append("  \"iters_per_rep\": ").append(itersPerRep).append("\n}\n");
        try (FileWriter fw = new FileWriter(path)) {
            fw.write(sb.toString());
        } catch (IOException ex) {
            System.err.println("Error writing JSON: " + ex.getMessage());
        }
    }
}
