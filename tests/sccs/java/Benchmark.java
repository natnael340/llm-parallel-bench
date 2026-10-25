import java.util.*;

public class Benchmark {

    // --- correctness: SCC strong-check heuristic (mirrors the Go harness) ---
    // For SCC of size k>1: (k-1) <= internal edges <= 2*(k-1), and every SCC
    // node appears in at least one kept internal edge.
    static boolean isSccStrong(List<Integer> sccNodes, List<int[]> edges) {
        Set<Integer> nodeSet = new HashSet<>(sccNodes);
        int k = sccNodes.size();
        if (k <= 1) return true;

        int internalEdges = 0;
        Set<Integer> touched = new HashSet<>();
        for (int[] e : edges) {
            if (nodeSet.contains(e[0]) && nodeSet.contains(e[1])) {
                internalEdges++;
                touched.add(e[0]);
                touched.add(e[1]);
            }
        }
        if (internalEdges < k - 1) return false;
        if (internalEdges > 2 * (k - 1)) return false;
        if (touched.size() < k) return false;
        return true;
    }

    static boolean checkAllSCCs(Impl g) {
        List<int[]> edges = g.reduceEdges();
        for (List<Integer> scc : g.findSCCs()) {
            if (!isSccStrong(scc, edges)) return false;
        }
        return true;
    }

    // Random multi-SCC graph; reduceEdges must return byte-identical output across runs.
    static boolean checkDeterminism() {
        final int numScc = 24, sccSize = 40, runs = 5;
        long seed = new Random().nextLong();
        Random rng = new Random(seed);

        Impl g = new Impl(numScc * sccSize);
        for (int s = 0; s < numScc; s++) {
            int start = s * sccSize;
            for (int u = start; u < start + sccSize; u++) g.addEdge(u, start + (u - start + 1) % sccSize);
            for (int i = 0; i < sccSize * 3; i++) {
                int u = start + rng.nextInt(sccSize), v = start + rng.nextInt(sccSize);
                if (u != v) g.addEdge(u, v);
            }
        }
        for (int s = 0; s < numScc - 1; s++) {
            for (int i = 0; i < 6; i++) g.addEdge(s * sccSize + rng.nextInt(sccSize), (s + 1) * sccSize + rng.nextInt(sccSize));
        }

        List<List<Integer>> sccs = g.findSCCs();
        List<int[]> first = null;
        for (int r = 0; r < runs; r++) {
            List<int[]> edges = g.reduceEdges();
            for (List<Integer> scc : sccs) {
                if (!isSccStrong(scc, edges)) {
                    System.out.println("determinism run " + r + ": reduced edges broke SCC (seed=" + seed + ")");
                    return false;
                }
            }
            if (first == null) {
                first = edges;
            } else if (!sameEdges(edges, first)) {
                System.out.println("determinism run " + r + ": output differs from run 0 (seed=" + seed + ")");
                return false;
            }
        }
        return true;
    }

    static boolean sameEdges(List<int[]> a, List<int[]> b) {
        if (a.size() != b.size()) return false;
        for (int i = 0; i < a.size(); i++) {
            if (!Arrays.equals(a.get(i), b.get(i))) return false;
        }
        return true;
    }

    static int runCorrectnessChecks() {
        int failures = 0;

        Impl g1 = new Impl(3);
        g1.addEdge(0, 1); g1.addEdge(1, 2); g1.addEdge(2, 0);
        failures += report("test_scc_3cycle", checkAllSCCs(g1));

        Impl g2 = new Impl(2);
        g2.addEdge(0, 1); g2.addEdge(1, 0);
        failures += report("test_scc_2node_mutual", checkAllSCCs(g2));

        Impl g3 = new Impl(5);
        g3.addEdge(0, 1); g3.addEdge(1, 2); g3.addEdge(2, 0);
        g3.addEdge(3, 4); g3.addEdge(4, 3);
        g3.addEdge(2, 3);
        failures += report("test_scc_multiple", checkAllSCCs(g3));

        Impl g4 = new Impl(7);
        g4.addEdge(0, 1); g4.addEdge(1, 2); g4.addEdge(1, 3); g4.addEdge(1, 4);
        g4.addEdge(2, 0); g4.addEdge(2, 3); g4.addEdge(3, 5); g4.addEdge(5, 3);
        g4.addEdge(5, 4); g4.addEdge(5, 6); g4.addEdge(6, 4); g4.addEdge(4, 6);
        failures += report("test_scc_7node", checkAllSCCs(g4));
        failures += report("test_scc_determinism", checkDeterminism());

        return failures;
    }

    static int report(String name, boolean ok) {
        System.out.println(name + (ok ? " passed" : " failed"));
        return ok ? 0 : 1;
    }

    // --- benchmark graph construction (shared with all languages) ---

    static void ringSCC(int start, int end, Impl g) {
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

    static Impl buildGraph(int graphSize, int clusterSize, int noClusterInGroup) {
        Impl g = new Impl(graphSize);
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

        Impl g = buildGraph(graphSize, clusterSize, noClusterInGroup);

        if (Bench.digestOut() != null) {
            List<int[]> edges = g.reduceEdges();
            StringBuilder out = new StringBuilder();
            for (List<Integer> scc : g.findSCCs()) {
                out.append('S');
                for (int v : scc) out.append(' ').append(v);
                out.append('\n');
            }
            for (int[] e : edges) out.append("E ").append(e[0]).append(' ').append(e[1]).append('\n');
            Bench.writeDigest(out);
            return;
        }

        int reps = Bench.reps(5);
        int iters = Bench.iters(20);

        Bench.Result r = Bench.run(() -> g.reduceEdges(), reps, iters, 1);

        String label = String.format("SCC ReduceEdges | graph_size=%d", graphSize);
        System.out.println(Bench.format(label, r));

        String params = String.format(
            "{\"graph_size\": %d, \"cluster_size\": %d, \"no_cluster_in_group\": %d}",
            graphSize, clusterSize, noClusterInGroup);
        Bench.writeResult(filename, r, "sccs", Bench.impl(), params);
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

        // Output path: --out flag, else BENCH_OUT env (may be empty: print only).
        String filename = argDict.getOrDefault("out", Bench.out());

        int failures = runCorrectnessChecks();
        if (failures > 0) {
            System.out.println(failures + " correctness check(s) failed — benchmarking anyway");
        }

        benchmarkReduceEdges(filename);
        if (failures > 0) System.exit(1);
    }
}
