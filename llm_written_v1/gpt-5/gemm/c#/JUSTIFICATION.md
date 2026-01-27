Decision summary
- Baseline bottleneck: The inner i×j×k loops of GEMM run sequentially per M-tile; only one core computes tiles even though tiles are independent.
- Chosen strategy: Parallelize the M-tiling loop with a bounded Task Parallel Library (TPL) Parallel.For over independent M tiles, per fixed N- and K-tiles.
- Why it is safe (determinism): Each worker updates a disjoint block of rows in C, and tiles are processed in a fixed outer-loop order; no shared writes, and no reductions across workers.
- Why it is faster: Work per M-tile is large and independent; running tiles on multiple cores uses all CPUs while keeping good cache locality with the existing packing.
- Worker count + chunk rule: MaxDegreeOfParallelism = Environment.ProcessorCount; iteration range split into fixed-size M tiles (ceil(m/MB)).
- Small-N fallback threshold: If m×n×k ≤ 1,000,000, run the original sequential path to avoid parallel overhead.
- Best rejected alternative + one key reason: Parallelizing the inner k-reduction would need cross-thread reductions or atomic updates to C, risking contention and non-determinism.

1) What changed and why
The original code computes C = alpha·A·B + beta·C using 3D tiling. It transposes B, packs submatrices of A and B into contiguous blocks, and for each (n,k,m) tile it multiplies and accumulates into C. All tiles are computed on a single thread; that is the bottleneck when matrices are large.

We kept the data layout and tiling. We parallelized only along the M dimension (rows of C) because those tiles write to different rows of C. That ensures no two workers touch the same output cells.

Example: Suppose A is 128×128, B is 128×128, MB=64, NB=64, KB=64. There are 2×2×2 tiles. For a fixed (n0,k0) = (0,0), the two m-tiles [0..63] and [64..127] are independent writes to C rows 0..63 and 64..127.

2) How we made it parallel (step-by-step idea, not code)
- Split the M dimension into chunks of size MB. The number of chunks is ceil(m/MB).
- For each N tile (columns) and K tile (reduction depth), spawn a bounded Parallel.For over the M-chunks.
- Each worker packs its A submatrix once and multiplies with the shared packed B tile, then adds into its own rows in C.
- Workers write into disjoint rows of C (no overlap). Only read-only shared data is Bpack and A/B inputs.
- Combining results is trivial: there is no cross-worker merge because each worker writes final values for its rows.
- The outer loops keep a fixed order over N and K, so the overall accumulation order per cell is identical to the sequential baseline.

ASCII sketch:
Input ▶ [Chunk A0][A1][A2] per M
           │       │       │
        Worker1 Worker2 Worker3
           └───► Fixed N,K outer order ◄───┘

3) Why the answer is always the same (determinism)
- Fixed split: Given m, MB, the number and start of M-tiles is fixed. Parallel.For enumerates the same integer range every run; with bounded degree, the logical partition stays the same even if scheduling differs.
- No conflicts: Each worker only writes rows m0..m1-1; there is no shared counter or reduction across threads. Bpack is read-only.
- Fixed accumulation order inside each cell: For a given (i,j), the k-blocks are processed in increasing k0 order in the outer loops, exactly like the baseline, and within a tile we sum k in the same order. Workers do not change that order.
- Floating-point sums are thus bit-identical with the baseline, and our tests use strict equality and hash checks.

4) Proof it works (point to evidence)
- Correctness: On nine cases (edge, small, medium, large, and alpha=0 path) the parallel outputs match the sequential outputs exactly. See run_summary.txt; all lines show equal=True.
- Determinism: We run the parallel function twice per case and hash the outputs. Hashes match for each pair (deterministic=True in run_summary.txt).
- Performance: For 256×256×256 we measured seq_ms=190.09, par_ms=92.56, a 2.05× speedup on the test machine. See perf.txt. We only report perf for large-enough work (≥16M mult-adds).

5) Limits & safety switches
- Small inputs: If m×n×k ≤ 1,000,000 we use the sequential version to avoid task overhead.
- Resource bounds: MaxDegreeOfParallelism is capped at the CPU core count, avoiding oversubscription.
- Corner cases: Empty or ragged matrices are rejected like before. alpha=0 returns C unchanged (after beta scaling). k-mismatch throws. The packing respects edge tiles.

6) How to reproduce (copy-paste commands)
- Run tests and create evidence files:
  dotnet run --project .setup
- Inspect results:
  cat run_summary.txt
  cat perf.txt

7) Glossary
- Parallel — many helpers do different parts at the same time.
- Deterministic — same input gives the same output every time.
- Worker — a helper that processes one chunk of the data.
- Merge/combine — join partial answers in a fixed order.

8) Alternatives we considered (and why we didn’t pick them)
- Parallelize N-tiles and M-tiles together (2D parallel grid): Would increase parallelism but risks false sharing when two workers update adjacent rows/cols within the same cache line of C; also larger scheduling overhead and more Bpack duplication. Current patch stays within ≤250 LOC and 1 file while giving good speedup.
- Parallelize the inner j-loop with per-column reductions: This would require either locks/atomics on C or per-thread scratch buffers and then a reduction. That adds memory bandwidth pressure and risks non-deterministic reduction order. Our chosen M-tiling avoids any cross-thread reduction.
- Task graph across K (wavefront): Splitting the k-reduction across tasks requires ordered accumulation or tree reductions to keep bitwise identity; this complicates the combine phase and can exceed our bounded patch without clear gain because K-tiling already gives good cache reuse.
