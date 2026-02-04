## Decision Summary

- **Baseline bottleneck:** The original code processes the outermost loop (`m` dimension) sequentially. For large matrices, this represents a significant amount of independent work that can be done in parallel.
- **Chosen strategy:** Parallelize the outermost loop over the `m` dimension blocks using `Parallel.For`. This approach assigns different blocks of rows of the output matrix `C` to different threads.
- **Why it is safe (determinism):** Each parallel task writes to a unique, non-overlapping block of the output matrix `C`. There are no shared memory locations being written to simultaneously by different threads, eliminating the possibility of race conditions. The order of floating-point additions is preserved within each `PartialMatmul` call, and since the writes are to independent locations, the final result is deterministic.
- **Why it is faster:** The computationally expensive `PartialMatmul` calls for different row blocks of matrix `A` are executed concurrently. For large matrices, this allows the workload to be distributed across multiple CPU cores, significantly reducing the total execution time.
- **Worker count + chunk rule:** The `Parallel.For` loop uses the default .NET thread pool, which manages the number of threads up to the number of available logical processors. The work is chunked by blocks of `MB` rows.
- **Small-N fallback threshold:** No explicit threshold is set; `Parallel.For` has its own internal heuristics that may use a sequential execution for very small loop counts where the overhead of parallelization would not be beneficial.
- **Best rejected alternative + one key reason:** Parallelizing the two outer loops (over `n` and `m` dimensions) was rejected because it would introduce significant locking overhead or require thread-local storage and a final reduction step to safely update the shared matrix `C`, adding complexity and potentially reducing performance gains.

## What Changed and Why

The original sequential process calculates the product of two matrices, `A` and `B`, and stores it in a result matrix `C`. It does this by breaking the matrices down into smaller rectangular blocks or "tiles." It then iterates through these blocks one by one. For each block, it performs a small matrix multiplication (`PartialMatmul`) and adds the result to the corresponding block in the final matrix `C`. This tiling strategy is good for CPU caches, but the loops that process these tiles were sequential, meaning only one block was processed at a time.

Imagine you have a large grid to paint (matrix `C`). The sequential approach is like one person painting one square tile of the grid at a time, row by row, until the entire grid is filled.

## How We Made It Parallel

We identified that the calculations for different row-blocks of the output matrix `C` are independent of each other. This means we can calculate them at the same time without them interfering.

1.  **Splitting the work:** The main change was to the loop that iterates over the rows of matrix `A` (the `m` dimension). We wrapped this loop in a `Parallel.For` construct from C#'s Task Parallel Library. This automatically divides the loop iterations (which correspond to row blocks) into chunks.
2.  **Worker tasks:** The .NET runtime assigns each chunk of row blocks to a worker thread from its thread pool. Each worker thread is responsible for computing the results for its assigned rows.
3.  **Independent writes:** Crucially, each worker thread writes its results to a different, pre-assigned section of the output matrix `C`. Worker 1 might handle rows 0-63, Worker 2 handles rows 64-127, and so on. They never need to write to the same memory location.
4.  **Combining results:** Because each worker writes directly to its designated part of the final `C` matrix, there is no separate "merge" or "combine" step. The matrix is complete once the last worker finishes its task.

Here is a sketch of the process:

Input (`A` blocks) ▶ [Block A1][Block A2][Block A3]
                          │         │         │
                       Worker1   Worker2   Worker3
                          │         │         │
                          ▼         ▼         ▼
Output (`C` blocks) ▶ [Block C1][Block C2][Block C3]

## Why the Answer Is Always the Same (Determinism)

-   **Fixed splitting:** For a given matrix size, `Parallel.For` with the chosen block division will always create the same set of tasks. Each task corresponds to a fixed range of rows in the output matrix.
-   **No ordering conflicts:** Since each thread writes to a completely separate part of the output matrix `C`, the order in which threads finish their work doesn't matter. The final result will be the same regardless of whether Worker 1 finishes before or after Worker 2.
-   **Preserved floating-point order:** The `PartialMatmul` function, which contains the floating-point additions, is unchanged and is executed sequentially within each thread. This means the order of additions for any given output element is always the same, preventing tiny floating-point variations that can occur with parallel reductions.
-   **No race conditions:** There are no shared variables that are read and written by multiple threads at the same time without locks. The output matrix `C` is shared for writing, but each thread writes to an exclusive, non-overlapping region.

