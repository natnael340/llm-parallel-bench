import java.util.*;
import java.util.concurrent.*;

public class AlgoParallel {
    private int V;
    private List<List<Integer>> adj;
    private List<List<Integer>> revAdj;
    private boolean verbose;

    public AlgoParallel(int v) { this(v, false); }

    public AlgoParallel(int v, boolean verbose) {
        this.V = v;
        this.verbose = verbose;
        this.adj = new ArrayList<>(v);
        this.revAdj = new ArrayList<>(v);
        for (int i = 0; i < v; i++) {
            adj.add(new ArrayList<>());
            revAdj.add(new ArrayList<>());
        }
    }

    public void addEdge(int v, int w) {
        adj.get(v).add(w);
        revAdj.get(w).add(v);
    }

    // Variant: GPT-5's iterative Kosaraju replaced by the baseline's recursive Tarjan
    // (baselines/sccs/java/Graph.java), copied unchanged. Everything else is GPT-5's code.

    // Tarjan's SCC DFS
    private void tarjanDFS(
            int u,
            int[] disc,
            int[] low,
            Deque<Integer> stack,
            boolean[] inStack,
            int[] timer,
            List<List<Integer>> sccList
    ) {
        disc[u] = low[u] = ++timer[0];
        stack.push(u);
        inStack[u] = true;

        for (int v : adj.get(u)) {
            if (disc[v] == -1) {
                tarjanDFS(v, disc, low, stack, inStack, timer, sccList);
                low[u] = Math.min(low[u], low[v]);
            } else if (inStack[v]) {
                low[u] = Math.min(low[u], disc[v]);
            }
        }

        if (low[u] == disc[u]) {
            List<Integer> scc = new ArrayList<>();
            int w;
            do {
                w = stack.pop();
                inStack[w] = false;
                scc.add(w);
            } while (w != u);
            sccList.add(scc);
        }
    }

    // Tarjan's SCC (O(V+E))
    public List<List<Integer>> findSCCs() {
        int[] disc = new int[V];
        int[] low = new int[V];
        Arrays.fill(disc, -1);
        Arrays.fill(low, -1);
        boolean[] inStack = new boolean[V];
        Deque<Integer> stack = new ArrayDeque<>();
        List<List<Integer>> sccList = new ArrayList<>();
        int[] timer = {0};

        for (int i = 0; i < V; i++) {
            if (disc[i] == -1) {
                tarjanDFS(i, disc, low, stack, inStack, timer, sccList);
            }
        }
        return sccList;
    }

    private List<int[]> buildSpanningTreeEdges(int start, List<List<Integer>> graph, Set<Integer> nodes) {
        List<int[]> edges = new ArrayList<>();
        Set<Integer> visited = new HashSet<>();
        Deque<Integer> st = new ArrayDeque<>();
        st.push(start);
        visited.add(start);

        while (!st.isEmpty()) {
            int node = st.pop();
            for (int nb : graph.get(node)) {
                if (nodes.contains(nb) && !visited.contains(nb)) {
                    edges.add(new int[]{node, nb});
                    visited.add(nb);
                    st.push(nb);
                }
            }
        }
        return edges;
    }

    public List<int[]> minimizeEdgesInSCC(List<Integer> scc) {
        if (scc.isEmpty()) return new ArrayList<>();
        Set<Integer> nodes = new HashSet<>(scc);
        List<int[]> essentialEdges = new ArrayList<>();

        List<int[]> forwardTree = buildSpanningTreeEdges(scc.get(0), adj, nodes);
        List<int[]> reverseTree = buildSpanningTreeEdges(scc.get(0), revAdj, nodes);

        essentialEdges.addAll(forwardTree);
        for (int[] e : reverseTree) essentialEdges.add(new int[]{e[1], e[0]});

        return essentialEdges;
    }

    // Parallel reduceEdges with deterministic merge order
    public List<int[]> reduceEdges() {
        List<List<Integer>> SCCs = findSCCs();
        if (verbose) {
            System.out.println("Found " + SCCs.size() + " SCC(s).");
        }
        int sccCount = SCCs.size();
        List<int[]> reducedEdges = new ArrayList<>();

        // small-N sequential fallback to avoid thread overhead
        int smallThreshold = 1000; // based on vertex count
        if (V <= smallThreshold || sccCount <= 1) {
            for (List<Integer> scc : SCCs) {
                List<int[]> minEdges = minimizeEdgesInSCC(scc);
                reducedEdges.addAll(minEdges);
            }
            if (verbose) {
                System.out.println("Reduced SCC edges: " + reducedEdges.size());
            }
            return reducedEdges;
        }

        int maxWorkers = Math.max(1, Math.min(Runtime.getRuntime().availableProcessors(), sccCount));
        ExecutorService pool = Executors.newFixedThreadPool(maxWorkers, r -> {
            Thread t = new Thread(r);
            t.setDaemon(false);
            t.setName("scc-worker-" + t.getId());
            return t;
        });
        @SuppressWarnings("unchecked")
        List<int[]>[] partial = new List[sccCount];
        List<Future<?>> futures = new ArrayList<>(sccCount);

        for (int i = 0; i < sccCount; i++) {
            final int idx = i;
            futures.add(pool.submit(() -> {
                List<int[]> res = minimizeEdgesInSCC(SCCs.get(idx));
                partial[idx] = res; // write to own slot
            }));
        }

        // Wait deterministically for all to finish
        for (Future<?> f : futures) {
            try {
                f.get();
            } catch (InterruptedException ie) {
                Thread.currentThread().interrupt();
                throw new RuntimeException("Interrupted waiting for workers", ie);
            } catch (ExecutionException ee) {
                throw new RuntimeException("Worker failed", ee.getCause());
            }
        }
        pool.shutdown();

        // Deterministic merge in SCC discovery order
        for (int i = 0; i < sccCount; i++) {
            if (partial[i] != null) reducedEdges.addAll(partial[i]);
        }

        if (verbose) {
            System.out.println("Reduced SCC edges: " + reducedEdges.size());
        }
        return reducedEdges;
    }
}
