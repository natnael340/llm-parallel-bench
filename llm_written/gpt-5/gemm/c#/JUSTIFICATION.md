Decision summary
- Baseline bottleneck: The inner matrix multiply runs serially per tile; only one CPU core computes many independent row tiles.
- Chosen strategy: Keep the original tiled order over N and K, and parallelize the independent M-tiles (row blocks) inside each fixed (N, K) tile.
- Why it is safe (determinism): Each worker writes to a disjoint stripe of rows in C, and we keep the N and K loops strictly serial, so the reduction order over K is fixed.
- Why it is faster: Many M-tiles are independent and heavy; running them on multiple cores hides compute costs while avoiding contention.
- Worker count + chunk rule: Max workers = min(request, CPU cores); static partitioning by equal-size M tiles (MB rows per tile).
- Small-N fallback threshold: If m·n·k ≤ 1,000,000 FLOPs, we run the sequential baseline to avoid parallel overheads.
- Best rejected alternative + one key reason: Parallelizing K-tiles and reducing into C would need reductions/locks and would break deterministic summation order.

What changed and why
The original process computes C = α·A·B + β·C using three nested tiled loops. It first scales C by β (if provided). It then transposes B once to speed up access. Next, it walks the result by column tiles (N) and inner dimension tiles (K). For each (N, K) tile it packs the needed parts of A and B into small buffers and calls a kernel that accumulates into a submatrix of C. In plain words: we slice the big problem into rectangles and add up partial products.

Example. Suppose A is 6×5 and B is 5×4 with MB=2, NB=2, KB=3. We take a 2-column band of B, then the first 3 columns (K) inside it, and multiply it with two rows of A at a time, adding the result into the right place of C. We repeat this for the next two rows, and so on, then move to the next K band and finally to the next set of output columns.

How we made it parallel
- We split the work across the M dimension (rows of C). For a fixed (N, K) tile pair, we create a list of starting row indices m0 = 0, MB, 2·MB, …
- Each worker picks one m-tile (MB consecutive rows). It packs its own small A slice and reuses the read-only packed B slice. It runs the same kernel as before for its rows and the current columns.
- Each worker writes to its own private rows in C. No two workers touch the same C[i, j], because their row ranges do not overlap.
- We combine results in a fixed order by keeping the outer loops over N and K serial, so partial sums over K add to C in the same deterministic order as the baseline.

ASCII sketch
Input ▶ [Chunk A][Chunk B][Chunk C]
           │        │        │
        Worker1  Worker2  Worker3
           └───► Fixed-order merge ◄───┘
Here, "merge" is simply the fact that we walk N then K in order and write into non-overlapping C rows in each step.

Why the answer is always the same (determinism)
- Same split every time: For given m, MB, we create the same sequence of row tiles. The number of workers is capped and fixed by settings and core count.
- Same combine order: We do not reorder the outer N and K loops. That means each C cell sees contributions from K-tiles in the same order as before.
- No conflicts: Workers only write to their own rows in C during a step. Bpack is read-only. Apack is private per worker. No atomics or locks are needed.
- No floating-point drift: There is no parallel reduction across K; summation order matches the baseline exactly.

Proof it works (point to evidence)
- Correctness parity: All edge, small, medium, and large tests report parity=True. See run_summary.txt.
- Determinism: We repeated the parallel run 3 times per case. All hashes match within a case; see run_summary.txt for the hashes (e.g., 256×256×256 hash=1908815398242490889).
- Performance: On a 384×384×384 case we measured seq=334.6 ms, par=124.5 ms, a 2.69× speedup using up to 64 logical cores. See perf.txt. Results are a single-run smoke check and will vary by machine.

Limits & safety switches
- Small inputs: When m·n·k ≤ 1,000,000 FLOPs, we use the sequential path. This avoids overhead from thread scheduling and packing.
- Resource bounds: We cap parallelism at Environment.ProcessorCount, and you can also set a smaller limit via the maxDegree parameter.
- Corner cases: Empty or ragged matrices are rejected. We handle non-multiples of tile sizes by clipping at the edges. alpha=0 returns C immediately. beta scaling is applied exactly once.

How to reproduce
- Parity + determinism: dotnet run
- Performance: dotnet run | grep "PERF"
- Change worker cap: edit the call site to pass maxDegree (e.g., Gemm.Run(A,B,maxDegree:8)).

Glossary
- Parallel — many helpers do different parts at the same time.
- Deterministic — same input gives the same output every time.
- Worker — a helper that processes one chunk of the data.
- Merge/combine — join partial answers in a fixed order.

Alternatives we considered
1) Parallelizing the K dimension (reductions)
   a) Idea: Let many workers compute products over different K slices for the same output tile, then sum the partial results into C.
   b) Why it loses: It needs a reduction (either locks or extra buffers plus a reduction pass). That risks race conditions or a different floating-point order, breaking determinism. It also adds memory traffic for temporary tiles.
   c) When viable: If we accepted non-deterministic sums or extra work to implement a fixed binary-tree reduction per tile.

2) Per-row Parallel.For inside the kernel
   a) Idea: Run one task per row of the m-tile, each traversing all columns.
   b) Why it loses: Too fine-grained; overhead of tasks dominates, and cache locality is worse due to many small tasks.
   c) When viable: If rows are huge and MB is also very large so each task is heavy enough.

3) PLINQ/parallel LINQ over tiles
   a) Idea: Use higher-level data parallel queries to map tiles and aggregate results.
   b) Why it loses: Scheduling and ordering are not as explicit; determinism is fragile, and overhead is higher than a bounded Parallel.For.
   c) When viable: If ease of composition is more important than strong control over ordering and resources.

4) Task-graph across (N, M) tiles with dependency edges on K
   a) Idea: Create tasks per (m0, n0, k0) block and enforce K-order dependencies. Could overlap different (n0) columns more.
   b) Why it loses: Heavy coordination and many small tasks; overhead and memory pressure likely outweigh gains for this data layout, and determinism needs strict graph constraints.
   c) When viable: If we restructured to larger tiles and batched k-slices to cut task count.
