# Parallelization Request

## Baseline Algorithm
Breadth-First Search (BFS) graph traversal in Java

## Input Code
- Sequential BFS implementation in Java
- Uses Queue-based level-order traversal
- Returns list of vertices in visit order

## Constraints
- Language: Java
- Must maintain correctness (same output as sequential)
- Must be deterministic (same input → same output every run)
- Must respect resource bounds (CPU cores)
- Preserve public API if feasible

## Key Challenges
- BFS has inherent ordering constraints (level-by-level)
- Shared visited set creates potential race conditions
- Queue operations are sequential by nature
- Result list order must match sequential baseline