## Proof It Works

-   **Correctness Parity:** The parallel implementation produces numerically identical results to the sequential one across a range of matrix sizes, from 1x1 to 512x512, as well as non-square matrices. The `run_summary.txt` file shows "Correctness: PASS" for all test cases.
-   **Determinism:** Running the parallel implementation three times on the same input matrices produces bit-for-bit identical output matrices. This is confirmed by comparing the SHA-256 hashes of the resulting matrices. For example, for the 128x128 case, all three runs produced the hash `2abf45043726bed6476e99b65fa75da593959f243c28679c895c12225c59b50f`. Details for all cases are in `run_summary.txt`.
-   **Performance:** On a large 1024x1024 matrix multiplication, the parallel version was significantly faster than the sequential one. The performance results are documented in `perf.txt`, showing a speedup of approximately 5.93x on a machine with 16 logical cores.

## Limits & Safety Switches

-   **Small Inputs:** For very small matrices, the overhead of creating and scheduling parallel tasks might make the parallel version slightly slower than the sequential one. We rely on the `Parallel.For` implementation's internal logic to manage this, which often executes small workloads sequentially.
-   **Resource Bounds:** The number of threads is managed by the .NET default thread pool, which is automatically configured to make efficient use of the available CPU cores without oversubscription. This prevents the application from creating too many threads and slowing down the system.
-   **Handled Corner Cases:** The code handles empty matrices and shape mismatches by throwing exceptions before any computation begins, for both sequential and parallel versions.

## How to Reproduce

To reproduce these results, you can run the provided test harness from the command line:

1.  **Rerun all correctness and determinism checks:**
    ```bash
    dotnet run --project .
    ```
2.  **Review the output:** The console will print the status of each test, and the detailed results will be saved in `run_summary.txt` and `perf.txt`.

## Alternatives We Considered

1.  **Parallelize the two outer loops (`n` and `m` dimensions):**
    -   *What it would do:* This would involve creating parallel tasks for each `(m0, n0)` block combination.
    -   *Why it loses here:* The `PartialMatmul` function modifies a shared `C` matrix. If we parallelized both loops, multiple threads would be trying to update the same elements in `C` from different `k`-loop iterations. This would create a race condition, requiring locks or other synchronization mechanisms. The overhead from locking would likely negate any performance benefits and add significant complexity.
    -   *What would make it viable:* If each task wrote to a private, temporary buffer that was later combined (reduced) into the final `C` matrix. This is a valid but more complex pattern.

2.  **Task-based parallelism with continuations:**
    -   *What it would do:* For each `k0` iteration, we could launch a set of parallel tasks for the `m0` loop. We could use task continuations to handle the dependencies between the `k0` steps.
    -   *Why it loses here:* The loops in this GEMM algorithm are perfectly nested and have a regular structure. The dependency on `k0` means we cannot simply parallelize all loops. The chosen `Parallel.For` on the `m` loop is a much simpler and more direct way to exploit the available parallelism without the overhead of creating and managing a complex graph of tasks.
    -   *What would make it viable:* If the computation involved irregular dependencies or a more complex workflow, a task-graph approach might be more suitable. For simple matrix multiplication, it's overkill.

3.  **Parallelize the innermost `k` loop (dot product):**
    -   *What it would do:* The dot product calculation inside `PartialMatmul` could be parallelized using a parallel sum (reduction).
    -   *Why it loses here:* This is the finest level of granularity. The amount of work in the innermost loop is often too small to justify the overhead of parallelization. Creating parallel tasks for each dot product would be extremely inefficient. Furthermore, parallel reductions can change the order of floating-point additions, which could lead to non-deterministic results unless a careful, fixed-order reduction is implemented.
    -   *What would make it viable:* If we were working with extremely long vectors (a very large `k` dimension) and the overhead of task creation was negligible, for example on a GPU. For CPU implementation, this is generally not a good strategy.
