User provided a sequential Java GEMM (tiled/packed) implementation and requested a correct, deterministic, resource-bounded parallel version with rigorous differential tests and justification. We must follow PLAN → PATCH → TEST → REFINE≤2 → FINALIZE. Language: Java. Use bounded parallelism (ForkJoinPool or fixed thread pool), ensure determinism, small-N fallback, and provide:
- algo_parallel.java (final implementation)
- test/run files
- JUSTIFICATION.md (600–1100 words)
- run_summary.txt, perf.txt
