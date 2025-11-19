# Parallelization Request

## Algorithm: SCC Edge Reduction using Tarjan's Algorithm

### Input Code (C++)
Graph class implementing:
1. Tarjan's SCC algorithm (O(V+E))
2. Minimal SCC Edge Reduction (O(V+E))
3. Edge reduction by computing forward + reverse spanning trees per SCC

### Key Components:
- `FindSCCs()`: Tarjan's DFS to find all strongly connected components
- `MinimizeEdgesInSCC(scc)`: For each SCC, build forward/reverse spanning trees
- `ReduceEdges()`: Main driver that finds SCCs and reduces edges in each

### Constraints:
- Language: C++
- Determinism: Must produce identical output on repeated runs
- Correctness: Must match sequential output exactly
- Resource bounds: Cap parallelism to core count

### Parallelization Target:
Main opportunity: `ReduceEdges()` processes independent SCCs - each SCC can be processed in parallel.
Secondary: Tarjan's initial SCC detection is inherently sequential (DFS-based).

### Strategy:
Parallelize the per-SCC edge minimization loop using OpenMP parallel for with deterministic ordering.
