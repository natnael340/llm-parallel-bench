User provided C# GEMM (matrix multiply) with tiling and packing, sequential. Goal: parallelize deterministically within bounded patch. Deliver algo_parallel.cs (final), tests and runner, justification, run_summary.txt, perf.txt.
Constraints:
- Keep public API method Gemm.Run signature intact and behavior.
- Deterministic results.
- Use TPL with bounded concurrency (CPU count). Preserve order where needed.
- Small-N sequential fallback.
- Build self-contained test harness to compare sequential baseline vs parallel implementation across sizes.
