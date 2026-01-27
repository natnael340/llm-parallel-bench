## JUSTIFICATION.md

### 1) What Changed and Why

The original program implements the Smith-Waterman algorithm, a method used in bioinformatics to find the best local alignment between two DNA or protein sequences. Sequentially, the process involves two main stages: first, constructing a grid (or matrix) where each cell's value is calculated based on its neighbors, and second, searching this entire grid to find the highest score, which marks the end of the best alignment.

For a simple example, imagine aligning "CAT" and "CAR". The algorithm builds a 4x4 grid. Each cell's score depends on the cells to its left, above, and diagonally up-left. This dependency, like a wave, means you can't calculate a cell until its predecessors are known, making this stage hard to parallelize. The second stage, finding the highest score, is a simple scan of every cell in the grid.

### 2) How We Made It Parallel

We focused on parallelizing the second stage—finding the highest score—as it is independent and easily divisible. The first stage of building the grid remains sequential to ensure correctness due to the data dependencies.

Here’s the parallel strategy for finding the highest score:

1.  **Split**: The grid is divided into horizontal chunks of rows. If we have 4 CPU cores and a 1000-row grid, each core gets a chunk of 250 rows to scan.
2.  **Work**: Each worker (a helper process) scans only its assigned rows to find the highest score within that local chunk.
3.  **Combine**: After all workers are done, a final step compares the highest scores found by each worker to determine the single, overall highest score for the entire grid. This merge step is done in a fixed order, ensuring the same result every time.

```
Input Grid ▶ [Chunk A (Rows 1-250)] [Chunk B (Rows 251-500)] [Chunk C (Rows 501-750)] [Chunk D (Rows 751-1000)]
                   │                      │                       │                       │
                Worker1                Worker2                 Worker3                 Worker4
                   └───► Fixed-order merge of local max scores ◄───┘
```

### 3) Why the Answer Is Always the Same (Determinism)

The parallel implementation is deterministic for two key reasons:

*   **Fixed Partitioning**: For a given grid size and number of CPU cores, the grid is always split into the exact same chunks of rows. Worker 1 always gets the first chunk, Worker 2 the second, and so on.
*   **Fixed-Order Reduction**: The process of combining the local maximum scores from each worker happens in a fixed, predetermined order. This ensures that if multiple cells have the same highest score, the one found first according to this deterministic process is consistently chosen.

Workers operate on their own chunks and only report their final local result; they do not interfere with each other, preventing conflicts.

### 4) Proof It Works

The new parallel version was rigorously tested against the original.

*   **Correctness Parity**: The parallel and sequential versions produce identical alignment results on a range of test cases, from empty strings to large, randomly generated sequences. The test summary can be found in `evidence/run_summary.txt`.
*   **Determinism**: Running the parallel code twice on the same large input produced bit-for-bit identical results, confirmed by comparing cryptographic hashes of the outputs. This is documented in `evidence/run_summary.txt`.
*   **Performance**: On a large alignment task (2000x2000 sequences), the parallel version showed a significant speedup. The performance metrics are recorded in `evidence/perf.txt`.

### 5) Limits & Safety Switches

*   **Small Inputs**: For small grids (less than 4096 cells), the program automatically uses the original sequential method. This avoids the overhead of managing parallel workers, which would be slower for small tasks.
*   **Resource Bounds**: The number of parallel workers is capped at the number of available CPU cores to prevent oversubscription and ensure efficient resource use.
*   **Corner Cases**: The implementation correctly handles edge cases like empty input strings.

### 6) How to Reproduce

To reproduce the verification results, you can run the following commands from the project root:

```bash
# Run correctness and determinism tests
go run test_runner.go algo_parallel.go

# Run performance benchmark (on a large, generated input)
go run test_runner.go algo_parallel.go perf
```

### 7) Glossary

*   **Parallel**: Many helpers (workers) do different parts of a task at the same time.
*   **Deterministic**: The same input gives the same output every single time.
*   **Worker**: A helper process that handles one chunk of the data.
*   **Merge/Combine**: The process of joining the partial answers from each worker into a final result in a fixed order.
*   **Reduction**: A type of combine step where multiple partial results are reduced to a single value (e.g., finding the single highest score from several local high scores).
