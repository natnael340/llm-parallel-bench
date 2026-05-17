# JUSTIFICATION.md

## 1. What Changed and Why

The original Smith-Waterman algorithm identifies the most similar regions between two strings (e.g., DNA sequences). It works by building a grid where each cell's value depends on its top, left, and top-left neighbors. This creates a dependency, as you can't calculate a cell until its neighbors are known. The sequential code calculated this grid cell-by-cell, row-by-row, which is slow for large strings.

For example, to align "CAT" and "CAR", it builds a 4x4 grid. The score for the 'T' vs 'R' comparison depends on the scores for 'T' vs 'A', 'A' vs 'R', and 'A' vs 'A'.

## 2. How We Made It Parallel

The key insight is that cells on the same anti-diagonal (from top-right to bottom-left) do not depend on each other. All cells on an anti-diagonal can be calculated simultaneously once the previous anti-diagonal is complete.

Our parallel strategy processes the grid in waves:

1.  **Split by Anti-Diagonal**: The work is divided into anti-diagonals of the grid.
2.  **Parallel Calculation**: Multiple worker threads calculate the scores for all cells on the current anti-diagonal at the same time. Each worker handles a subset of cells on that line.
3.  **Synchronization**: A barrier ensures all workers finish the current anti-diagonal before any worker moves to the next one, preserving the data dependency.
4.  **Combine Results**: The final grid is assembled as each wave completes. The subsequent steps of finding the highest score and traceback are also parallelized. The highest score search is parallelized by dividing the grid into chunks and having each thread find a local maximum, followed by a deterministic reduction to find the global maximum.

```
      Reference ->
Query [Wave 1] [Wave 2] [Wave 3] ...
  |      │        │        │
  ▼   Worker1  Worker1  Worker1
      Worker2  Worker2  Worker2
      Worker3  Worker3  Worker3
         └───► Barrier Sync ◄───┘
```

## 3. Why the Answer Is Always the Same (Determinism)

Determinism is guaranteed through several mechanisms:

*   **Fixed Calculation Order**: The anti-diagonal approach provides a fixed, predictable order for calculations, ensuring the scoring grid is always identical for the same inputs.
*   **Deterministic Tie-Breaking**: When finding the highest score in the grid, if multiple cells have the same top score, we deterministically choose the one with the smallest row index, and then the smallest column index.
*   **Deterministic Traceback**: During the final alignment construction (traceback), if multiple paths from a cell are possible, we enforce a strict priority: `Diagonal > Up > Left`. This ensures the same alignment is produced every time.
*   **Static Scheduling**: OpenMP's `schedule(static)` directive is used in loops to ensure that the same data is assigned to the same thread for a given input size, removing variability from thread scheduling.

## 4. Proof It Works

The solution was rigorously tested against the original sequential implementation.

*   **Correctness**: The parallel version produces bit-identical outputs to the sequential version across a range of test cases, from empty strings to sequences 1000 characters long. The test harness compares hashes of the results to confirm this. See `evidence/run_summary.txt`.
*   **Determinism**: Running the parallel code twice on the same input produces the exact same result hash, confirming its deterministic nature. See `evidence/run_summary.txt`.
*   **Performance**: For large inputs (1000x1000 strings), the parallel version shows a significant speedup. See `evidence/perf.txt` for detailed timings.

## 5. Limits & Safety Switches

*   **Small Input Fallback**: For strings shorter than 250 characters, the algorithm switches back to the sequential implementation. This avoids the overhead of thread management, which would make the parallel version slower on small inputs.
*   **Resource Bounds**: The number of threads is managed by OpenMP and is typically capped at the number of available CPU cores to prevent oversubscription and inefficient processing.

## 6. How to Reproduce

To compile and run the tests, use the following commands:

```bash
# Compile the test harness
g++ -O3 -fopenmp test_harness.cpp smith_waterman_sequential.cpp algo_parallel.cpp -o test_harness

# Run the tests
./test_harness

# Inspect the evidence
cat evidence/run_summary.txt
cat evidence/perf.txt
```

## 7. Glossary

*   **Parallel**: Doing multiple parts of a task at the same time.
*   **Deterministic**: Giving the same output for the same input, every single time.
*   **Worker**: A helper (CPU thread) that processes one chunk of data.
*   **Anti-Diagonal**: A line of cells in the grid running from top-right to bottom-left.
*   **Traceback**: The process of reconstructing the final alignment by tracing a path back through the scoring grid.
