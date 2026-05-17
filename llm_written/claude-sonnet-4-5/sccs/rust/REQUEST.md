# Parallelization Request

## Algorithm
Tarjan's Strongly Connected Components (SCC) algorithm with edge reduction

## Language
Rust

## Baseline Implementation
- Sequential Tarjan's SCC using DFS
- Builds forward and reverse spanning trees for each SCC
- Minimizes edges within each SCC
- Public API: Graph::new(), add_edge(), find_sccs(), minimize_edges_in_scc(), reduce_edges()

## Constraints
- Must maintain correctness (same SCCs found)
- Must be deterministic (same output every run)
- Respect resource bounds (CPU core count)
- Preserve public API where feasible
