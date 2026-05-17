import java.util.*;
import java.util.concurrent.*;
import java.util.stream.Collectors;

public class BfsParallel {
    private static final int SMALL_N_THRESHOLD = 1000;

    public static List<Integer> run(Graph graph, int startVertex) {
        if (!graph.getVertices().containsKey(startVertex)) {
            return new ArrayList<>();
        }

        if (graph.getVertices().size() < SMALL_N_THRESHOLD) {
            return Bfs.run(graph, startVertex);
        }

        Set<Integer> visited = ConcurrentHashMap.newKeySet();
        List<Integer> result = new CopyOnWriteArrayList<>();
        List<Integer> frontier = new CopyOnWriteArrayList<>();

        frontier.add(startVertex);
        visited.add(startVertex);
        result.add(startVertex);

        int nThreads = Runtime.getRuntime().availableProcessors();
        ForkJoinPool forkJoinPool = new ForkJoinPool(nThreads);

        while (!frontier.isEmpty()) {
            final List<Integer> currentFrontier = frontier;
            List<Integer> nextFrontier = forkJoinPool.submit(() ->
                currentFrontier.parallelStream()
                    .flatMap(current -> {
                        List<Integer> neighbors = graph.getVertices().get(current);
                        return (neighbors != null) ? neighbors.stream() : null;
                    })
                    .filter(Objects::nonNull)
                    .filter(visited::add)
                    .collect(Collectors.toList())
            ).join();

            Collections.sort(nextFrontier);
            result.addAll(nextFrontier);
            frontier = nextFrontier;
        }

        forkJoinPool.shutdown();
        return new ArrayList<>(result);
    }
}
