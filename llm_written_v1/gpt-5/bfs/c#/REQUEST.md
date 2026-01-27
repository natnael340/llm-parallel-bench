User provided a sequential BFS algorithm in C# and stated the graph is present in the directory.
Goal: Produce a correct, deterministic, resource-bounded parallel implementation, with tests and justification.

Baseline (inline):
- Class Bfs with Run(Graph graph, int startVertex) using a Queue<int>, HashSet<int> visited, and adjacency from Graph.Vertices.

Constraints:
- Keep public API intact for final implementation: Bfs.Run(Graph,int) returns List<int>.
- Deterministic parallelism, bounded by CPU cores.
- Small-N sequential fallback.
- Differential tests vs baseline, determinism checks, and lightweight perf check.
- Minimal changes/files: use 3 code files (algo_parallel.cs, algo_sequential.cs, run_bfs.cs); do not modify Graph.cs.
