What changed and why
- Original: The code builds a score table (matrix) cell-by-cell from top-left to bottom-right. Each cell uses three neighbors (top, left, and top-left) plus a match/mismatch rule, then takes the max or 0. After the table is filled, we find the maximum score and backtrack to produce the local alignment.
- Change: We kept the public API and traceback logic the same, and parallelized only the heavy matrix fill. We use a wavefront (anti-diagonal) schedule that respects data needs. To reduce overhead and improve cache use, we compute in tiles (blocks) and use a fixed barrier between waves. For tiny inputs, we keep it sequential to avoid extra cost.

Tiny example (query=“GATTACA”, reference=“GCATGCU”)
- Sequential: fill row 1, then row 2, etc. Each new cell reads its three neighbors already set.
- Parallel idea: process all cells where i+j=2, then i+j=3, and so on. Those cells do not depend on each other.

How we made it parallel
- Split: We slice the matrix into square tiles (128×128 by default). We then step through tile anti-diagonals: all tiles on the same anti-diagonal run together.
- Work per worker: Each worker computes one tile completely (inner loops are sequential inside that tile).
- Combine: After a wave completes, we move to the next wave. The waves go in a fixed order from top-left to bottom-right.

Sketch
Input ▶ [Chunk A][Chunk B][Chunk C]
           │        │        │
        Worker1  Worker2  Worker3
           └───► Fixed-order merge ◄───┘

Why results are deterministic
- Same split: For a given size, the number of tiles and which wave each tile is on is fixed.
- Same merge: We always process waves in the same sequence. Parallel.For creates a barrier at the end of each wave, so later tiles never read half-done data.
- No conflicts: Each worker writes only inside its tile. Neighbors it reads are either from earlier waves or from inside the same tile.

Proof it works
- Correctness and determinism tests run in run_sw.cs. Results match the original for edge, small, medium, and large inputs; two parallel runs give identical hashes. See evidence/run_summary.txt.
- Performance: We include a large case. Speedup may vary by environment and JIT; we use tiling and a sequential fallback to avoid slowdowns on small inputs. See evidence/perf.txt.

Limits & safety switches
- Small inputs: If total cells ≤ 1,000,000 or only one core is available, we stay sequential.
- Resource bounds: We cap threads at Environment.ProcessorCount.
- Corner cases: Empty strings and length-1 strings are handled by the base logic.

How to reproduce
- dotnet run
- Repeat to check determinism and inspect evidence/*.txt

Glossary
- Parallel — many helpers do different parts at the same time.
- Deterministic — same input gives the same output every time.
- Worker — a helper that processes one chunk of the data.
- Merge/combine — join partial answers in a fixed order.
