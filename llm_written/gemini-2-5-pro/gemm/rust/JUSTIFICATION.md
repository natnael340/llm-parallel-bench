# Parallel GEMM Justification

## 1. Decision Summary

- **Baseline bottleneck:** The sequential implementation uses three nested loops (`n`, `k`, `m` dimensions), making the computation time O(n*k*m). For large matrices, this is extremely slow.
- **Chosen strategy:** We parallelized the outermost loop over the `m` dimension (rows of the output matrix `C`) using Rayon's `par_chunks_mut`. This divides the output matrix into independent horizontal bands that can be computed concurrently.
- **Why it is safe (determinism):** Each parallel task works on a distinct, non-overlapping chunk of the output matrix `C`. There are no shared writes between threads, eliminating the possibility of data races. The order of floating-point additions is preserved within each chunk, and since chunks are independent, the final result is always the same.
- **Why it is faster:** The problem is highly data-parallel. By splitting the `m` dimension, we distribute the most computationally expensive part of the algorithm across multiple CPU cores, leading to a significant reduction in wall-clock time for large matrices.
- **Worker count + chunk rule:** Rayon's default thread pool is used, which typically matches the number of logical CPU cores. The output matrix `C` is divided into chunks of `mb` rows (where `mb` is the tile size, 64 in our tests).
- **Small-N fallback threshold:** A fallback to the sequential version is triggered if `m < mb * 2` or `n < nb * 2`. This avoids the overhead of thread management for matrices that are too small to benefit from parallelism.
- **Best rejected alternative + one key reason:** Parallelizing the `n` loop (over columns) was rejected because the current implementation iterates through `n` in the outermost `while` loop, creating a dependency that would require restructuring the entire loop order and potentially harming cache performance.

## 2. What Changed and Why

The original code calculates the product of two matrices, `A` and `B`, and stores it in a third matrix, `C`. Imagine you're filling in the cells of the output matrix `C` one by one. To calculate a single cell `C[i][j]`, you need to take row `i` from matrix `A` and column `j` from matrix `B`, multiply their corresponding elements, and sum the results.

The sequential code does this using a technique called "tiling" or "blocking." Instead of calculating `C` cell by cell, it processes small rectangular blocks (tiles) of the matrices at a time. This helps keep data in the CPU's fast cache memory. However, it still processes these blocks one after another. For a large 1024x1024 matrix, this means processing 256 blocks sequentially, which is a lot of work for a single core.

## 3. How We Made It Parallel

The key insight is that the calculation for one block of rows in the output matrix `C` is completely independent of the calculation for any other block of rows. This allows us to divide the work cleanly among multiple workers (CPU cores).

1.  **Splitting the work:** We split the output matrix `C` into horizontal bands, or "chunks." For example, if `C` has 1024 rows and our chunk size is 64, we create 16 chunks.
2.  **Assigning to workers:** Rayon, our parallelization library, assigns each of these 16 chunks to an available worker thread. Worker 1 gets rows 0-63, Worker 2 gets rows 64-127, and so on.
3.  **Independent computation:** Each worker computes the final values for its assigned rows only. It reads from matrices `A` and `B` but only writes to its own, separate portion of `C`.
4.  **Combining results:** No explicit combination step is needed. Because each worker modifies its part of the `C` matrix in place, the final matrix is already complete once the last worker finishes its task.

Here is a sketch of the process:

```
Input (Matrix C) ▶ [Chunk 0-63][Chunk 64-127][Chunk 128-191] ...
                        │             │              │
                     Worker 1      Worker 2       Worker 3
                        │             │              │
                        ▼             ▼              ▼
                   (Writes to      (Writes to      (Writes to
                    C[0-63])       C[64-127])     C[128-191])
```

## 4. Why the Answer Is Always the Same (Determinism)

Determinism is guaranteed because our parallel strategy prevents threads from interfering with each other:

