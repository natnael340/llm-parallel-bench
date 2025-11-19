User request:

Parallelize the provided sequential C++ algorithm and write a test for it. Also provide a brief justification for the parallelization.

Given baseline code (Tarjan SCC and SCC edge reduction):
- Graph with adjacency and reverse adjacency
- Tarjan's SCC (sequential DFS)
- MinimizeEdgesInSCC builds spanning trees in forward and reverse graphs and merges results
- ReduceEdges computes SCCs then processes each SCC sequentially

Constraints and goals (from ParallelAgent contract):
- Produce a deterministic, resource-bounded parallel implementation with minimal changes
- Keep public API intact; add parallel version if needed
- Use OpenMP for C++ with explicit schedules and deterministic reductions
- Provide a differential test harness comparing baseline vs parallel on several sizes, repeat parallel runs to check determinism
- Small-N sequential fallback; bound workers to CPU cores
- Provide evidence files and a concise justification

Deliverables:
- algo_parallel.cpp (final implementation)
- test_algo.cpp (test runner)
- JUSTIFICATION.md (plain-language explanation)
- evidence files produced by running the tests