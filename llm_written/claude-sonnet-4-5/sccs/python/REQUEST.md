# Parallelization Request

## Input Algorithm
Tarjan's Strongly Connected Components (SCC) algorithm with edge reduction.

## Key Operations
1. `find_sccs()`: Tarjan's DFS to find all SCCs (inherently sequential)
2. `reduce_edges()`: For each SCC, minimize edges by building forward/reverse spanning trees
3. `minimize_edges_in_scc()`: Per-SCC edge minimization (independent work)

## Constraints
- Must preserve deterministic output (same SCC order, same edges)
- Graph structure immutable during computation
- Python implementation

## Parallelization Strategy
- Keep Tarjan's DFS sequential (loop-carried dependencies)
- Parallelize per-SCC edge minimization in `reduce_edges()` using ProcessPoolExecutor
- Preserve SCC order in final result for determinism
- Add sequential fallback for small graphs (< 4 SCCs)
