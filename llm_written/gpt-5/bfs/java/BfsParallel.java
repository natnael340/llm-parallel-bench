import java.util.*;
import java.util.concurrent.*;

public class BfsParallel {
    private static final int MAX_WORKERS = Math.max(1, Runtime.getRuntime().availableProcessors());
    private static final int ALPHA_DIV = 12;
    private static final int BETA_DIV = 18;

    public static List<Integer> run(Graph graph, int startVertex) {
        int[] dist = distances(graph, startVertex);
        List<Integer> order = new ArrayList<>();
        if (dist == null) return order;
        int n = graph.getVertices().size();
        int[] ids = new int[n];
        int i = 0; for (int id : graph.getVertices().keySet()) ids[i++] = id; Arrays.sort(ids);
        int maxd = -1; for (int d : dist) if (d > maxd) maxd = d;
        if (maxd < 0) return order;
        Map<Integer,Integer> idToIdx = new HashMap<>(n*2);
        for (int k = 0; k < n; k++) idToIdx.put(ids[k], k);
        for (int d = 0; d <= maxd; d++) {
            for (int id : ids) {
                Integer idx = idToIdx.get(id);
                if (idx != null && dist[idx] == d) order.add(id);
            }
        }
        return order;
    }

    public static int[] distances(Graph graph, int startVertex) {
        Set<Integer> keySet = graph.getVertices().keySet();
        if (!keySet.contains(startVertex)) return null;
        int n = keySet.size();
        int[] idxToId = new int[n];
        int[] sorted = new int[n];
        int k = 0; for (int id : keySet) sorted[k++] = id; Arrays.sort(sorted);
        for (int i = 0; i < n; i++) idxToId[i] = sorted[i];
        Map<Integer,Integer> idToIdx = new HashMap<>(n*2);
        for (int i = 0; i < n; i++) idToIdx.put(idxToId[i], i);

        int[] rowPtr = new int[n + 1];
        for (int i = 0; i < n; i++) {
            List<Integer> nbrs = graph.getVertices().get(idxToId[i]);
            int deg = (nbrs == null) ? 0 : nbrs.size();
            rowPtr[i + 1] = rowPtr[i] + deg;
        }
        int totalEdges = rowPtr[n];
        int[] cols = new int[totalEdges];
        int[] nextPos = Arrays.copyOf(rowPtr, n + 1);
        for (int i = 0; i < n; i++) {
            List<Integer> nbrs = graph.getVertices().get(idxToId[i]);
            if (nbrs != null) {
                for (int nbId : nbrs) {
                    Integer nbIdx = idToIdx.get(nbId);
                    if (nbIdx != null) cols[nextPos[i]++] = nbIdx;
                }
            }
        }

        Integer sIdxObj = idToIdx.get(startVertex);
        if (sIdxObj == null) return null;
        int sIdx = sIdxObj;

        final boolean[] visited = new boolean[n];
        boolean[] frontier = new boolean[n];
        boolean[] nextFrontier = new boolean[n];
        int[] dist = new int[n];
        Arrays.fill(dist, -1);

        visited[sIdx] = true;
        dist[sIdx] = 0;
        frontier[sIdx] = true;
        boolean useBottomUp = false;

        ForkJoinPool pool = new ForkJoinPool(MAX_WORKERS);

        while (true) {
            int frontierCount = 0; long frontierEdges = 0L;
            for (int v = 0; v < n; v++) if (frontier[v]) { frontierCount++; frontierEdges += (rowPtr[v+1]-rowPtr[v]); }
            if (frontierCount == 0) break;

            if (!useBottomUp) {
                if (frontierEdges > (long) totalEdges / ALPHA_DIV || frontierCount > n / BETA_DIV) useBottomUp = true;
            }

            Arrays.fill(nextFrontier, false);

            if (!useBottomUp) {
                int[] parents = new int[frontierCount]; int pi=0; for (int v = 0; v < n; v++) if (frontier[v]) parents[pi++] = v;
                final boolean[] visitedSnap = visited; final int[] rowPtrRef=rowPtr; final int[] colsRef=cols; final int[] parentsRef = parents; final boolean[] nextRef = nextFrontier;
                int workers = Math.min(MAX_WORKERS, frontierCount);
                int base = frontierCount / workers, rem = frontierCount % workers; int start = 0;
                List<Callable<Void>> tasks = new ArrayList<>(workers);
                for (int w = 0; w < workers; w++) {
                    int size = base + (w < rem ? 1 : 0); int s=start; int e=s+size; start=e;
                    tasks.add(() -> {
                        for (int i2 = s; i2 < e; i2++) {
                            int v = parentsRef[i2];
                            for (int p = rowPtrRef[v]; p < rowPtrRef[v+1]; p++) {
                                int nb = colsRef[p];
                                if (!visitedSnap[nb]) nextRef[nb] = true;
                            }
                        }
                        return null;
                    });
                }
                try { for (Future<Void> f : pool.invokeAll(tasks)) f.get(); }
                catch (InterruptedException ie){Thread.currentThread().interrupt(); throw new RuntimeException(ie);} 
                catch (ExecutionException ee){ throw new RuntimeException(ee.getCause()); }
            } else {
                final boolean[] frontierSnap = frontier; final int[] rowPtrRef=rowPtr; final int[] colsRef=cols; final boolean[] nextRef = nextFrontier;
                int workers = MAX_WORKERS; int base = n / workers, rem = n % workers; int start = 0;
                List<Callable<Void>> tasks = new ArrayList<>(workers);
                for (int w = 0; w < workers; w++) {
                    int size = base + (w < rem ? 1 : 0); int s=start; int e=s+size; start=e;
                    tasks.add(() -> {
                        for (int u = s; u < e; u++) {
                            if (!visited[u]) {
                                for (int p = rowPtrRef[u]; p < rowPtrRef[u+1]; p++) {
                                    int nb = colsRef[p];
                                    if (frontierSnap[nb]) { nextRef[u] = true; break; }
                                }
                            }
                        }
                        return null;
                    });
                }
                try { for (Future<Void> f : pool.invokeAll(tasks)) f.get(); }
                catch (InterruptedException ie){Thread.currentThread().interrupt(); throw new RuntimeException(ie);} 
                catch (ExecutionException ee){ throw new RuntimeException(ee.getCause()); }
            }

            int minFrontierDist = Integer.MAX_VALUE;
            for (int v = 0; v < n; v++) if (frontier[v]) minFrontierDist = Math.min(minFrontierDist, dist[v]);
            int level = (minFrontierDist == Integer.MAX_VALUE ? 0 : (minFrontierDist + 1));

            int newCount = 0;
            for (int v = 0; v < n; v++) {
                if (nextFrontier[v] && !visited[v]) { visited[v] = true; dist[v] = level; newCount++; }
            }

            if (useBottomUp && newCount < n / BETA_DIV) useBottomUp = false;
            if (newCount == 0) break;

            boolean[] tmp = frontier; frontier = nextFrontier; nextFrontier = tmp; Arrays.fill(nextFrontier, false);
        }

        pool.shutdown();
        return dist;
    }
}
