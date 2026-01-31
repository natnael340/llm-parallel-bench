import java.util.Collections;
import java.util.List;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

public class Graph {
    private final Map<Integer, List<Integer>> vertices;

    public Graph() {
        this.vertices = new ConcurrentHashMap<>();
    }

    public void addEdge(int u, int v) {
        vertices.computeIfAbsent(u, k -> Collections.synchronizedList(new java.util.ArrayList<>())).add(v);
        vertices.computeIfAbsent(v, k -> Collections.synchronizedList(new java.util.ArrayList<>())).add(u);
    }
    
    public void addVertex(int u) {
        vertices.computeIfAbsent(u, k -> Collections.synchronizedList(new java.util.ArrayList<>()));
    }

    public Map<Integer, List<Integer>> getVertices() {
        return vertices;
    }
}
