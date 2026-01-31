User provided a Python Graph class implementing Tarjan's SCC algorithm and a function to reduce edges inside each SCC by building forward and reverse spanning trees. Goal: produce a deterministic, resource-bounded parallel implementation with rigorous differential tests and justification.

Provided snippet (summary):
- Graph with add_edge, Tarjan DFS (recursive), find_sccs.
- build_spanning_tree returns a set of edges using DFS over adjacency list.
- minimize_edges_in_scc builds forward and reverse spanning trees starting at scc[0], merges them into a list.
- reduce_edges finds all SCCs and concatenates minimized edges from each SCC.

Constraints and expectations (from system instructions):
- Strict PLAN → PATCH → TEST → (optional) REFINE≤2 → FINALIZE loop.
- Correctness and determinism over performance.
- Build a separate test runner that compares sequential baseline vs parallel results, repeats parallel runs for determinism, and includes a basic performance check.
- Deliverables: algo_parallel.py, run/test script, JUSTIFICATION.md, run_summary.txt, perf.txt.
