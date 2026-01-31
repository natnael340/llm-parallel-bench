import java.util.*;
import java.util.concurrent.*;

public class AlgoParallel {
    private final int V;
    private final List<List<Integer>> adj;     // builder-time lists
    private final List<List<Integer>> revAdj;  // builder-time lists
    private boolean verbose;

    // CSR arrays built on first use
    private int[] off;   // size V+1
    private int[] dst;   // size E
    private int[] roff;  // size V+1
    private int[] rdst;  // size E
    private volatile boolean csrBuilt = false;

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
        csrBuilt = false; // invalidate CSR on mutation
    }

    private void buildCSRIfNeeded() {
        if (csrBuilt) return;
        synchronized (this) {
            if (csrBuilt) return;
            // Build CSR from adj and revAdj preserving insertion order
            int E = 0;
            for (int i = 0; i < V; i++) E += adj.get(i).size();
            off = new int[V + 1];
            dst = new int[E];
            int pos = 0;
            for (int i = 0; i < V; i++) {
                off[i] = pos;
                List<Integer> nbrs = adj.get(i);
                for (int v : nbrs) dst[pos++] = v;
            }
            off[V] = pos;

            // reversed CSR
            int RE = 0;
            for (int i = 0; i < V; i++) RE += revAdj.get(i).size();
            roff = new int[V + 1];
            rdst = new int[RE];
            pos = 0;
            for (int i = 0; i < V; i++) {
                roff[i] = pos;
                List<Integer> nbrs = revAdj.get(i);
                for (int v : nbrs) rdst[pos++] = v;
            }
            roff[V] = pos;

            csrBuilt = true;
        }
    }

    // Iterative Kosaraju using CSR for determinism and performance
    public List<List<Integer>> findSCCs() {
        buildCSRIfNeeded();
        List<List<Integer>> sccList = new ArrayList<>();
        boolean[] visited = new boolean[V];
        int[] nextIdx = new int[V];
        int[] stack = new int[Math.max(1, V)];
        int top = 0;
        List<Integer> order = new ArrayList<>(V);

        for (int i = 0; i < V; i++) {
            if (visited[i]) continue;
            // push i
            stack[top++] = i;
            visited[i] = true;
            while (top > 0) {
                int u = stack[top - 1];
                int begin = off[u], end = off[u + 1];
                if (nextIdx[u] < (end - begin)) {
                    int v = dst[begin + nextIdx[u]++];
                    if (!visited[v]) {
                        visited[v] = true;
                        if (top == stack.length) stack = Arrays.copyOf(stack, stack.length * 2);
                        stack[top++] = v;
                    }
                } else {
                    // finished u
                    top--;
                    order.add(u);
                }
            }
        }

        Arrays.fill(visited, false);
        int[] q = new int[Math.max(1, V)];
        for (int i = order.size() - 1; i >= 0; i--) {
            int start = order.get(i);
            if (visited[start]) continue;
            List<Integer> comp = new ArrayList<>();
            int qs = 0, qe = 0;
            q[qe++] = start;
            visited[start] = true;
            while (qs < qe) {
                int u = q[qs++];
                comp.add(u);
                int begin = roff[u], end = roff[u + 1];
                for (int ei = begin; ei < end; ei++) {
                    int v = rdst[ei];
                    if (!visited[v]) {
                        visited[v] = true;
                        if (qe == q.length) q = Arrays.copyOf(q, q.length * 2);
                        q[qe++] = v;
                    }
                }
            }
            sccList.add(comp);
        }
        return sccList;
    }

    private List<int[]> buildSpanningTreeEdgesCSR(int start, int[] offArr, int[] dstArr, boolean[] inScc) {
        // Emulate GraphSeq's stack-DFS style: pop node, iterate all neighbors once, push newly discovered ones.
        List<int[]> edges = new ArrayList<>();
        boolean[] visited = new boolean[V];
        int[] st = new int[Math.max(1, V)];
        int sp = 0;
        st[sp++] = start;
        visited[start] = true;
        while (sp > 0) {
            int u = st[--sp]; // pop
            int begin = offArr[u], end = offArr[u + 1];
            for (int ei = begin; ei < end; ei++) {
                int v = dstArr[ei];
                if (inScc[v] && !visited[v]) {
                    edges.add(new int[]{u, v});
                    visited[v] = true;
                    if (sp == st.length) st = Arrays.copyOf(st, st.length * 2);
                    st[sp++] = v;
                }
            }
        }
        return edges;
    }

    public List<int[]> minimizeEdgesInSCC(List<Integer> scc) {
        if (scc.isEmpty()) return new ArrayList<>();
        buildCSRIfNeeded();
        boolean[] inScc = new boolean[V];
        for (int node : scc) inScc[node] = true;
        int root = scc.get(0);
        for (int x : scc) if (x < root) root = x; // canonical min root like baseline
        List<int[]> essential = new ArrayList<>();
        essential.addAll(buildSpanningTreeEdgesCSR(root, off, dst, inScc));
        essential.addAll(buildSpanningTreeEdgesCSR(root, roff, rdst, inScc));
        for (int node : scc) inScc[node] = false;
        return essential;
    }

    // Parallel reduceEdges with deterministic merge order
    public List<int[]> reduceEdges() {
        List<List<Integer>> SCCs = findSCCs();
        if (verbose) {
            System.out.println("Found " + SCCs.size() + " SCC(s).");
        }
        int sccCount = SCCs.size();
        List<int[]> reducedEdges = new ArrayList<>();

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

        for (int i = 0; i < sccCount; i++) {
            if (partial[i] != null) reducedEdges.addAll(partial[i]);
        }

        if (verbose) {
            System.out.println("Reduced SCC edges: " + reducedEdges.size());
        }
        return reducedEdges;
    }
}
