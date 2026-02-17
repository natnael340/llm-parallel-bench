using System;
using System.Collections.Generic;
using System.Threading.Tasks;

public static class BfsParallel
{
    // Parallel, deterministic, level-synchronous BFS
    // Public API preserved: Run(Graph graph, int startVertex) -> List<int>
    public static List<int> Run(Graph graph, int startVertex)
    {
        if (!graph.Vertices.ContainsKey(startVertex))
            return new List<int>();

        int vertexCount = graph.Vertices.Count;
        // Small-N fallback to avoid overheads
        if (vertexCount < 512)
            return BfsSequential.Run(graph, startVertex);

        var visited = new HashSet<int>();
        var result = new List<int>(capacity: Math.Max(16, vertexCount));
        var frontier = new List<int> { startVertex };

        while (frontier.Count > 0)
        {
            // 1) Visit all nodes in current level in a fixed order (frontier order)
            foreach (var v in frontier)
            {
                if (visited.Add(v))
                    result.Add(v);
            }

            // 2) Expand neighbors in parallel with fixed partitioning and deterministic merge
            //    We read from visited only (no writes in parallel region), and write to per-chunk buffers.
            int workers = Math.Min(Environment.ProcessorCount, frontier.Count);

            // For small frontier, expand sequentially to reduce overhead
            if (workers <= 1 || frontier.Count < 1024)
            {
                var candidates = new List<int>();
                foreach (var v in frontier)
                {
                    if (graph.Vertices.TryGetValue(v, out var neighbors))
                    {
                        foreach (var nei in neighbors)
                        {
                            if (!visited.Contains(nei))
                                candidates.Add(nei);
                        }
                    }
                }
                // Stable first-unique to match sequential enqueue order semantics
                var seenNext = new HashSet<int>();
                var nextFrontierSeq = new List<int>();
                foreach (var u in candidates)
                {
                    if (seenNext.Add(u))
                        nextFrontierSeq.Add(u);
                }
                frontier = nextFrontierSeq;
                continue;
            }

            int chunkCount = workers;
            int chunkSize = (frontier.Count + chunkCount - 1) / chunkCount; // ceil
            var chunkLists = new List<int>[chunkCount];
            for (int i = 0; i < chunkCount; i++) chunkLists[i] = new List<int>();

            var tasks = new Task[chunkCount];
            for (int ci = 0; ci < chunkCount; ci++)
            {
                int start = ci * chunkSize;
                int end = Math.Min(frontier.Count, start + chunkSize);
                if (start >= end)
                {
                    tasks[ci] = Task.CompletedTask;
                    continue;
                }
                var localList = chunkLists[ci];
                tasks[ci] = Task.Run(() =>
                {
                    for (int idx = start; idx < end; idx++)
                    {
                        int v = frontier[idx];
                        if (graph.Vertices.TryGetValue(v, out var neighbors))
                        {
                            // Keep adjacency order
                            foreach (var nei in neighbors)
                            {
                                // visited is read-only here (current and previous levels), safe to read without locks
                                if (!visited.Contains(nei))
                                    localList.Add(nei);
                            }
                        }
                    }
                });
            }
            Task.WaitAll(tasks);

            // Deterministic merge: concatenate chunk outputs in chunk-index order
            var merged = new List<int>();
            for (int ci = 0; ci < chunkCount; ci++)
                merged.AddRange(chunkLists[ci]);

            // Stable first-unique to form next frontier in the same order as the first enqueues would appear
            var seen = new HashSet<int>();
            var nextFrontier = new List<int>();
            foreach (var u in merged)
            {
                if (!seen.Contains(u))
                {
                    seen.Add(u);
                    if (!visited.Contains(u)) // redundant due to earlier filter, but safe
                        nextFrontier.Add(u);
                }
            }

            frontier = nextFrontier;
        }

        return result;
    }
}
