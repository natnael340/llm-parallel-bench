### 1. What Changed and Why

The original algorithm, Smith-Waterman, finds the best local alignment between two sequences (like DNA). It builds a grid where each cell's value depends on its neighbors above, to the left, and diagonally. This dependency forces a sequential, row-by-row calculation, which is slow for large sequences. Our first parallel attempt, while correct, was slower than the original due to high coordination costs for very small tasks.

This advanced version uses a more effective "block-based" or "tiled" approach. Instead of workers calculating single cells, they now calculate large square blocks (e.g., 64x64 cells) at a time. This gives each worker a meaningful chunk of work, drastically reducing the ratio of management overhead to useful computation.

### 2. How We Made It Parallel

The grid is divided into large blocks. Just like the cells, a block can only be computed once the blocks above, to the left, and diagonally to its top-left are complete. We process the grid in waves of anti-diagonals of *blocks*, not individual cells.

All blocks on a given anti-diagonal are independent and can be computed in parallel. Each worker is assigned a full block to compute. Once all workers finish their blocks in the current wave, they synchronize and move to the next wave of blocks.

```
      (Block 0,0) (Block 0,1) (Block 0,2)  <-- Wave 1: Proc(0,0)
      (Block 1,0) (Block 1,1) (Block 1,2)  <-- Wave 2: Proc(1,0), Proc(0,1)
      (Block 2,0) (Block 2,1) (Block 2,2)  <-- Wave 3: Proc(2,0), Proc(1,1), Proc(0,2)

      Input ▶ [Wave 1 Blocks] [Wave 2 Blocks] [Wave 3 Blocks]
                   │               │               │
               Worker Pool     Worker Pool     Worker Pool
```

### 3. Why the Answer Is Always the Same (Determinism)

This advanced method remains fully deterministic for the same reasons as the simpler one, just at a larger scale.
- **Fixed Split:** The grid is always partitioned into the same fixed-size blocks for a given input.
- **Fixed Combine Order:** The algorithm processes anti-diagonals of blocks in a strict, sequential order (Wave 1, then Wave 2, etc.). Workers within a wave are independent.
- **No Conflicts:** Each worker is assigned a unique block within its wave. It only reads from completed blocks from prior waves and writes only to its own assigned block's memory, ensuring no data races.

### 4. Proof It Works

This implementation is correct, deterministic, and provides a significant performance improvement.
- **Correctness:** All tests confirm that the block-based parallel version produces results identical to the sequential algorithm. See `evidence/run_summary.txt`.
- **Determinism:** Executing the parallel code twice on the same input yields the exact same alignment and score, as verified by the test harness. See `evidence/run_summary.txt`.
- **Performance:** The block-based strategy achieved a **1.95x speedup** on a large input (1500x1600 characters), reducing the runtime from 134.51 ms to 68.99 ms. This confirms the approach is effective. See `evidence/perf.txt`.

### 5. Limits & Safety Switches

- **Small Inputs:** For sequences that are too small to form at least one full block (e.g., smaller than 64x64), the algorithm automatically falls back to the proven sequential implementation. This avoids parallel overhead for tiny inputs.
- **Resource Bounds:** The number of parallel workers is capped at the system's processor count to avoid creating more threads than cores, which would be inefficient.
- **Block Size:** The block size (64x64) is a tunable parameter. This size was chosen as a balance between providing enough work per task and not creating too few tasks for effective parallelization.

### 6. How to Reproduce

To compile and run the tests from the command line, use the .NET CLI:
```bash
# Compile and run all correctness, determinism, and performance tests
dotnet run --project .
```
The test runner will execute all cases and print a final summary of the results.

### 7. Glossary

- **Parallel:** Many helpers (workers) do different parts of a task at the same time.
- **Deterministic:** The same input gives the exact same output every time.
- **Worker:** A helper that processes one chunk of the data (in this case, a 64x64 block of the grid).
- **Block/Tile:** A large, square sub-section of the main computation grid.
