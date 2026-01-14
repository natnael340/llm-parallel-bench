Why ProcessPoolExecutor was avoided

Summary
Our first attempt used ProcessPoolExecutor to parallelize each anti-diagonal. Although correct and deterministic when writing back in fixed order, it was significantly slower and added complexity. We replaced it with NumPy vectorization, which is both faster and simpler.

Main issues with ProcessPoolExecutor
1) High overhead per task (IPC + pickling)
   - Each diagonal requires shipping helper arrays (up/left/diag values) and parameters to worker processes, then collecting results.
   - For diagonals with tens to a few hundred cells, serialization and inter-process communication costs dominate the small compute per cell.

2) Poor cache locality and memory pressure
   - Data are copied to child processes (especially on platforms using spawn). This duplicates memory and defeats locality benefits.
   - Workers compute on small slices that are then merged, causing extra allocation and copies.

3) Scheduling and determinism handling complexity
   - We must partition diagonals, submit jobs, and then reassemble in order. Even with ordered collection, this adds boilerplate and error surface.
   - With many small tasks, completion order is unpredictable; extra sorting/ordering steps add overhead.

4) Oversubscription risk when combined with numeric kernels
   - NumPy (and linked BLAS) may use internal threading. Mixing process pools and threaded kernels can oversubscribe cores, hurting throughput and latency.

5) Portability and startup costs
   - On Windows/CI (spawn), process startup and module import per worker are noticeable. This is repeated across many diagonals.

Measured impact (on this machine)
- ProcessPool version: For 512×512 case, sequential took ≈0.24 s; process-based “parallel” took ≈9.27 s (≈0.03× speedup, i.e., 30× slower).
- NumPy vectorized version: ≈0.10 s (≈2.33× faster than sequential).
- See perf.txt for final numbers; the process-pool timing was observed during development and is noted here for rationale.

Why NumPy vectorization instead
- Anti-diagonals map naturally to vector operations: read three neighbor bands, compute candidates, take elementwise max, and write back.
- NumPy executes in optimized C with SIMD and controlled threading, avoiding Python-level loop and IPC overhead while keeping deterministic updates.

When ProcessPoolExecutor might make sense
- Running many independent alignments (batching different (query, reference) pairs) where each alignment is large, so each task is coarse-grained.
- Not for intra-algorithm fine-grained steps like per-diagonal parallelism.

Safeguards kept
- Small-N sequential fallback to avoid overhead on tiny inputs.
- Deterministic, fixed-order writes per diagonal; integer operations only.
