# Parallel BFS Request

## Input
Sequential breadth-first search (BFS) implementation for undirected graphs.

## Constraints
- BFS has level-synchronous structure: must process all nodes at distance d before distance d+1
- Visit order within a level can vary, but must be deterministic across runs
- Graph structure is read-only during traversal
- Must handle: empty graph, single vertex, disconnected components, cycles

## Strategy
Level-synchronous parallel BFS:
- Process each BFS level in parallel
- Within a level, workers process frontier vertices independently
- Use set-based visited tracking (thread-safe)
- Sort neighbors within each level for deterministic ordering
- Small frontier: sequential fallback

## Language
Python with ProcessPoolExecutor for CPU-bound work
