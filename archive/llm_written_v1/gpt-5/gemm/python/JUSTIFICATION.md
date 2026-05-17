This repository contains a sequential baseline (gemm_seq.py), a parallel implementation (gemm_parallel.py) with the same public API, and an external test runner (test_gemm.py) that differentially validates correctness and determinism.

API preservation
- The function gemm(A, B, alpha=1.0, C=None, beta=0, MB=64, NB=64, KB=64) keeps its signature and semantics. Helper functions (get_size, validate_matrix, generate_matrix, transpose, pack_matrix) are preserved. The test invokes both implementations identically.

Parallel partitioning and worker logic
- The baseline computes by iterating tiles over n, k, then m and calling partial_matmul to accumulate directly in C.
- In gemm_parallel.py, we parallelize across the m-tiles for each fixed (n0, k0) slab. Function _compute_block_contrib(Apack, Bpack, kb, alpha) computes the alpha-scaled contribution for one (mb x nb) block using a deterministic k-loop order and returns a dense block of size (mb x nb).
- The main gemm() prepares Bpack = pack_matrix(Bt, k0, k1, n0, n1) once per (n0, k0), then for each m0 tile it packs Apack and submits a task to the ProcessPoolExecutor. Results are merged into C strictly in ascending m0 order. This ensures that, even though tasks finish out of order, the final write to C follows the same iteration order as the baseline for equivalent numerical stability.

Determinism and numeric stability
- Each worker performs dot products in left-to-right k order, identical to the sequential inner loop, so each returned block is bitwise stable. Accumulation across k is not parallelized; only different m-tiles are concurrent, which are independent writes to disjoint rows of C for the same (n0, k0). Merging simply adds one slab’s contribution per block, preserving baseline accumulation order across (n0, k0) and then m0.

Resource bounds and small-input fast path
- Workers are bounded by min(os.cpu_count(), ceil(m/MB), 4) to avoid oversubscription in constrained environments. For small problems (m*n <= 1024) or single-core systems, gemm() defers to the sequential implementation (seq_gemm) after pre-scaling C by beta, passing beta=1.0 to avoid double scaling.

Edge cases handled
- All input validation mirrors the baseline (shape checks, numeric checks). alpha==0 short-circuits. Pre-filled C is scaled by beta exactly once.

Complexity and memory
- Time complexity remains O(m*k*n). Extra memory is the temporary Bpack, Apack per task, and returned blocks of size up to MB*NB per m-tile. No shared mutable state is accessed by workers, avoiding races and false sharing.

Testing evidence
- test_gemm.py executes two suites: small/edge cases (sequential fast path) and a medium-size parallel path. It compares the parallel output to the baseline and checks determinism by running the same inputs twice. Results: all tests passed in repeated local runs (2 suites, both successful).