-   **Fixed Task Distribution:** For a given matrix size, Rayon's `par_chunks_mut(mb)` will always divide the matrix `C` into the same number of chunks of the same size.
-   **No Shared Writes:** The most critical factor is that each worker is given an exclusive, mutable slice of `C` (`c_chunk`). Worker 1 can only write to its assigned rows, and Worker 2 can only write to its different set of assigned rows. They never try to write to the same memory location.
-   **Fixed-Order Operations:** Within each chunk, the floating-point calculations happen in the same sequential order as they did in the original code. This prevents tiny rounding differences that can occur if the order of summation changes.

Since the work is split the same way every time and there's no cross-talk between workers, the final result is identical on every run.

## 5. Proof It Works

We have verified the correctness, determinism, and performance of the parallel implementation with a comprehensive test suite.

-   **Correctness Parity:** The parallel version produces results that are numerically identical to the sequential baseline across a range of matrix sizes, from a tiny 1x1 to a large 512x512 matrix. All correctness tests passed, as shown in `run_summary.txt`.
-   **Determinism:** We ran the parallel implementation twice on the same 256x256 input matrices and confirmed that the outputs were bit-for-bit identical. The test passed, and the details are in `run_summary.txt`.
-   **Performance:** On a large 1024x1024 matrix multiplication, the parallel version achieved a **6.64x speedup** over the sequential version, utilizing 16 threads. This demonstrates a parallel efficiency of approximately 41.5%. The full results are documented in `perf.txt`.

## 6. Limits & Safety Switches

-   **Small Inputs:** For matrices with fewer than 128 rows or columns, the overhead of creating and scheduling parallel tasks can be greater than the performance benefit. The code includes a safety switch that detects these small cases and automatically runs the original sequential `gemm_sequential` function instead.
-   **Resource Bounds:** The implementation uses Rayon's default thread pool, which automatically scales to the number of available CPU cores on the machine. This prevents the program from creating too many threads and overloading the system.

## 7. How to Reproduce

To reproduce these results, you will need a Rust environment with Cargo installed.

1.  **Compile and run all tests:**
    ```bash
    # Ensure you have the necessary dependencies, e.g., by creating a Cargo.toml
    # with `rayon` listed.
    cargo run --release --bin gemm_parallel
    ```
2.  **Verify correctness and determinism results:**
    ```bash
    cat run_summary.txt
    ```
3.  **Verify performance results:**
    ```bash
    cat perf.txt
    ```

## 8. Alternatives We Considered

-   **Parallelize the `n` loop (columns):**
    -   *What it would do:* Instead of giving each worker a band of rows, we would give them a band of columns to compute.
    -   *Why it loses here:* The existing code structure has a `while n0 < n` loop as the outermost loop. Parallelizing this directly is awkward and would require significant refactoring. More importantly, writing to columns is often less cache-friendly than writing to contiguous rows, which could lead to worse performance due to "cache line ping-ponging."
    -   *What would make it viable:* If the data layout were column-major (SoA instead of AoS), this could be a very effective strategy.

-   **Parallelize the `k` loop (inner reduction):**
    -   *What it would do:* For each output cell `C[i][j]`, the summation `s += a[i][k] * b[k][j]` would be parallelized.
    -   *Why it loses here:* This is a parallel reduction. It introduces significant overhead because each summation is very small. The cost of creating tasks would far outweigh the benefit. Furthermore, ensuring deterministic floating-point summation would require a fixed-order reduction, adding even more complexity and overhead for minimal gain.
    -   *What would make it viable:* This is almost never a good strategy for matrix multiplication unless the `k` dimension is extraordinarily large and the `m` and `n` dimensions are very small.

-   **Task-based parallelism with recursion (e.g., fork-join):**
    -   *What it would do:* Recursively split matrices A, B, and C into quadrants and compute the sub-problems in parallel.
    -   *Why it loses here:* While this is a classic and effective algorithm, it is more complex to implement correctly than simple data parallelism on one dimension. It would require more significant refactoring of the existing tiled implementation. Given that parallelizing the `m` loop provides excellent speedup and is simple to implement and verify, the added complexity was not justified.
    -   *What would make it viable:* For extremely large, non-square matrices, a recursive approach can offer better load balancing. If our simple chunking strategy resulted in poor performance due to imbalanced work, this would be the next best alternative.
