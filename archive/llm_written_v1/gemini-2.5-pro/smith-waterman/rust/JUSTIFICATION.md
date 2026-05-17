# Smith-Waterman Sequence Alignment Parallelization

## Decision Summary

- **Baseline bottleneck**: The core bottleneck is the `construct_matrix` function, an O(N*M) operation with loop-carried dependencies, making simple parallelization impossible.
- **Chosen strategy**: A wavefront (or anti-diagonal) parallelization for the matrix construction and a parallel reduction for finding the highest score.
- **Why it is safe (determinism)**: The wavefront approach processes the matrix in fixed-order anti-diagonals, ensuring every cell's dependencies are met before it's calculated. The parallel search for the maximum score uses a deterministic reduction, always selecting the first-encountered maximum in case of ties.
- **Why it is faster**: For large matrices, calculating all cells in an anti-diagonal simultaneously utilizes multiple cores, significantly reducing the wall-clock time for the O(N*M) construction phase. The parallel max-score search is also faster on large matrices.
- **Worker count + chunk rule**: The implementation uses Rayon's default thread pool, which is capped at the number of logical CPU cores to prevent oversubscription. Work is dynamically stolen by available threads.
- **Small-N fallback threshold**: A fallback to the sequential implementation is triggered if either the query or reference length is less than 20 characters (`n < 20 || m < 20`). This avoids parallel overhead on inputs too small to benefit.
- **Best rejected alternative + one key reason**: **Blocked Matrix Decomposition**. This strategy involves dividing the matrix into blocks and processing them in a dependency-aware order. It was rejected because the wavefront approach is a more natural fit for this specific dependency structure and can be implemented more cleanly within the bounded patch constraints, whereas blocking requires more complex state management.

## 1. What Changed and Why

The original Smith-Waterman algorithm is a powerful tool for finding the best local alignment between two sequences (like DNA or protein strings). Its most time-consuming part is building a scoring matrix.

Imagine you have two words, "CAT" and "CAR". The algorithm creates a grid. To figure out the score at any cell in the grid, you need to know the scores of the cells immediately above, to the left, and diagonally up-left. This creates a dependency chain: you must fill the top-left of the grid before you can fill the bottom-right. The original code did this one cell at a time, row by row, which is slow for large sequences.

The goal was to speed up the grid-building part by using multiple "helpers" (CPU cores) at once, without changing the final answer.

## 2. How We Made It Parallel

The key was to change the order of operations from row-by-row to anti-diagonal-by-anti-diagonal. An anti-diagonal is a line of cells from top-right to bottom-left.

The crucial insight is that **all cells on the same anti-diagonal are independent of each other**. Their dependencies are all on cells in previous anti-diagonals, which have already been computed. This allows us to safely calculate all the cells on a single anti-diagonal at the same time.

Here’s the step-by-step process:
1.  **Flatten the Grid**: Instead of a grid (a list of lists), we represent the matrix as a single, long list of numbers. This is more efficient for memory access.
2.  **Split the Work**: The main thread iterates through the anti-diagonals one by one. For each anti-diagonal, it assigns the task of calculating the scores for the cells on that line to a pool of worker threads managed by the Rayon library.
3.  **Independent Calculation**: Each worker calculates the score for its assigned cell. It only needs to read the already-completed scores from the previous two anti-diagonals. Since no worker writes to a location another worker is reading from or writing to, there are no conflicts.
4.  **Synchronization**: The workers automatically synchronize after each anti-diagonal is complete before moving to the next one. This ensures the dependency order is always respected.
5.  **Parallel Search**: Once the matrix is built, finding the highest score is also done in parallel. Each worker searches a chunk of the matrix, and a final deterministic reduction step finds the overall maximum.

```
Sequential (row-by-row):
[1] → [2] → [3]
 ↓     ↓     ↓
[4] → [5] → [6]
 ↓     ↓     ↓
[7] → [8] → [9]

Parallel (anti-diagonal):
[1]
 ↓
[2] [4]  (Workers 1 & 2 run in parallel)
   ↘↙
[3] [5] [7] (Workers 1, 2, 3 run in parallel)
   ↘↙ ↘↙
[6] [8]
   ↘↙
[9]
```

## 3. Why the Answer Is Always the Same (Determinism)

The parallel version gives the exact same result every time for several reasons:

