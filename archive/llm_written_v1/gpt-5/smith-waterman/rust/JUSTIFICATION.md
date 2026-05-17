JUSTIFICATION

1) What changed and why
The original program builds a scoring table (matrix) for two strings. Each cell uses three neighbors (left, up, and diagonal) and a rule: match adds points, mismatch or gap subtracts, and values do not drop below zero. After the table is filled from top-left to bottom-right, it finds the highest cell and walks backward to produce the best local alignment. Example (A vs ACT): rows are A, columns ACT; we compute each cell from its neighbors, then trace back from the best cell to get the aligned letters.

We kept the public interface and traceback the same. We parallelized only the matrix fill because it dominates runtime for large inputs. Parallel work follows the “wavefront” (anti-diagonals). Cells on the same anti-diagonal do not depend on each other, so they can be computed at the same time.

Tiny example (query=ACGT, ref=ACCT): compute diagonal k=2: (1,1); k=3: (1,2),(2,1); k=4: (1,3),(2,2),(3,1); and so on. All pairs with the same k are independent.

2) How we made it parallel
- Split: For a given anti-diagonal k, we list its positions in order of increasing row i.
- Workers: We partition that list into equal chunks and start a bounded number of threads (at most CPU cores). Each worker reads the previous diagonal and writes results into its own local buffer.
- Merge: After all workers finish the current diagonal, we sort the partial results by their fixed positions and store them back into the matrix from left to right. We then move to the next diagonal.

Sketch:
Input ▶ [Chunk A][Chunk B][Chunk C]
           │        │        │
        Worker1  Worker2  Worker3
           └───► Fixed-order merge ◄───┘

3) Why the answer is always the same (determinism)
- Same split: For the same input size, we compute the same anti-diagonals and slice them at fixed chunk sizes.
- Same combine: We always merge results in increasing position order (A then B then C).
- No conflicts: Workers only read the matrix and characters; they write to private buffers. Only the final combine touches the shared matrix.

4) Proof it works (evidence)
Our tester compares sequential vs. parallel on edge, small, and larger cases, and runs the parallel path twice. All cases matched and repeated exactly. See evidence/run_summary.txt. Determinism is shown by identical matrices and alignments in both parallel runs. Performance was not a focus in this sandbox, so we kept a safety guard. See evidence/perf.txt.

5) Limits & safety switches
- Small inputs: We keep it sequential below 1,000,000 cells to avoid overhead.
- Resource bounds: Threads are capped to the number of CPU cores. No global shared state.
- Corner cases: Empty strings and size=1 are handled.

6) How to reproduce
- Build and run tests: rustc main.rs and execute binary (or cargo run with the included setup).
- Parity and determinism: Run the program; it prints per-case parity and determinism and writes evidence/run_summary.txt.
- Performance: It also writes evidence/perf.txt with basic timing.

7) Glossary
- Parallel — many helpers do parts at the same time.
- Deterministic — same input gives the same output every time.
- Worker — a helper that processes one chunk.
- Merge/combine — join partial answers in a fixed order.
