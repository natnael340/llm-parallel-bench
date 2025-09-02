This repository contains a baseline sequential implementation (gemm_seq_impl.cpp) and a parallel OpenMP implementation (gemm_parallel_impl.cpp) of the GEMM routine with the same public API declared in gemm_seq.hpp:

Matrix gemm(const Matrix& A, const Matrix& B, double alpha=1.0, Matrix* Cptr=nullptr, double beta=0.0, int MB=64, int NB=64, int KB=64);

API preserved
- Signature, defaults, and semantics match the original: compute C := alpha*A*B + beta*C; if Cptr==nullptr, a new m×n matrix is created and beta is ignored.
- Input validation and shape checks mirror the baseline.

Partitioning and worker count
- The algorithm keeps the baseline’s 3-level blocking over N, K, then M. We parallelize the innermost loop over the M-blocks within each fixed (n0,k0) tile.
- In gemm_parallel_impl.cpp, for each Bpack (fixed n0,k0), we execute:
  #pragma omp parallel for schedule(static) num_threads(threads)
  for (int m0 = 0; m0 < m; m0 += MB) { ... }
- Worker count threads equals min(omp_get_max_threads(), number of M blocks), thus bounding parallelism to available cores and avoiding oversubscription.

Worker logic
- Each iteration computes a disjoint M×NB tile: it packs A[m0:m1, k0:k1] (Apack) and multiplies against the shared Bpack, accumulating directly into the distinct rows C[m0:m1, n0:n1]. This preserves the baseline order for all accumulations into a given C tile, just performed by different threads on different row ranges.

Merge rule and determinism
- Because each thread writes to exclusive rows of C for the current (n0,k0) tile, there are no write-write races and no reductions. Within each tile, the summation over K is performed in the same loop order as the baseline (partialMatmul), ensuring deterministic bit-identical results even with OpenMP. The outer loops over (n0,k0) remain sequential to keep a fixed update order across tiles.

Small-input fast path
- A sequential kernel gemm_seq_kernel reproduces the exact baseline order. For small problems (m*n*k ≤ 2e5 MACs), the parallel routine calls this kernel to avoid thread overhead and keep behavior identical.

Resource bounds and avoidance of contention
- Parallelism is bounded by cores. No shared false-shared scalars are updated in parallel; threads only touch their own row slices (continuous memory segments), reducing cache conflicts. Bpack is read-only and shared safely.

Edge cases handled
- alpha==0 short-circuits; beta scaling of C is performed before parallel work (only when Cptr != nullptr); when C is newly allocated, it is zero-initialized and beta is ignored, per spec. Ragged matrices and shape mismatches throw exceptions as in the baseline.

Complexity
- Time: O(mnk). Memory: O(MB*KB + NB*KB) for temporary packs per tile (identical to baseline). Each thread allocates its own Apack; Bpack is reused.

Testing and evidence
- test_gemm.cpp compiles both implementations into one program via macro renaming and runs differential tests: exhaustive small sizes and tilings, hand-checked edge cases, and several randomized moderate cases. It also runs the parallel implementation twice to confirm determinism. Results: all tests passed on two consecutive runs, with exact equality (no tolerance) because accumulation orders match.
