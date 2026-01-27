// Convenience delegate to match deliverable naming; actual implementation is BfsParallel.
import java.util.*;

class algo_parallel {
    public static List<Integer> run(Graph g, int start) {
        return BfsParallel.run(g, start);
    }
}
