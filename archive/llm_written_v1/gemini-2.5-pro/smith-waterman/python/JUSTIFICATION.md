
### 1) What Changed and Why

The original Smith-Waterman algorithm finds the best local alignment between two sequences (e.g., DNA strands). It works in three main steps:
1.  **Build a grid (matrix):** It creates a grid where each cell `(i, j)` holds a score for the best possible alignment ending at position `i` of the first sequence and `j` of the second.
2.  **Find the highest score:** It scans the entire grid to find the cell with the highest score. This marks the end of the best local alignment.
3.  **Trace back:** Starting from the highest-scoring cell, it traces a path backward to the start of the alignment, reconstructing the aligned sequences.

The most time-consuming part for large sequences is often building the grid, but its calculation has dependencies that make it hard to parallelize simply. However, the second step—finding the highest score—is a simple search that can be done in parallel. We focused on parallelizing this search to speed up the process for large inputs.

### 2) How We Made It Parallel

We split the task of finding the highest score among multiple helpers, called "workers."

1.  **Splitting the Grid:** The grid is divided into horizontal chunks of rows. Each worker is assigned one chunk to search.
2.  **Independent Searching:** All workers search their assigned chunk at the same time. Each worker finds the highest score and its location *within its own chunk*.
3.  **Combining Results:** A main coordinator gathers the "best" score from each worker. It then compares these few scores to find the one true highest score for the entire grid.

This process is deterministic because the grid is always split the same way, and the final check is always done in a fixed order.

```
Input Grid ▶ [Chunk A][Chunk B][Chunk C][Chunk D]
                │        │        │        │
             Worker1  Worker2  Worker3  Worker4
                │        │        │        │
                ▼        ▼        ▼        ▼
             [Max A]  [Max B]  [Max C]  [Max D]
                └─────────► Fixed-order Merge ◄─────────┘
                                  │
                                  ▼
                            Final Max Score
```

### 3) Why the Answer Is Always the Same (Determinism)

The parallel version is guaranteed to produce the exact same result as the original every time:
*   **Fixed Task Splitting:** For a grid of a given size, we always split it into the same number of chunks with the same rows. Worker 1 always gets the first set of rows, Worker 2 the next, and so on.
*   **Deterministic Local Search:** Each worker's search within its small chunk is a standard, non-random process.
*   **Fixed-Order Merge:** The results from the workers are combined in a fixed sequence. This ensures that if two chunks have the same highest score, the one from the earlier chunk is chosen consistently, matching the behavior of the original top-to-bottom sequential scan.
*   **No Conflicts:** Workers only read from the grid and only report their findings. They don't modify the grid or interfere with each other, eliminating any chance of conflicts.

### 4) Proof It Works

We built a rigorous test suite to prove the parallel version is correct and deterministic.
*   **Correctness:** The output of the parallel code was compared against the original sequential code across various test cases, from empty strings to large sequences. All tests passed, confirming the results are identical. See `evidence/run_summary.txt`.
*   **Determinism:** We ran the parallel code twice on every test case and hashed the results. The hashes were identical for both runs, proving the output is repeatable. The summary file shows these matching hashes (e.g., `Hashes: 5a706b24 == 5a706b24`).
*   **Performance:** Performance tests on large sequences (1500x1400) showed that the parallel version was often slightly slower. This is because the overhead of creating processes and transferring data outweighed the benefit of parallel search for this specific problem size and hardware. The parallelization strategy is sound, but in this case, the `findHighestScore` step was not the primary bottleneck. See `evidence/perf.txt`.

### 5) Limits & Safety Switches

*   **Small Input Fallback:** For small grids (under 100 rows or 100,000 cells), the code automatically uses the original sequential method. This avoids the unnecessary overhead of parallelization for inputs where it would be slower.
*   **Resource Bounds:** The number of parallel workers is capped at the number of CPU cores available on the machine, preventing it from slowing down the system.
*   **Edge Cases:** The code correctly handles empty inputs and cases where one sequence is empty, returning a score of 0 without errors.

### 6) How to Reproduce

You can rerun all the checks using the following commands:
1.  **Run correctness and determinism tests:**
    ```bash
    python test_runner.py
    ```
2.  **Run performance tests (on large inputs):**
    ```bash
    python test_runner.py --perf
    ```

### 7) Glossary

*   **Parallel:** Many helpers do different parts of a task at the same time.
*   **Deterministic:** The same input always produces the same output.
*   **Worker:** A helper process that handles one chunk of the data.
*   **Merge/Combine:** Joining the partial answers from each worker into a final result in a fixed order.
