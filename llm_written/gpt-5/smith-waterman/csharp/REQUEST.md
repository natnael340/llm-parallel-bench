User provided a sequential C# implementation of Smith-Waterman local alignment (dynamic programming) with methods:
- ConstructMatrix(query, reference): fills DP matrix H (int[][]) row by row
- FindHighestScore(H): scans for max
- Traceback(H, query, reference): backtracks from max to build local alignment
- FindAlignment(query, reference): convenience wrapper

Task: Transform to a correct, deterministic, resource-bounded parallel implementation, provide differential tests and justification.

Constraints/Plan:
- Preserve public API surface; provide parallel drop-in with same methods.
- Parallelize only the matrix construction (core bottleneck). Traceback and max scan can remain sequential.
- Use wavefront (anti-diagonal) parallelism: cells with i+j constant are independent.
- Use TPL Parallel.For with fixed MaxDegreeOfParallelism <= Environment.ProcessorCount.
- Provide small-N sequential fallback to avoid overhead.
- Determinism by fixed partitioning and barrier between diagonals (each Parallel.For completes before next diagonal).
- Build test harness that compares sequential vs parallel outputs on multiple sizes; repeat parallel twice to test determinism; capture performance on large N when CPUCount>1 and run long enough.
- Evidence written to evidence/run_summary.txt and evidence/perf.txt.
