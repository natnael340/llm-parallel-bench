User request:
- Provide a parallel implementation of BFS for the given Graph.java.
- Original sequential algorithm (provided inline) to be used as baseline.
- Allowed to do extensive implementation changes to improve performance.
- Language: Java; Graph.java is present in the directory.

Constraints and goals per ParallelAgent contract:
- Produce a deterministic, resource-bounded parallel BFS with rigorous differential tests.
- Deliverables: algo_parallel.java (final impl), run_bfs.java (runner/tests), JUSTIFICATION.md, run_summary.txt, perf.txt.
- Keep changes bounded and deterministic; preserve public API: run(Graph,int) signature.
- Include small-N sequential fallback; cap workers to CPU count.
