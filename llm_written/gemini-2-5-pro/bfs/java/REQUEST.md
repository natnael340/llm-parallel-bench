The user wants to parallelize a sequential Breadth-First Search (BFS) algorithm implemented in Java.

## Input

`Bfs.java`:
```java
import java.util.*;

public class Bfs {
    public static List<Integer> run(Graph graph, int startVertex) {
        if (!graph.getVertices().containsKey(startVertex)) {
            return new ArrayList<>();
        }

        Set<Integer> visited = new HashSet<>();
        List<Integer> result = new ArrayList<>();
        Queue<Integer> queue = new LinkedList<>();

        queue.add(startVertex);

        while (!queue.isEmpty()) {
            int current = queue.poll();

            if (!visited.contains(current)) {
                visited.add(current);
                result.add(current);

                List<Integer> neighbors = graph.getVertices().get(current);
                if (neighbors != null) {
                    for (int neighbor : neighbors) {
                        if (!visited.contains(neighbor)) {
                            queue.add(neighbor);
                        }
                    }
                }
            }
        }

        return result;
    }
}
```

`Graph.java`: (Assumed structure, will be created)
A simple graph representation class.

## Constraints
- The parallel implementation must be correct and deterministic.
- The solution should be resource-bounded (e.g., using a fixed-size thread pool).
- The public API should be preserved if possible.
