import java.util.*;
import java.util.concurrent.*;
import java.nio.file.*;
import java.nio.charset.StandardCharsets;

public class TestAlgo {
    static String canonicalize(List<int[]> edges) {
        List<int[]> copy = new ArrayList<>(edges.size());
        for (int[] e : edges) copy.add(new int[]{e[0], e[1]});
        copy.sort((a,b) -> {
            if (a[0] != b[0]) return Integer.compare(a[0], b[0]);
            return Integer.compare(a[1], b[1]);
        });
        StringBuilder sb = new StringBuilder();
        for (int[] e : copy) {
            sb.append(e[0]).append('>').append(e[1]).append(',');
        }
        return sb.toString();
    }

    static List<int[]> generateRandomEdges(int V, int E, long seed) {
        Random rnd = new Random(seed);
        HashSet<Long> seen = new HashSet<>();
        List<int[]> edges = new ArrayList<>(E);
        int maxTries = Math.max(E * 3, 1000);
        int tries = 0;
        while (edges.size() < E && tries < maxTries) {
            int u = rnd.nextInt(Math.max(1, V));
            int v = rnd.nextInt(Math.max(1, V));
            long key = (((long)u) << 32) ^ (v & 0xffffffffL);
            if (!seen.contains(key)) {
                seen.add(key);
                edges.add(new int[]{u, v});
            }
            tries++;
        }
        return edges;
    }

    static List<int[]> edgesFromPairs(int[][] pairs) {
        List<int[]> edges = new ArrayList<>();
        for (int[] p : pairs) edges.add(new int[]{p[0], p[1]});
        return edges;
    }

    static class CaseResult {
        String name;
        boolean ok;
        String hashSeq;
        List<String> parHashes;
        String details;
        CaseResult(String name) { this.name = name; this.ok = true; this.parHashes = new ArrayList<>(); }
    }

    static CaseResult runCase(String name, int V, List<int[]> edges, boolean doPerf) throws Exception {
        CaseResult cr = new CaseResult(name);
        GraphSeq gs = new GraphSeq(V, false);
        AlgoParallel gp = new AlgoParallel(V, false);
        for (int[] e : edges) { if (e[0] < V && e[1] < V) { gs.addEdge(e[0], e[1]); gp.addEdge(e[0], e[1]); } }

        long t0 = System.nanoTime();
        List<int[]> seq = gs.reduceEdges();
        long t1 = System.nanoTime();
        String hSeq = canonicalize(seq);
        cr.hashSeq = hSeq;

        String h1 = null, h2 = null, h3 = null;
        long p0 = System.nanoTime();
        List<int[]> par1 = gp.reduceEdges();
        long p1 = System.nanoTime();
        h1 = canonicalize(par1);
        cr.parHashes.add(h1);

        List<int[]> par2 = gp.reduceEdges();
        long p2 = System.nanoTime();
        h2 = canonicalize(par2);
        cr.parHashes.add(h2);

        List<int[]> par3 = gp.reduceEdges();
        long p3 = System.nanoTime();
        h3 = canonicalize(par3);
        cr.parHashes.add(h3);

        boolean sameAsSeq = hSeq.equals(h1) && hSeq.equals(h2) && hSeq.equals(h3);
        boolean det = h1.equals(h2) && h2.equals(h3);
        cr.ok = sameAsSeq && det;
        if (!cr.ok) {
            cr.details = "Mismatch or non-determinism";
        }

        if (doPerf) {
            double msSeq = (t1 - t0) / 1e6;
            double msPar = Math.min((p1 - p0), Math.min((p2 - p1), (p3 - p2))) / 1e6; // take best of 3
            double speedup = msSeq / msPar;
            String perf = String.format(Locale.US, "V=%d E=%d t_seq=%.2fms t_par=%.2fms speedup=%.2fx", V, edges.size(), msSeq, msPar, speedup);
            Files.write(Paths.get("perf.txt"), (name+": "+perf+"\n").getBytes(StandardCharsets.UTF_8), StandardOpenOption.CREATE, StandardOpenOption.APPEND);
        }
        return cr;
    }

    public static void main(String[] args) throws Exception {
        List<String> lines = new ArrayList<>();
        boolean overall = true;

        // Edge cases
        {
            CaseResult cr = runCase("empty-graph", 0, Collections.emptyList(), false);
            lines.add(String.format("%s: %s", cr.name, cr.ok?"PASS":"FAIL"));
            overall &= cr.ok;
        }
        {
            CaseResult cr = runCase("single-node", 1, Collections.emptyList(), false);
            lines.add(String.format("%s: %s", cr.name, cr.ok?"PASS":"FAIL"));
            overall &= cr.ok;
        }
        {
            List<int[]> edges = edgesFromPairs(new int[][]{ {0,1},{1,2},{2,0} });
            CaseResult cr = runCase("single-cycle", 3, edges, false);
            lines.add(String.format("%s: %s", cr.name, cr.ok?"PASS":"FAIL"));
            overall &= cr.ok;
        }
        {
            List<int[]> edges = edgesFromPairs(new int[][]{ {0,1},{1,0}, {2,3},{3,2}, {1,2} });
            CaseResult cr = runCase("two-sccs", 4, edges, false);
            lines.add(String.format("%s: %s", cr.name, cr.ok?"PASS":"FAIL"));
            overall &= cr.ok;
        }

        // Random small/medium
        {
            List<int[]> edges = generateRandomEdges(200, 800, 12345L);
            CaseResult cr = runCase("random-small", 200, edges, false);
            lines.add(String.format("%s: %s", cr.name, cr.ok?"PASS":"FAIL"));
            overall &= cr.ok;
        }
        {
            List<int[]> edges = generateRandomEdges(2000, 8000, 54321L);
            CaseResult cr = runCase("random-medium", 2000, edges, false);
            lines.add(String.format("%s: %s", cr.name, cr.ok?"PASS":"FAIL"));
            overall &= cr.ok;
        }

        boolean skipPerf = Arrays.stream(args).anyMatch(s -> s.equalsIgnoreCase("skipperf"));
        if (!skipPerf) {
            List<int[]> edges = generateRandomEdges(12000, 48000, 2024L);
            CaseResult cr = runCase("random-large", 12000, edges, true);
            lines.add(String.format("%s: %s", cr.name, cr.ok?"PASS":"FAIL"));
            overall &= cr.ok;
        }

        StringBuilder sb = new StringBuilder();
        sb.append("Test Summary\n");
        for (String l : lines) sb.append(l).append('\n');
        sb.append("OVERALL: ").append(overall?"PASS":"FAIL").append('\n');
        System.out.print(sb.toString());
        Files.write(Paths.get("run_summary.txt"), sb.toString().getBytes(StandardCharsets.UTF_8));

        if (!overall) {
            System.exit(1);
        }
    }
}
