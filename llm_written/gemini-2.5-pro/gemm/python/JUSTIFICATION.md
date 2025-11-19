
## Parallel GEMM Justification

This document explains the parallelization strategy for the `gemm` (General Matrix Multiplication) function, implemented in `gemm_parallel.py`.

### 1. API Stability
The public API of the parallel `gemm` function remains identical to the original sequential version:
`gemm(A, B, alpha=1.0, C=None, beta=0.0, MB=64, NB=64, KB=64)`.
It accepts the same parameters and produces the same output, ensuring it's a drop-in replacement. The original sequential logic was preserved in `gemm_sequential` for baseline testing and as a fallback.

### 2. Partitioning Scheme and Worker Logic
The parallelization strategy is based on data parallelism, specifically by partitioning the output matrix `C` into non-overlapping blocks. The nested loops over `m` (rows of A) and `n` (columns of B) are the outermost loops in the parallel design, making them ideal for parallelization.

- **Partitioning**: The `gemm` function generates a list of tasks, where each task corresponds to computing one `MB x NB` block of the final matrix `C`. A task is defined by a tuple `(alpha, m0, n0, m1, n1, k, KB)`, representing the metadata needed to compute the sub-matrix `C[m0:m1, n0:n1]`.

- **Worker Logic**: The `_gemm_worker` function is executed by each process in a `ProcessPoolExecutor`. It receives a task tuple and computes its assigned block of `C`. Crucially, each worker creates its own local result matrix, `C_block`, preventing any race conditions. The worker iterates through the full `k` dimension (in `KB`-sized chunks) to compute the final values for its block, performing a series of smaller matrix multiplications (`A_pack` * `B_pack`) and accumulating the results locally.

### 3. Merge Step and Determinism
- **Merge**: After a worker completes its computation, it returns its starting coordinates (`m0`, `n0`) and the computed `C_block`. The main process receives these results asynchronously via `concurrent.futures.as_completed` and adds the values from `C_block` into the corresponding region of the final matrix `C`. Since each worker writes to a distinct, non-overlapping block of `C`, the order of completion and merging does not affect the final result, guaranteeing determinism. This was verified by the `test_determinism` case in `test_gemm.py`.

- **Resource Management**: Parallelism is bounded by `os.cpu_count()`, creating a worker pool that matches the available hardware cores to avoid over-subscription. To minimize data transfer to child processes, the large matrices `A` and `B_t` (transposed B) are passed to the pool's `initializer` (`_init_worker`). This leverages the OS's copy-on-write memory management, making the matrices available in each worker's address space without expensive serialization.

### 4. Small-Input Fast Path
A sequential fast path is included. The `gemm` function calculates the total number of blocks to be computed. If this number is less than or equal to the number of available CPU cores, the overhead of creating a process pool would likely outweigh the benefits of parallelism. In such cases, the function directly calls the `gemm_sequential` implementation.

### 5. Verification and Correctness
The parallel implementation was rigorously verified using the `test_gemm.py` script.
- **Differential Testing**: The parallel `gemm` output was compared against the `gemm_sequential` baseline for a wide range of matrix shapes, sizes, and block configurations, including prime and non-power-of-two dimensions.
- **Edge Cases**: Tests for `alpha` and `beta` scaling factors confirmed they are handled correctly.
- **Determinism**: The `test_determinism` function ran the same parallel computation twice and asserted that the results were bit-for-bit identical.
- **Test Results**: All 6 tests passed across two separate runs, confirming the implementation is correct, robust, and deterministic.
