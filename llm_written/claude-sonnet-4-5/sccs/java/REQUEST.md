# Parallelization Request

## Original Algorithm
Sequential Java implementation of Tarjan's Strongly Connected Components (SCC) algorithm with minimal edge reduction.

## Key Operations
1. **findSCCs()**: Tarjan's DFS-based SCC detection (O(V+E))
2. **minimizeEdgesInSCC()**: For each SCC, builds forward and reverse spanning trees to find minimal edge set
3. **reduceEdges()**: Orchestrates SCC finding and per-SCC edge minimization

## Constraints
- Language: Java
- Must maintain correctness (same output as sequential)
- Must be deterministic (same input → same output every run)
- Resource-bounded parallelism (respect CPU core count)
- Preserve public API where feasible

## Input Characteristics
- Graph with V vertices and E edges
- Directed graph (adjacency list + reverse adjacency list)
- Can have multiple SCCs of varying sizes
