User provided a Go implementation of the Smith-Waterman local alignment algorithm with a sequential dynamic programming (DP) matrix fill and a traceback to build the alignment.

Goal: Produce a correct, deterministic, resource-bounded parallel version, tests, and justification following the required PLAN → PATCH → TEST → FINALIZE loop.

Key functions in the provided code:
- type SmithWaterman { matchScore, mismatchScore, gapScore int }
- NewSmithWaterman
- max
- ConstructMatrix(query, reference string) [][]int  // sequential DP fill
- FindHighestScore(H [][]int) (int, int)
- Traceback(H [][]int, query, reference string) (string, string, int, float64)
- FindAlignment(query, reference string)
- main() demo

Constraints:
- Deterministic parallelization
- Bounded concurrency (no unbounded goroutines)
- Preserve public API; provide sequential baseline and parallel implementation with minimal changes
- Provide a test/runner that compares sequential vs parallel across sizes, checks determinism, and measures perf on large N
- Deliverables: algo_parallel.go, run_sw.go (test runner), JUSTIFICATION.md, evidence files
