Parallelization summary

Files:
- gemm_parallel.go: parallel, deterministic GEMM implementation with the same API as described.
- test_gemm.go: self-contained test runner performing differential testing against the sequential baseline and edge/error cases.

API preservation
- Function Gemm(A, B Matrix, alpha float64, C Matrix, beta float64, MB, NB, KB int) (Matrix, error) is kept identical.
- Helper types and functions (Matrix, getSize, validateMatrix, generateMatrix, transpose, packMatrix, partialMatmul) retain original semantics.

Partitioning and worker model
- Parallelism is introduced only along the outer m-dimension tile loop in Gemm. For each (n0, k0) tile, the m-loop is split into [m0,m1) chunks of height MB. These chunks are sent via a bounded job channel mJobs to a worker pool sized to min(GOMAXPROCS(), number of m-chunks). Each worker packs its local A submatrix and calls partialMatmul(Apack, Bpack, C, alpha, m0Local, n0, kb).
- This is safe because each job updates a disjoint set of rows in C: C[m0:m1][n0:n1]. No two workers touch the same C indices for fixed (n0,k0), eliminating write races without locks.

Determinism and merge rule
- The only floating-point accumulation is performed within partialMatmul over k in strictly increasing order; that order is identical for all workers. Across different k-tiles (k0 blocks), the same cell C[i][j] is updated sequentially by the outer loops in fixed order (n0 then k0 increasing). We do not perform parallel reductions into the same element, so the summation order matches the sequential version, ensuring deterministic, bit-reproducible results.

Resource bounds and small-input fast path
- Worker count is bounded: workers = min(GOMAXPROCS(), ceil(m/MB)); never spawns unbounded goroutines. mJobs is closed and each worker signals completion on the done channel, preventing leaks or deadlocks.
- For small problems (m*n <= 1000 or degenerate dimensions), Gemm dispatches to gemmSequential to avoid parallel overhead.

Edge cases and validation
- Input validation mirrors the baseline. C is scaled by beta before compute; alpha==0 short-circuits to return C. Ragged/nil rows and shape mismatches are detected.

Complexity
- Time complexity remains O(mkn). Memory overhead is O(m+n) for transpose(B) and transient slices for packing views; no extra large buffers are allocated per worker besides small slice headers.

Testing evidence
- The runner generates edge cases (1x1, vectors), random small and larger matrices, and shape-mismatch checks. It compares Gemm vs gemmSequential with tolerance 1e-12 and prints a per-case status. Random seed is fixed (1337) for reproducibility.
