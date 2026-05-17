User provided a sequential tiled GEMM (matrix multiply) in C# (namespace GemmBenchmark, class Gemm). Task: Transform into a correct, deterministic, resource-bounded parallel implementation with rigorous differential tests and justification. Deliverables: algo_parallel.cs, run_gemm.cs, JUSTIFICATION.md, run_summary.txt, perf.txt.

Constraints:
- Keep correctness parity with baseline
- Determinism across runs
- Bounded parallelism (<= CPU cores)
- Small-N sequential fallback
- Add tests covering edge/small/medium/large; repeat parallel >=3 times
- Prefer TPL in C#
- Implement fixed order combines to avoid FP drift
