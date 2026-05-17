Decision summary
- Baseline bottleneck: all work for each M-block is done serially even though different row blocks write to disjoint rows of C.
- Chosen strategy: fixed thread-pool, data-parallel execution over M-tiles for each (N-tile, K-tile) with pack-and-compute per tile.
- Why it is safe (determinism): each task writes to a unique row range in C; K-tiles and N-tiles are processed in a single fixed outer-loop order; we synchronize after each (N,K) tile. No reductions across threads.
- Why it is faster: row tiles are independent and CPU-bound; a bounded worker pool exploits multiple cores while preserving cache locality of packed tiles. For N≥512 we measured ~1.43× speedup.
- Worker count + chunk rule: workers = min(available CPU cores, number of M-tiles); chunk = one M-tile per task per (N,K) tile.
- Small-N fallback threshold: use sequential path if m·n·k < 1e6 or workers < 2.
- Best rejected alternative + one key reason: parallelizing both M and N tiles at once (2D) would contend on C and need locks or atomics for overlapping updates across K-tiles, risking nondeterminism and overhead.

1) What changed and why
The original method multiplies A (m×k) by B (k×n) using three nested tile loops: over N (columns), K (inner dimension), and M (rows). For each N-tile and K-tile, it packs the corresponding slabs of B and A, then computes a partial product into C. This is repeated over K so that C accumulates contributions.

We noticed that, within a fixed N- and K-tile, each M-tile updates a different set of rows in C. Those writes do not overlap. That is a good unit to split across threads safely. By keeping the order of N and K loops exactly the same and only parallelizing the inner M-tiling, we avoid races and keep the math identical to the sequential code.

2) How we made it parallel (step-by-step idea, not code)
- We keep the public API the same. We also preserved the original algorithm as runSequential for testing.
- For each N-tile and K-tile we build a list of M-tile tasks. Each task:
  - Packs its own A submatrix rows for that K range.
  - Multiplies its A-pack with the pre-packed B slab for this (N,K) tile.
  - Writes results to its exclusive row range in C.
- We submit those tasks to a fixed-size thread pool and wait for all to finish before moving to the next tile. This barrier preserves the exact accumulation order across K.

ASCII sketch
Input ▶ [Chunk A][Chunk B][Chunk C]
           │        │        │
        Worker1  Worker2  Worker3
           └───► Fixed-order merge ◄───┘
Here, each chunk is a distinct M-tile (a row block). The merge is implicit because workers write to non-overlapping slices of C; the outer loops advance in a fixed order.

3) Why the answer is always the same (determinism)
- Same split: for a given (m,n,k,MB), the number of M-tiles is fixed, and we cap the worker count deterministically to min(cores, M-tiles).
- Same combine order: the N and K tiles iterate in the same order as the baseline, and we wait for all M-tile tasks of a tile to complete before advancing. No cross-thread reductions occur.
- No conflicts: each task only writes to C rows [m0..m1) and columns [n0..n1) for its tile. No two tasks touch the same cell, so no races or locks.
- Floating-point stability: since we keep the same accumulation order over K and N as the baseline, we get bit-for-bit identical results. Our determinism check hashes the entire C matrix twice and matches.

4) Proof it works (point to evidence)
- Correctness parity: Edge (1×1), small (8×5×7), medium (64×64), and large (512×512) all pass equality vs the sequential baseline. See run_summary.txt.
- Determinism: Two parallel runs on the same large input produced the same SHA-256 hash: 3919829652005c07e7ed039e86a4cd6ffd04e866b4149cc344f142d8e24fc4f2 (see run_summary.txt).
- Performance: On N=512 on this machine, sequential 246.37 ms, parallel 171.83 ms, giving 1.43× speedup with a fixed worker pool. See perf.txt.

5) Limits & safety switches
- Small inputs: Below about 1e6 scalar ops or when there is only one M-tile, we run sequential. Parallel overhead would outweigh gains.
- Resource bounds: We cap threads at the core count and the number of M-tiles. We reuse a fixed pool per run and wait at each tile to avoid oversubscription.
- Corner cases: Empty or ragged matrices are rejected (validateMatrix). If alpha is 0 we return C early. If C is provided with beta≠1, it is scaled first. We handle last partial tiles with Math.min.

6) How to reproduce (copy-paste commands)
- Compile: javac Gemm.java RunGemm.java
- Run tests: java RunGemm
- Inspect outputs: cat run_summary.txt; cat perf.txt

7) Glossary
- Parallel — many helpers do different parts at the same time.
- Deterministic — same input gives the same output every time.
- Worker — a helper that processes one chunk of the data.
- Merge/combine — join partial answers in a fixed order.

8) Alternatives we considered (and why we didn’t pick them)
- 2D tiling tasks over both M and N at once:
  a) Split both rows and columns and schedule a grid of tile tasks.
  b) Loses here because for a fixed K-tiling we would then need either atomic adds or extra buffers to avoid overlapping writes when summing over K tiles, which hurts determinism and adds memory traffic. Locks/atomics on doubles also serialize, harming speed.
  c) Would be viable if we restructured to accumulate into private per-task C tiles and added a fixed-order reduction step, but that exceeds the patch budget and memory limits for large N.
- Parallelizing the K-loop (inner dimension) with shared C updates:
  a) Give each worker a slice of K and let them update the same C cells.
  b) Loses here due to write contention and nondeterministic floating-point summation order unless we introduce per-cell reductions or compensation, which is heavy and slow in Java arrays.
  c) Would be viable if we used per-thread private C buffers followed by a fixed-order sum; again more code and memory than our bounds.
- ForkJoin across all tiles with work-stealing:
  a) Express each M-tile as a task in a global deque and let work-stealing schedule them.
  b) Loses here because work-stealing reorders execution; while results stay correct (non-overlapping writes), the reuse of B-pack across M-tasks per (N,K) tile would degrade locality and introduce nondeterministic timing that complicates perf. We preferred invokeAll per tile to preserve locality and order.

Patch bounds
- Files touched: 2 (Gemm.java, RunGemm.java)
- Public API preserved; added runSequential for baseline.
- Implementation delta within Tier 1 (<250 LOC changed).