-   **Fixed Calculation Order**: The anti-diagonals are always processed in the same order (from top-left to bottom-right). Within an anti-diagonal, the calculations can happen in any order, but this doesn't matter because they are independent. The final value of a cell `(i, j)` is always based on the same, fully computed values of `(i-1, j)`, `(i, j-1)`, and `(i-1, j-1)`.
-   **No Data Races**: The most complex part of the implementation involves using `unsafe` Rust code to allow multiple threads to write to the shared matrix. This is proven safe because the wavefront algorithm guarantees that no two threads can ever access the same memory location at the same time in a conflicting way. We are essentially telling the compiler, "We have enforced the safety rules manually through our algorithm's logic."
-   **Deterministic Reduction**: When searching for the highest score, if multiple cells have the same maximum score, the parallel reduction is designed to be deterministic. It will always pick the one found first according to the original data order, preventing variability between runs.

## 4. Proof It Works

The solution was rigorously tested against the original sequential version to ensure correctness and determinism.

-   **Correctness Parity**: The parallel implementation's output was compared against the sequential baseline across 10 test cases, from empty strings to large sequences. All tests passed, confirming the results are identical. See `run_summary.txt` for the pass/fail log.
-   **Determinism**: For each test case, the parallel version was run twice, and the outputs were hashed. The hashes were identical for every run, proving the output is deterministic. For example, for the "Large" case, both runs produced a result with hash `11049450632170736596`. See `run_summary.txt` for details.
-   **Performance**: Performance was measured on a large input (400x400 matrix) using an optimized release build. The parallel version demonstrated a significant speedup. See `perf.txt` for the exact numbers.

## 5. Limits & Safety Switches

-   **Small Input Fallback**: For sequences shorter than 20 characters, the algorithm falls back to the original sequential version. This is a performance optimization to avoid the overhead of thread management, which would make the parallel version slower on small inputs.
-   **Resource Bounds**: The number of threads is managed by the Rayon library, which defaults to the number of logical cores on the machine. This prevents the program from creating too many threads and slowing down the system.
-   **Memory Usage**: The algorithm uses a flattened 1D vector to store the scoring matrix, which requires `O(N*M)` memory. This is the same as the sequential version and is the theoretical minimum for this algorithm.

## 6. How to Reproduce

To reproduce the verification results, you will need Rust and Cargo installed.

1.  **Compile and Run Tests (Optimized Release Mode)**:
    ```bash
    cargo run --release
    ```
2.  **Verify Correctness & Determinism**:
    -   Inspect `run_summary.txt`. It should show `PASS` for all correctness and determinism checks.
    -   To manually check determinism, run the command twice and confirm the hashes in the output are identical.

3.  **Verify Performance**:
    -   Inspect `perf.txt`. It will contain the sequential time, parallel time, speedup factor, and core count for the large test case.

## 7. Glossary

-   **Parallel** — Doing multiple independent parts of a big task at the same time.
-   **Deterministic** — The same input always produces the exact same output.
-   **Worker** — A helper (a CPU thread) that processes one chunk of the data.
-   **Wavefront / Anti-diagonal** — A pattern for processing a grid where all cells on a diagonal line are computed simultaneously.
-   **Data Race** — A bug where multiple workers try to read and write to the same memory location without coordination, leading to unpredictable results.

## 8. Alternatives We Considered

-   **Blocked Matrix Decomposition**:
    -   *What it would do*: This strategy divides the matrix into smaller square blocks. A block can only be computed once the blocks to its left, above, and diagonally-up-left are complete.
    -   *Why it loses here*: While effective, this adds significant complexity to the logic. You need a system to manage the dependency graph of the blocks. The wavefront approach is a simpler, more direct application of parallelism that perfectly fits the data dependency pattern of Smith-Waterman and was easier to implement correctly within the project's bounded patch constraints.
    -   *What would make it viable*: If the matrix were too large to fit in cache, a cache-aware blocking strategy could potentially outperform the wavefront by improving data locality.

-   **Row-by-Row Parallelism with Synchronization**:
    -   *What it would do*: Attempt to parallelize the inner loop (columns) for each row.
    -   *Why it loses here*: This is fundamentally incorrect due to the data dependency `h[i][j]` depends on `h[i][j-1]`. To make it work would require fine-grained locking or synchronization on every single cell, the overhead of which would make the solution orders of magnitude slower than the sequential version.

-   **Using a Global Mutex Lock**:
    -   *What it would do*: Keep the parallel wavefront structure but have each worker lock a mutex around the entire matrix before writing its result.
    -   *Why it loses here*: This was attempted during early refinement. A global lock completely eliminates all parallelism, as only one worker can hold the lock and write to the matrix at a time. This serialization makes the performance far worse than the sequential version due to the constant lock contention and overhead. This approach is functionally correct but defeats the purpose of parallelization.
    -   *What would make it viable*: Never. This strategy is an anti-pattern for this kind of fine-grained computation.