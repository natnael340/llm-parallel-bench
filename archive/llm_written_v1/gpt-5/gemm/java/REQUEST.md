User provided a sequential Java tiled GEMM (matrix multiply) implementation and asked to parallelize it deterministically with tests.

Inputs:
- Java class Gemm with methods: getSize, validateMatrix, zeros, transpose, packMatrix, partialMatmul, and run (with tiling MB/NB/KB). Convenience overloads call run with defaults.
- Goal: Transform to a safe, deterministic, resource-bounded parallel implementation, plus differential tests and justification.

Constraints from Operating Contract:
- Follow PLAN → PATCH → TEST → REFINE≤2 → FINALIZE.
- Minimal bounded patch: default Tier 1 ≤3 files and ≤250 LOC net change; can escalate if needed.
- Determinism required. Bound workers to CPU count. Small-N sequential fallback.
- Provide deliverables: algo_parallel.<ext>, tests/runner, JUSTIFICATION.md, run_summary.txt, perf.txt (if perf run performed).

Design summary (to be implemented):
- Keep API the same. Add runSequential that preserves the original baseline. Implement run (parallel) that parallelizes across m-blocks for each (n0,k0) tile using a fixed-size thread pool.
- Tasks update disjoint rows in C; k-dimension accumulation remains sequential to preserve determinism.
- Fixed worker count: min(availableProcessors, number of m-tiles). Small-N fallback if operations < 1e6 or tasks < 2.
- Build a Java runner (RunGemm) to compare sequential vs parallel on edge/small/medium/large, verify determinism by repeating parallel run, and measure performance on a larger case.
