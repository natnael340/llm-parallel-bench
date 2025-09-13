The sequential `Gemm` algorithm was parallelized by decomposing the matrix multiplication problem into independent subproblems. The chosen approach leverages Go's native concurrency features to achieve parallelism while ensuring correctness and determinism.

**API Preservation**
The public API `Gemm(A, B Matrix, alpha float64, C Matrix, beta float64, MB, NB, KB int) (Matrix, error)` remains unchanged. The function signature, parameters, and return values are identical to the sequential version, ensuring drop-in compatibility.

**Partitioning Scheme & Worker Management**
The core of the parallelization strategy lies in partitioning the work based on blocks of the output matrix `C`. The two outer loops of the sequential algorithm, which iterate over the `m` (rows) and `n` (columns) dimensions of `C`, define independent tasks. Each task consists of calculating a full `MB x NB` block of the `C` matrix.

A bounded worker pool, managed by a semaphore (`sem`), is used to control concurrency. The number of concurrent workers is limited to `runtime.NumCPU()`, which prevents the creation of an excessive number of goroutines that could lead to performance degradation from scheduling overhead. A `sync.WaitGroup` is used to ensure the main function waits for all block computations to complete before returning.

**Worker Logic & Merge Rule**
Each goroutine is assigned a specific `(m0, n0)` block of the output matrix. The worker's logic involves iterating through the entire `k` dimension (in `KB`-sized chunks) to compute the final values for its assigned block. The "merge" step is implicit and race-free: since each worker writes to a distinct, non-overlapping region of the `C` matrix, results are written directly into their final locations without needing locks or atomic operations. This design is crucial for both correctness and performance.

**Determinism & Correctness**
Determinism is guaranteed because the floating-point additions for any given element `C[i][j]` always occur in the same order as in the sequential version (i.e., iterating through the `k` dimension). The parallelization only changes the order in which different `(i, j)` blocks are computed, not the order of operations within a block.

The correctness of the parallel implementation is verified by the `gemm_test.go` file. This test suite performs differential testing by comparing the output of the parallel `Gemm` against the original `gemmSequential` function across various matrix sizes, block sizes, and edge cases (e.g., `alpha=0`, `beta=0`, `nil` input `C`). A dedicated `TestDeterminism` function runs the parallel computation twice with identical inputs and confirms the outputs are bit-for-bit identical. All 13 test cases passed successfully across multiple runs.

**Small-Input Fast Path**
For small matrices where the total number of `MB x NB` blocks is less than the number of available CPU cores, the overhead of goroutine creation and scheduling can outweigh the benefits of parallelism. To handle this, a sequential fast path is implemented: if `numMBlocks * numNBlocks < runtime.NumCPU()`, the original `gemmSequential` function is called directly.
