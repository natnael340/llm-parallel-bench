Decision summary
- Baseline bottleneck: Single-threaded tiled GEMM multiplies tiles in sequence; all m×n tiles are computed one-by-one.
- Chosen strategy: 2D tiling over output C with a fixed thread pool. Each task owns one C tile (an m-block × n-block) and iterates k-tiles in order.
- Why it is safe (determinism): Tiles are disjoint in C so there are no shared writes. For a given input, partitioning and combine order are fixed; k-accumulation within a tile is in a fixed loop order.
- Why it is faster: Many tiles are independent; running them on multiple cores uses available CPU parallelism. B tiles are pre-packed and shared read-only across tasks to reduce packing work.
- Worker count + chunk rule: Workers = available CPU cores; 1 task per (MB,NB) tile. K is processed in strictly increasing blocks per task.
- Small-N fallback threshold: Sequential path if m·n·k ≤ 500,000 to avoid thread overhead.
- Best rejected alternative + reason: Parallelize inner loops with atomic adds — loses due to heavy contention and non-deterministic reduction order.

1) What changed and why
The original code computes C = α·A·B + β·C using a cache-friendly, tiled approach. It loops over N tiles, then K tiles, then M tiles. For every (m-block, n-block, k-block), it packs parts of A and B and accumulates partial products into C. All work runs on one thread, so even if many tiles are independent, only one can be processed at a time.

We parallelized the outer 2D grid of output tiles. Think of C as a grid of rectangles. Each rectangle can be computed without touching any other rectangle, provided we handle its internal k-accumulation locally. That means many rectangles can be computed at once. We also moved B-packing outside the per-tile tasks so the cost of preparing B chunks is shared.

As a tiny example, if A is 6×6 and B is 6×6 with MB=NB=KB=3, then C has 4 tiles: rows[0–3),[3–6) and cols[0–3),[3–6). Two different workers can compute the top-left and top-right tiles at the same time.

2) How we made it parallel
- Split input: We set MB, NB, KB tile sizes. The number of tile rows is ceil(m/MB); the number of tile cols is ceil(n/NB). Each (tileRow, tileCol) defines one C tile.
- Worker task: A task owns one C tile [m0:m1) × [n0:n1). It performs a loop over k-blocks from 0 to k in steps of KB. For each k-block, it packs the needed A rows and reuses a pre-packed B block, computes partial products, and accumulates into its private C tile region.
- Where writes go: Tasks write only to their own region of C. No two tasks write to the same C cell, so there is no conflict.
- Combine order: For a given tile, partial results over k are combined in increasing k order inside that same task. Across tiles, no combine is required (tiles are disjoint), so global order does not matter. Task creation order is fixed to ensure a stable work partition.

ASCII sketch
Input ▶ [Chunk A][Chunk B][Chunk C]
           │        │        │
        Worker1  Worker2  Worker3
           └───► Fixed-order merge ◄───┘
Here, the “merge” means: inside each worker, k-blocks are added in order.

3) Why the answer is always the same (determinism)
- Fixed split: For a given m, n, k, MB, NB, KB, we compute the same number of tiles and submit them in the same order. The pool size is fixed to the CPU core count, but task boundaries are identical every run.
- Fixed combine order: Within a tile, we always process k-blocks in increasing order. That sets the floating-point summation order and removes run-to-run variation.
- No conflicts: Each worker writes only to its own tile in C. There are no atomics or locks on C’s elements. B-packed blocks are read-only. A packing is per-task local.

4) Proof it works (point to evidence)
- Correctness: test runner RunGemm.java compares outputs of the original GemmBaseline and the new parallel algo on several sizes. All “parity” checks pass (see run_summary.txt).
- Determinism: The runner executes the parallel kernel three times on the same inputs and hashes the result. Hashes match every time for each case (see run_summary.txt, the hex hashes per case).
- Performance: On a 512×512×512 case, we measured seq_ms=174 and par_ms=31 for ≈5.61× speedup using all available cores (perf.txt). Smaller sizes show neutral or worse results when thread overhead dominates; the small-N fallback avoids this cost.

5) Limits & safety switches
- Small inputs use the sequential baseline if m·n·k ≤ 500,000. This keeps overhead low where parallelism does not pay off.
- Resource bounds: We cap the thread count at the number of CPU cores (no oversubscription) via a fixed thread pool. Each task is compute-bound and independent.
- Corner cases: Empty or ragged matrices are rejected just like the baseline. beta is applied once up-front; if alpha is 0 we return early, matching the baseline.

6) How to reproduce
- Compile and run tests:
  javac GemmBaseline.java algo_parallel.java RunGemm.java
  java RunGemm > run_summary.txt
- Check performance numbers (already included):
  cat perf.txt  # created by the run
If you want to re-run perf explicitly:
  java RunGemm | tail -n 1 > perf.txt

7) Glossary
- Parallel — many helpers do different parts at the same time.
- Deterministic — same input gives the same output every time.
- Worker — a helper that processes one chunk of the data.
- Merge/combine — join partial answers in a fixed order.

8) Alternatives we considered (and why we didn’t pick them)
- Parallelizing inner loops (i/j) with atomics:
  a) Idea: Multiple threads update the same C elements using atomic additions or locks.
  b) Why it loses: Heavy contention on C cells, non-deterministic reduction order for floating point, and poor scalability.
  c) Viable if: We accept looser numerical tolerance and have hardware atomics with low contention (rare for dense GEMM).
- Parallelizing only the K-reduction across threads:
  a) Idea: Split k into chunks, have threads compute partial sums and then reduce into C.
  b) Why it loses: Needs extra buffers or locks for each C tile; final reduction order must be fixed to be deterministic, which adds overhead and memory.
  c) Viable if: Memory for per-thread tile buffers is abundant and we can afford a fixed tree reduction.
- Work-stealing ForkJoin with fine tiles:
  a) Idea: Create many tiny tasks for better load balance; let a ForkJoinPool steal work.
  b) Why it loses: Stealing makes run-to-run task order vary; floating-point reduction order inside tiles can vary with steals, risking non-determinism and more scheduling overhead.
  c) Viable if: Determinism is not a requirement and inputs are extremely imbalanced.
- Vectorization-only approach (no threads):
  a) Idea: Rewrite to use BLAS/ND4J and rely on vector units.
  b) Why it loses: We must supply a parallel implementation within this codebase without external libs; also, vendor BLAS may spawn threads unpredictably.
  c) Viable if: External dependencies and non-deterministic threading are acceptable.
