import java.util.*;

public class BaselineBfs {
    public static List<Integer> run(Graph graph, int startVertex) {
        if (!graph.getVertices().containsKey(startVertex)) {
            return new ArrayList<>();
        }
        Set<Integer> visited = new HashSet<>();
        List<Integer> result = new ArrayList<>();
        Queue<Integer> queue = new LinkedList<>();
        Map<Integer,Integer> dist = new HashMap<>();
        queue.add(startVertex);
        visited.add(startVertex);
        dist.put(startVertex, 0);
        result.add(startVertex);
        while (!queue.isEmpty()) {
            int current = queue.poll();
            List<Integer> neighbors = graph.getVertices().get(current);
            if (neighbors != null) {
                for (int neighbor : neighbors) {
                    if (!visited.contains(neighbor)) {
                        visited.add(neighbor);
                        dist.put(neighbor, dist.get(current)+1);
                        result.add(neighbor);
                        queue.add(neighbor);
                    }
                }
            }
        }
        return result;
    }

    // Helper for testing distance correctness (not parallelized)
    public static Map<Integer,Integer> distances(Graph graph, int startVertex) {
        Map<Integer,Integer> dist = new HashMap<>();
        if (!graph.getVertices().containsKey(startVertex)) return dist;
        Queue<Integer> q = new ArrayDeque<>();
        q.add(startVertex);
        dist.put(startVertex, 0);
        while (!q.isEmpty()) {
            int v = q.poll();
            List<Integer> ns = graph.getVertices().get(v);
            if (ns == null) continue;
            for (int u : ns) {
                if (!dist.containsKey(u)) {
                    dist.put(u, dist.get(v)+1);
                    q.add(u);
                }
            }
        }
        return dist;
    }
}
