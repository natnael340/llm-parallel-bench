User request: Parallelize the provided C# BFS (Breadth-First Search) algorithm.

Constraints:
- The parallel version must be correct and produce the same output as the sequential version.
- The parallel version must be deterministic (same input always produces the same output).
- The implementation should be resource-bounded, using a sensible number of threads (e.g., based on CPU cores).
- A differential test harness is required to prove correctness and determinism.
- A JUSTIFICATION.md file must be created explaining the design choices.

Baseline sequential algorithm is provided in `Bfs.cs`.
Graph data structure is in `Graph.cs`.
Language: C#
