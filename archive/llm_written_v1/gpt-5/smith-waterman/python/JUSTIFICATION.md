Overview
We started with a classic Smith–Waterman local alignment algorithm. It fills a grid (matrix) one cell at a time. Each cell takes the best of three neighbors (diagonal, up, left) plus a score, or zero. After the grid is built, we walk back from the best cell to form the aligned strings.

Original sequential flow
Think of placing letters of the query on the rows and the reference on the columns. We fill the grid row by row. For example, with query “ACACA” and reference “AGCAC”, we compute each cell using its three neighbors. This creates a wave of values that moves across the grid.

What changed (high level)
We kept the public API the same. We added a second implementation, SmithWatermanParallel, that builds the same grid but uses vectorized “anti-diagonals.” On each anti-diagonal (cells where i + j is the same), all values are independent once the previous anti-diagonal is complete. We compute those cells together with NumPy, which runs them in parallel under the hood and uses fast low-level code.

How parallelization works
- Split: We go diagonal by diagonal. For a diagonal s, valid (i, j) pairs form a continuous band. We make arrays of those i and j.
- Work per worker: NumPy acts as the worker. It evaluates the three candidates (diag+match/mismatch, up+gap, left+gap) for every (i, j) on that diagonal at once.
- Merge in fixed order: We write results back into the matrix at the exact (i, j) positions in ascending i (this is deterministic). Then we move to the next diagonal.

ASCII sketch
Input ▶ [Chunk A][Chunk B][Chunk C]
           │        │        │
        Worker1  Worker2  Worker3
           └───► Fixed-order merge ◄───┘

Determinism
- Same split: For a given input length, each diagonal has a fixed set of cells.
- Same combine: We store results into H in ascending i for each diagonal.
- No races: All reads are from the previous diagonal; writes only touch the current diagonal. Each worker (NumPy) operates on private temporaries.

Evidence
- Correctness: test_smith_waterman.py compares sequential vs. parallel matrices and final alignments on edge/small/medium/large. It reports “Correctness+determinism passed on 11 cases.” See run_summary.txt.
- Determinism: The parallel path is run twice for each case; matrices are identical.
- Performance: On 512×512, seq≈0.24s, par≈0.10s, speedup≈2.33× on this machine. See perf.txt.

Limits & safety
- Small inputs: For max(n, m) ≤ 64 we fall back to sequential to avoid overhead.
- Resource bounds: We avoid creating extra processes; NumPy uses efficient native code. No oversubscription from our code.
- Corner cases: Empty strings and size‑1 are handled; identity percentage protects divide-by-zero.

How to reproduce
- python test_smith_waterman.py  # parity + determinism + perf
- python run_smith_waterman.py   # quick run + hash

Glossary
- Parallel — many helpers do different parts at the same time.
- Deterministic — same input gives the same output every time.
- Worker — a helper that processes one chunk of the data.
- Merge/combine — join partial answers in a fixed order.
