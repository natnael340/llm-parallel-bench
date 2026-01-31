User provided a Rust implementation of a directed graph with Tarjan's SCC and a method to reduce edges within SCCs by taking DFS spanning trees in forward and reverse graphs and merging them. The goal: transform it into a deterministic, resource-bounded parallel implementation with rigorous differential tests and performance checks.

Key snippet (baseline essence):
- Graph with adjacency and reverse adjacency lists
- Tarjan DFS to find SCCs (sequential)
- For each SCC, build a forward and reverse DFS spanning tree within the SCC and merge edges
- reduce_edges() iterates SCCs sequentially and accumulates edges

Constraints per project brief:
- Follow PLAN → PATCH → TEST → REFINE ≤2 → FINALIZE
- Provide deterministic parallelization (prefer Rayon; if unavailable, use bounded std threads)
- Deliverables: algo_parallel.rs, run_algo.rs (runner), JUSTIFICATION.md, run_summary.txt, perf.txt
- Determinism: fixed partitioning and fixed combine order
- Performance: attempt speedup on large input; include small-N sequential fallback