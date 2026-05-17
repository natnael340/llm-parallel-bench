import java.util.*;
import java.util.concurrent.*;
import java.util.stream.Collectors;
import java.util.stream.Stream;

/**
 * Measures the serial and parallel fractions of BfsParallel directly,
 * to compute an empirical Amdahl serial fraction rather than back-calculating
 * from overall speedup (which is distorted by data structure differences).
 *
 * Instruments the BFS loop to separately time:
 *   - parallel section: forkJoinPool.submit(...).join()  [neighbour collection]
 *   - serial section:   Collections.sort + result.addAll [merge and bookkeeping]
 */
public class BfsAmdahlTest {

    static long totalParallelNs = 0;
    static long totalSerialNs   = 0;

    public static List<Integer> runInstrumented(Graph graph, int startVertex) {
        totalParallelNs = 0;
        totalSerialNs   = 0;

        if (!graph.getVertices().containsKey(startVertex)) return new ArrayList<>();
        if (graph.getVertices().size() < 1000) return Bfs.run(graph, startVertex);

        Set<Integer> visited = ConcurrentHashMap.newKeySet();
        List<Integer> result = new CopyOnWriteArrayList<>();
        List<Integer> frontier = new CopyOnWriteArrayList<>();

        frontier.add(startVertex);
        visited.add(startVertex);
        result.add(startVertex);

        int nThreads = Runtime.getRuntime().availableProcessors();
        ForkJoinPool pool = new ForkJoinPool(nThreads);

        while (!frontier.isEmpty()) {
            final List<Integer> currentFrontier = frontier;

            // --- parallel section ---
            long p0 = System.nanoTime();
            List<Integer> nextFrontier = pool.submit(() ->
                currentFrontier.parallelStream()
                    .flatMap(current -> {
                        List<Integer> neighbors = graph.getVertices().get(current);
                        return (neighbors != null) ? neighbors.stream() : Stream.empty();
                    })
                    .filter(visited::add)
                    .collect(Collectors.toList())
            ).join();
            long p1 = System.nanoTime();
            totalParallelNs += (p1 - p0);

            // --- serial section ---
            long s0 = System.nanoTime();
            Collections.sort(nextFrontier);
            result.addAll(nextFrontier);
            frontier = nextFrontier;
            long s1 = System.nanoTime();
            totalSerialNs += (s1 - s0);
        }

        pool.shutdown();
        return new ArrayList<>(result);
    }

    public static void main(String[] args) {
        int numVertices = (args.length > 0) ? Integer.parseInt(args[0]) : 50000;
        int runs        = (args.length > 1) ? Integer.parseInt(args[1]) : 5;

        System.out.println("Graph: " + numVertices + " vertices, " + (numVertices * 5) + " edges (random)");
        System.out.println("Runs: " + runs);
        System.out.println("Available cores: " + Runtime.getRuntime().availableProcessors());
        System.out.println();

        boolean complete = (args.length > 2 && args[2].equals("complete"));
        Graph graph = complete ? buildCompleteGraph(numVertices) : buildGraph(numVertices);
        int startVertex = complete ? 1 : 0;
        System.out.println("Graph type: " + (complete ? "complete" : "random sparse"));

        // warmup
        runInstrumented(graph, startVertex);
        runInstrumented(graph, startVertex);

        double[] serialFractions = new double[runs];

        for (int r = 0; r < runs; r++) {
            runInstrumented(graph, startVertex);
            double par    = totalParallelNs / 1e6;
            double serial = totalSerialNs   / 1e6;
            double total  = par + serial;
            System.out.printf("Run %d: parallel=%.3f ms (%d ns)  serial=%.3f ms (%d ns)  total=%.3f ms%n",
                r + 1, par, totalParallelNs, serial, totalSerialNs, total);
            if (total == 0) { serialFractions[r] = Double.NaN; continue; }
            double S      = serial / total;
            serialFractions[r] = S;
            System.out.printf("        S=%.4f  Amdahl_max=%.2fx  Amdahl_%dcores=%.2fx%n",
                S, 1.0 / S,
                Runtime.getRuntime().availableProcessors(),
                1.0 / (S + (1.0 - S) / Runtime.getRuntime().availableProcessors()));
        }

        double meanS = Arrays.stream(serialFractions).average().orElse(0);
        int N = Runtime.getRuntime().availableProcessors();
        System.out.println();
        System.out.printf("Mean serial fraction S     : %.4f (%.1f%%)%n", meanS, meanS * 100);
        System.out.printf("Amdahl ceiling (inf cores) : %.2fx%n", 1.0 / meanS);
        System.out.printf("Amdahl limit (%d cores)    : %.2fx%n", N, 1.0 / (meanS + (1.0 - meanS) / N));
    }

    private static Graph buildGraph(int n) {
        Graph g = new Graph();
        Random rand = new Random(42);
        for (int i = 0; i < n; i++) g.addVertex(i);
        for (int i = 0; i < n * 5; i++) {
            int u = rand.nextInt(n), v = rand.nextInt(n);
            if (u != v) g.addEdge(u, v);
        }
        return g;
    }

    private static Graph buildCompleteGraph(int n) {
        Graph g = new Graph();
        for (int i = 1; i <= n; i++) g.addVertex(i);
        for (int i = 1; i <= n; i++)
            for (int j = i + 1; j <= n; j++) {
                g.addEdge(i, j);
                g.addEdge(j, i);
            }
        return g;
    }
}
