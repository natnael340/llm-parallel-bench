### Justification for Parallel GEMM Implementation

This document details the parallelization strategy for the General Matrix-Matrix Multiplication (GEMM) algorithm in `gemm_parallel.cpp`.

#### API Preservation
The parallel implementation preserves the public API defined in the sequential version. The function signature in `gemm_parallel.hpp` remains `gemm(const Matrix& A, const Matrix& B, double alpha, Matrix* Cptr, double beta, int MB, int NB, int KB)`, ensuring drop-in compatibility.

#### Partitioning Scheme and Worker Logic
The core of the sequential algorithm is a triply-nested loop that iterates over blocks of the output matrix `C`. The parallelization strategy focuses on distributing the work of computing these blocks across multiple threads. The two outer loops, which iterate over the `m` (rows) and `n` (columns) dimensions of `C`, are parallelized using an OpenMP `#pragma omp parallel for collapse(2)`.

This directive instructs OpenMP to collapse the two loops into a single larger iteration space and distribute chunks of it among a team of threads. Each thread is assigned a unique set of `(m0, n0)` starting indices, which correspond to a specific block of the output matrix `C`. For each assigned block, a thread executes the innermost loop over the `k` dimension sequentially. This includes creating local copies of sub-matrices (`Apack`, `Bpack`) and calling `partialMatmul` to compute the contribution to its assigned block of `C`.

#### Correctness and Determinism
The correctness of this approach hinges on the independence of the block computations. Since each thread writes to a disjoint region `C[m0:m1][n0:n1]` of the output matrix, there are no write-write races between threads. All threads read from the input matrices `A` and `Bt` concurrently, which is safe. This partitioning eliminates the need for locks or atomic operations, ensuring both efficiency and freedom from deadlocks.

Determinism is guaranteed because the computational work is partitioned spatially. The final value of any element `C[i][j]` depends only on the calculations performed by the single thread assigned to the block containing that element. The order in which threads complete their tasks does not alter the final result.

#### Small-Input Fast Path and Resource Management
Parallelism introduces overhead. To avoid this for small matrices, a threshold `PARALLEL_THRESHOLD_M` is used. The `#pragma omp parallel for` is guarded by an `if(m * n > PARALLEL_THRESHOLD_M * PARALLEL_THRESHOLD_M)` clause, which ensures that thread creation is skipped for small problems where sequential execution would be faster. A similar guard is applied to the initial scaling of the `C` matrix by `beta`. OpenMP manages the thread pool, typically defaulting to the number of available CPU cores, which provides sensible resource bounding.

#### Test Verification
The implementation was rigorously verified by the `test_gemm.cpp` program. This test suite performs a differential comparison between the parallel `gemm` and the sequential `gemm_seq` functions. It covers a range of scenarios:
- Small matrices (1x1, 10x10) to test the sequential fast path.
- Large and rectangular matrices (250x250, 512x128x256) to activate parallelism.
- Edge cases for `alpha` and `beta` coefficients (0.0 and 1.0).
- Both `Cptr` being provided and `nullptr`.

The tests were run twice, passing completely on both occasions with identical outputs, confirming correctness and determinism across various conditions with fixed random seeds (1, 42-50).
