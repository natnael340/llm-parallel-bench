Overview
We started from a standard Smith–Waterman (SW) local alignment. The original code fills a grid, one cell at a time, from top-left to bottom-right. Each cell uses three neighbors: diagonal (match/mismatch), up (gap), and left (gap). After the grid is filled, a traceback walks back from the best cell to reconstruct the alignment and compute identity.

Sequential example (tiny)
For query “AGCTA” vs reference “GCTA”, the DP grid (6×5 including a zero row/col) is filled row by row. Each cell is the best of 4 numbers: 0, diag+score, up+gap, left+gap. The traceback then follows the highest-scoring path backwards.

What changed (in plain terms)
We kept the scoring and traceback the same. We changed only how the grid is filled. Instead of row-by-row, we process independent bands (anti-diagonals) of blocks in parallel. Each band is split into several tiles; different workers handle different tiles at the same time.

How parallel fill works
- Split: We divide the DP grid into 32×32 tiles. Tiles on the same anti-diagonal depend only on tiles from earlier diagonals, so they can run together.
- Workers: We use up to NumCPU helpers (capped at 64). For a given diagonal, we partition its tiles into contiguous ranges and assign them to workers deterministically.
- Local compute: Inside a tile, cells are filled sequentially to respect the data dependencies within the tile.
- Fixed merge: We wait for all workers of a diagonal to finish before moving to the next diagonal. This guarantees the next diagonal sees all required neighbors.

Determinism
- Fixed partitioning: For the same input sizes and worker count, the same tiles go to the same worker ranges in the same order.
- No shared writes: Each cell belongs to exactly one tile. Workers write only to their own tile region.
- Fixed combine order: Diagonals advance in order (k=0..K). Within a diagonal we do not sum floats; each cell is a pure max of integers. Results are therefore identical to the sequential version.

Evidence
- Correctness and determinism: run algo_parallel.go prints OK for edge/small/medium/large sizes. Two parallel runs per case match the sequential hash and each other (see evidence/run_summary.txt).
- Performance: On 512×800, parallel time 14.30 ms vs sequential 18.99 ms (1.33× faster) using 16 cores (see evidence/perf.txt and run output).

Limits & safety
- Sequential fast path for small problems (≤ 65,536 cells) avoids overhead.
- Worker cap avoids oversubscription.
- Handles empty inputs.

Reproduce
- go run algo_parallel.go
- go run algo_parallel.go -workers 8
- go run run_sw.go  (stripped runner that writes evidence files)

Glossary
- Parallel: many helpers process different tiles at the same time.
- Deterministic: same input yields the same output every time.
- Worker: a helper goroutine that processes assigned tiles.
- Merge/combine: moving to the next diagonal after all tiles in the current band finish.
