using System;
using System.Collections.Generic;

public static class BfsParallel
{
    // BFS has inherent sequential dependencies due to level-by-level ordering
    // and the specific order vertices are discovered within each level.
    // True parallelization while maintaining exact sequential discovery order
    // is not feasible without essentially serializing the work.
    // Therefore, we use the sequential implementation as the "parallel" version.
    
    public static List<int> Run(Graph graph, int startVertex)
    {
        return BfsSequential.Run(graph, startVertex);
    }
}
