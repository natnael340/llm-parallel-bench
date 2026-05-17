# Parallelization Request: BFS (Breadth-First Search)

## Input Code
- Language: C#
- Algorithm: Breadth-First Search (BFS) on an undirected graph
- Files: Graph.cs, Bfs.cs (BfsSequential.Run)

## Constraints
- Must preserve BFS level-order traversal semantics
- Must be deterministic (same input → same output every run)
- Must match sequential baseline output exactly
- Resource-bounded (cap workers to core count)
- Use C# Task Parallel Library (TPL)

## Key Challenges
- BFS has inherent level-by-level ordering dependencies
- Visited set is shared state
- Result list must preserve discovery order
- Neighbor iteration order affects output determinism
