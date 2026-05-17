User provided a sequential Java implementation of Smith-Waterman local alignment with linear gap.
Goal: produce a deterministic, resource-bounded parallel implementation and a differential test harness.
Constraints:
- Maintain public API for alignment result but can add new class for parallel.
- Use bounded threads (ForkJoinPool or ExecutorService), deterministic fixed split.
- Provide small-N sequential fallback.
- Provide correctness parity, determinism tests, and basic perf check.
Deliverables:
- algo_parallel.java (final impl)
- test_<algo>.java and/or run_<algo>.java
- JUSTIFICATION.md (250–450 words)