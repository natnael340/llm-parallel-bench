What changed and why
- Original process: The sequential code fills a 2D score grid H for the two strings. Each cell uses three neighbors (up, left, diagonal) and a max-with-zero rule. After the grid is done, it scans for the highest score and traces back to produce the best local alignment.
- Example (tiny): Query=“GATT”, Ref=“GCT”. We build H row by row; each position checks match/mismatch and gap penalties, picks the best, or 0. The best path then gives a short aligned pair like “GAT” vs “GCT”.
- Change: We kept the public API and traceback logic but replaced the matrix constructor with a parallel, deterministic wavefront implementation. We also kept a sequential fallback for very small inputs to avoid overhead.

How we made it parallel
- Split: The grid has anti-diagonals (cells with i+j equal). Within one anti-diagonal, cells are independent once the previous anti-diagonal is complete.
- Workers: We create a fixed-size pool capped to CPU cores. Each worker takes a striped subset of positions on every anti-diagonal (e.g., worker 0 does indices 0, W, 2W, … on that diagonal).
- Combine: There is a barrier at the end of each anti-diagonal. Only when all workers finish diagonal d do we move to d+1. We always traverse diagonals in increasing order and keep the same worker count, so the split does not change.

Why the answer is always the same
- Same split: For given input sizes and core count, the number of diagonals and the stripe pattern are fixed. No randomness is used.
- Same combine order: We enforce a barrier per diagonal, so all cells of diagonal d are done before any cell of d+1. Each worker only writes its own cells; there is no shared write conflict.
- Integers only: No floating-point reductions, so no rounding drift. Traceback reads the finished grid, which is identical to the sequential one.

Proof it works
- Correctness parity and determinism are exercised in run_smithwaterman.java. It compares full matrices and alignment outputs on edge/small/medium inputs and runs the parallel traceback twice to confirm the same hash. See evidence/run_summary.txt.
- Performance: The harness can optionally run a larger test via --perf N M and writes evidence/perf.txt. On tiny inputs or CI, we skip perf to avoid noise.

Limits & safety
- Small inputs: We keep it sequential when (n−1)*(m−1) ≤ 50,000 cells to avoid thread overhead.
- Resources: Worker count is capped to available CPU cores; no unbounded goroutines. Barrier ensures no races.
- Edge cases handled: empty strings, length-1 cases, and skewed shapes.

Reproduce
- Compile & run tests: javac SmithWatermanSeq.java AlgoParallel.java run_smithwaterman.java && java run_smithwaterman
- Determinism check (twice): java run_smithwaterman; then inspect evidence/run_summary.txt for matching hashes.
- Optional perf: java run_smithwaterman --perf 3000 3000; inspect evidence/perf.txt.

Glossary
- Parallel — many helpers do different parts at the same time.
- Deterministic — same input gives the same output every time.
- Worker — a helper that processes one chunk of the data.
- Merge/combine — join partial answers in a fixed order.

ASCII sketch
Input ▶ [Chunk A][Chunk B][Chunk C]
           │        │        │
        Worker1  Worker2  Worker3
           └───► Fixed-order merge ◄───┘
