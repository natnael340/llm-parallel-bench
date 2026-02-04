import java.util.*;
import java.util.concurrent.*;
import java.util.stream.IntStream;

public class BfsParallel {
    private static final int SEQUENTIAL_THRESHOLD = 100;
    private final ForkJoinPool pool;

    public BfsParallel() {
        // Bound parallelism to available processors
        this(Runtime.getRuntime().availableProcessors());
    }

    public BfsParallel(int parallelism) {
        this.pool = new ForkJoinPool(parallelism);
    }

    public List<Integer> run(Graph graph, int startVertex) {
        if (!graph.getVertices().containsKey(startVertex)) {
            return new ArrayList<>();
        }

        int graphSize = graph.getVertices().size();
        
        // Use sequential for small graphs
        if (graphSize <= SEQUENTIAL_THRESHOLD) {
            return BfsSequential.run(graph, startVertex);
        }

        return runParallel(graph, startVertex);
    }

    private List<Integer> runParallel(Graph graph, int startVertex) {
        try {
            return pool.submit(() -> bfsLevelSynchronous(graph, startVertex)).get();
        } catch (InterruptedException | ExecutionException e) {
            throw new RuntimeException("Parallel BFS failed", e);
        }
    }

    private List<Integer> bfsLevelSynchronous(Graph graph, int startVertex) {
        Set<Integer> visited = new HashSet<>();
        List<Integer> result = new ArrayList<>();
        
        // Current level to process
        List<Integer> currentLevel = new ArrayList<>();
        currentLevel.add(startVertex);
        visited.add(startVertex);

        while (!currentLevel.isEmpty()) {
            // Add current level to result (already in correct order)
            result.addAll(currentLevel);

            // Discover next level in parallel while preserving order
            List<Integer> nextLevel = discoverNextLevel(graph, currentLevel, visited);
            currentLevel = nextLevel;
        }

        return result;
    }

    private List<Integer> discoverNextLevel(Graph graph, List<Integer> currentLevel, Set<Integer> visited) {
        int levelSize = currentLevel.size();
        
        // For very small levels, process sequentially
        if (levelSize < 4) {
            List<Integer> nextLevel = new ArrayList<>();
            for (int vertex : currentLevel) {
                List<Integer> neighbors = graph.getVertices().get(vertex);
                if (neighbors != null) {
                    for (int neighbor : neighbors) {
                        if (!visited.contains(neighbor) && visited.add(neighbor)) {
                            nextLevel.add(neighbor);
                        }
                    }
                }
            }
            return nextLevel;
        }

        // Phase 1: Parallel neighbor discovery (read-only on visited set)
        // Each vertex collects its neighbors without modifying visited
        List<List<Integer>> perVertexCandidates = new ArrayList<>(levelSize);
        for (int i = 0; i < levelSize; i++) {
            perVertexCandidates.add(null);
        }

        IntStream.range(0, levelSize).parallel().forEach(i -> {
            int vertex = currentLevel.get(i);
            List<Integer> neighbors = graph.getVertices().get(vertex);
            List<Integer> candidates = new ArrayList<>();
            
            if (neighbors != null) {
                // Just collect neighbors, don't check visited yet
                candidates.addAll(neighbors);
            }
            
            perVertexCandidates.set(i, candidates);
        });

        // Phase 2: Sequential processing to maintain deterministic order
        // Process candidates in the order they were discovered
        List<Integer> nextLevel = new ArrayList<>();
        for (List<Integer> candidates : perVertexCandidates) {
            if (candidates != null) {
                for (int neighbor : candidates) {
                    // Check and mark as visited in deterministic order
                    if (!visited.contains(neighbor) && visited.add(neighbor)) {
                        nextLevel.add(neighbor);
                    }
                }
            }
        }

        return nextLevel;
    }

    public void shutdown() {
        pool.shutdown();
    }
}
