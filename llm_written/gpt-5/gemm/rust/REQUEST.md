User provided a sequential Rust implementation of tiled GEMM (general matrix multiply) with helper functions and requested a parallel, deterministic, resource-bounded implementation plus rigorous differential tests and justification.

Provided baseline (simplified):
- Matrix = Vec<Vec<f64>>
- validate_matrix, zeros, transpose, pack_matrix
- partial_matmul (operates on packed tiles)
- gemm(): loops over N tiles → K tiles → M tiles, packs tiles, calls partial_matmul to accumulate into C
- gemm_simple(): convenience wrapper

Constraints:
- Produce a correct, deterministic parallel version.
- Build tests that compare sequential vs parallel on multiple sizes, repeat parallel ≥3 times for determinism, and hash outputs.
- Provide small-N sequential fallback, bounded worker count.
- Write JUSTIFICATION.md and files: algo_parallel.rs, tests/runner, run_summary.txt, perf.txt.

Environment:
- Single-binary Rust project (Cargo.toml present). For portability in this environment, avoid external crates in code that’s compiled via rustc-only tool; implement parallelism with std threads.
