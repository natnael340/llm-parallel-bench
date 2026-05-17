import java.util.*;
import java.util.concurrent.*;
import java.util.stream.Collectors;

public class Graph_parallel {
    private int V;
    private List<List<Integer>> adj;
    private List<List<Integer>> revAdj;
    private boolean verbose;

    public Graph_parallel(int v) {
        this(v, false);
    }

    public Graph_parallel(int v, boolean verbose) {
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

    // Tarjan's SCC DFS - unchanged
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

    // Build spanning tree returning list of int[] pairs - unchanged
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

    // Tarjan's SCC (O(V+E)) - unchanged
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

    // Minimal SCC Edge Reduction (O(V+E)) - unchanged
    public List<int[]> minimizeEdgesInSCC(List<Integer> scc) {
        Set<Integer> nodes = new HashSet<>(scc);
        List<int[]> essentialEdges = new ArrayList<>();

        if (scc.isEmpty()) {
            return essentialEdges;
        }

        // Step 1: forward spanning tree using DFS
        List<int[]> forwardTree = buildSpanningTreeEdges(scc.get(0), adj, nodes);

        // Step 2: reverse spanning tree using DFS on the reversed graph
        List<int[]> reverseTree = buildSpanningTreeEdges(scc.get(0), revAdj, nodes);

        // Step 3: Merge both trees
        essentialEdges.addAll(forwardTree);
        essentialEdges.addAll(reverseTree);

        return essentialEdges;
    }

    // Parallelized version of reduceEdges
    public List<int[]> reduceEdges() {
        List<List<Integer>> sccs = findSCCs();
        if (verbose) {
            System.out.println("Found " + sccs.size() + " SCC(s).");
        }

        // Determinism: Sort SCCs to ensure canonical order before parallel processing.
        for (List<Integer> scc : sccs) {
            Collections.sort(scc);
        }
        sccs.sort(Comparator.comparingInt(scc -> scc.isEmpty() ? -1 : scc.get(0)));


        // Use a fixed-size thread pool for resource bounding.
        int numThreads = Runtime.getRuntime().availableProcessors();
        ExecutorService executor = Executors.newFixedThreadPool(numThreads);

        List<Future<List<int[]>>> futures = new ArrayList<>();
        for (List<Integer> scc : sccs) {
            Callable<List<int[]>> task = () -> minimizeEdgesInSCC(scc);
            futures.add(executor.submit(task));
        }

        List<int[]> reducedEdges = new ArrayList<>();
        try {
            for (Future<List<int[]>> future : futures) {
                reducedEdges.addAll(future.get());
            }
        } catch (InterruptedException | ExecutionException e) {
            // Fallback to sequential execution on error
            e.printStackTrace();
            reducedEdges.clear();
             for (List<Integer> scc : sccs) {
                reducedEdges.addAll(minimizeEdgesInSCC(scc));
            }
        } finally {
            executor.shutdown();
        }

        if (verbose) {
            System.out.println("Reduced SCC edges: " + reducedEdges.size());
        }
        return reducedEdges;
    }
}
