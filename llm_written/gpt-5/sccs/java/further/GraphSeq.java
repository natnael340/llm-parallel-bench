import java.util.*;

public class GraphSeq {
    private int V;
    private List<List<Integer>> adj;
    private List<List<Integer>> revAdj;
    private boolean verbose;

    public GraphSeq(int v) {
        this(v, false);
    }

    public GraphSeq(int v, boolean verbose) {
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

    // Iterative Kosaraju to avoid recursion depth issues
    public List<List<Integer>> findSCCs() {
        List<List<Integer>> sccList = new ArrayList<>();
        boolean[] visited = new boolean[V];
        int[] nextIdx = new int[V];
        Deque<Integer> stack = new ArrayDeque<>();
        List<Integer> order = new ArrayList<>(V);

        for (int i = 0; i < V; i++) {
            if (visited[i]) continue;
            // iterative DFS to compute finishing order
            stack.push(i);
            visited[i] = true;
            while (!stack.isEmpty()) {
                int u = stack.peek();
                List<Integer> nbrs = adj.get(u);
                if (nextIdx[u] < nbrs.size()) {
                    int v = nbrs.get(nextIdx[u]++);
                    if (!visited[v]) {
                        visited[v] = true;
                        stack.push(v);
                    }
                } else {
                    stack.pop();
                    order.add(u);
                }
            }
        }

        // second pass on reversed graph (DFS for consistency)
        Arrays.fill(visited, false);
        int[] nextIdx2 = new int[V];
        for (int i = order.size() - 1; i >= 0; i--) {
            int start = order.get(i);
            if (visited[start]) continue;
            List<Integer> comp = new ArrayList<>();
            Deque<Integer> st = new ArrayDeque<>();
            st.push(start);
            visited[start] = true;
            while (!st.isEmpty()) {
                int u = st.peek();
                List<Integer> nbrs = revAdj.get(u);
                if (nextIdx2[u] < nbrs.size()) {
                    int v = nbrs.get(nextIdx2[u]++);
                    if (!visited[v]) {
                        visited[v] = true;
                        st.push(v);
                    }
                } else {
                    st.pop();
                    comp.add(u);
                }
            }
            sccList.add(comp);
        }
        return sccList;
    }

    // Build spanning tree returning list of int[] pairs
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

    // Minimal SCC Edge Reduction (O(V+E))
    public List<int[]> minimizeEdgesInSCC(List<Integer> scc) {
        if (scc.isEmpty()) return new ArrayList<>();
        Set<Integer> nodes = new HashSet<>(scc);
        // Canonical root to ensure deterministic equality across impls
        int root = scc.get(0);
        for (int x : scc) if (x < root) root = x;
        List<int[]> essentialEdges = new ArrayList<>();

        // Step 1: forward spanning tree using DFS
        List<int[]> forwardTree = buildSpanningTreeEdges(root, adj, nodes);

        // Step 2: reverse spanning tree using DFS on the reversed graph
        List<int[]> reverseTree = buildSpanningTreeEdges(root, revAdj, nodes);

        // Step 3: Merge both trees
        essentialEdges.addAll(forwardTree);
        essentialEdges.addAll(reverseTree);

        return essentialEdges;
    }

    public List<int[]> reduceEdges() {
        List<List<Integer>> SCCs = findSCCs();
        if (verbose) {
            System.out.println("Found " + SCCs.size() + " SCC(s).");
        }

        List<int[]> reducedEdges = new ArrayList<>();
        for (List<Integer> scc : SCCs) {
            List<int[]> minEdges = minimizeEdgesInSCC(scc);
            reducedEdges.addAll(minEdges);
        }

        if (verbose) {
            System.out.println("Reduced SCC edges: " + reducedEdges.size());
        }
        return reducedEdges;
    }
}
