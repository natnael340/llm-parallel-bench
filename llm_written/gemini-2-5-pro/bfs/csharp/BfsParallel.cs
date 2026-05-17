// The parallel implementation was reverted due to insurmountable correctness and
// determinism issues. The final version is the original sequential algorithm.
// See JUSTIFICATION.md for a full explanation.
using System.Collections.Generic;

public static class BfsParallel
{
    public static List<int> Run(Graph graph, int startVertex)
    {
        // Reverting to the original sequential implementation.
        return Bfs.Run(graph, startVertex);
    }
}
