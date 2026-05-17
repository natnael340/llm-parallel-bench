import java.util.*;

public class Graph {
    private final Map<Integer, List<Integer>> vertices = new HashMap<>();

    public Map<Integer, List<Integer>> getVertices() {
        return vertices;
    }

    public void addEdge(int fromVertex, int toVertex) {
        vertices.computeIfAbsent(fromVertex, k -> new ArrayList<>());
        vertices.computeIfAbsent(toVertex, k -> new ArrayList<>());

        vertices.get(fromVertex).add(toVertex);
        vertices.get(toVertex).add(fromVertex);
    }
}
