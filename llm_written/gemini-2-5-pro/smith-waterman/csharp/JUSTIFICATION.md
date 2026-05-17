### 1. What Changed and Why

The original algorithm, Smith-Waterman, finds the best local alignment between two sequences (e.g., DNA strings). It works by building a grid where each cell's value depends on its neighbors above, to the left, and diagonally. The sequential process fills this grid cell by cell, row by row, which is slow for large sequences.

Imagine making a quilt where the color of each patch depends on the three patches just above and to its left. You can't just give half the quilt to a friend to work on; you have to do it in order.

### 2. How We Made It Parallel

The key dependency is that to calculate a cell, you need the values from the previous row and column. However, cells along an "anti-diagonal" (from top-right to bottom-left) are independent of each other. This allows for a "wavefront" parallelization.

We split the work by these anti-diagonals. Each worker is assigned a set of cells on the *same* anti-diagonal to compute. Once all workers finish the current anti-diagonal, they move to the next one together. This ensures that by the time we calculate a cell, its dependencies have already been computed in previous waves.

```
      Reference Sequence →
Query   [C1] [C2] [C3] [C4]  <-- Wave 1 (C1)
  ↓     [C2] [C3] [C4] [C5]  <-- Wave 2 (C2s)
        [C3] [C4] [C5] [C6]  <-- Wave 3 (C3s)
        [C4] [C5] [C6] [C7]  <-- Wave 4 (C4s)

Workers compute all C3s at the same time, then all C4s, etc.
```

### 3. Why the Answer Is Always the Same (Determinism)

The parallel version is fully deterministic because the order of operations is strictly preserved.
- **Fixed Split:** The work is always split by anti-diagonals, which are the same for a given input.
- **Fixed Combine Order:** The algorithm proceeds from one anti-diagonal to the next in a fixed sequence (Wave 1, then Wave 2, etc.). There is no "merge" step; workers write directly to the final grid, but only to cells that other workers are not touching.
- **No Conflicts:** Workers on the same wave (anti-diagonal) compute different cells, so they never interfere with each other.

### 4. Proof It Works

The parallel implementation produces identical results to the original.
- **Correctness:** Tests on various inputs (empty, small, medium, large) confirm the outputs match the sequential version exactly. See `evidence/run_summary.txt`.
- **Determinism:** Running the parallel code twice on the same input produces the exact same alignment, score, and percentage. See `evidence/run_summary.txt`.
- **Performance:** For this algorithm, the overhead of managing the parallel tasks was greater than the benefit of parallel computation on our test machine. The parallel version was slower, with a speedup of 0.15x on a large input (see `evidence/perf.txt`). This demonstrates that while the logic is correct, not all parallel algorithms yield speedups without more complex, low-level implementation.

### 5. Limits & Safety Switches

- **Small Inputs:** For grids with fewer than 40,000 cells (e.g., 200x200), the algorithm runs the original sequential code. This avoids the high overhead of parallelization on small problems where it would be slower.
- **Resource Bounds:** The number of workers (threads) is capped at the number of available CPU cores to prevent oversubscription and inefficient task switching.
- **Edge Cases:** The code correctly handles empty or very short input strings.

### 6. How to Reproduce

To compile and run the tests, use the .NET CLI:
```bash
# Compile and run all correctness, determinism, and performance tests
dotnet run --project .
```
The test runner will print a summary of results for each case.

### 7. Glossary

- **Parallel:** Many helpers (workers) do different parts of a task at the same time.
- **Deterministic:** The same input gives the exact same output every time.
- **Worker:** A helper that processes one chunk of the data (in this case, cells on an anti-diagonal).
- **Anti-diagonal:** A line of cells in a grid running from top-right to bottom-left.
