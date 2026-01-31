Decision summary
- Baseline bottleneck: single-threaded blocked GEMM loops over tiles; all work done serially across M×N tiles and K blocks.
- Chosen strategy: data-parallel over independent M-row tiles with fixed partitioning; each worker owns disjoint rows of C and accumulates locally before a deterministic merge.
- Why it is safe (determinism): fixed chunking and a fixed merge order by row index; no shared writes between threads; floating-point additions happen in the same K-block grouping for a tile, so each tile’s accumulation uses a fixed order.
- Why it is faster: large row tiles expose coarse-grain parallel work; threads reuse packed A/B sub-blocks and perform most time in compute; zero locks and no contention.
- Worker count + chunk rule: min(available_cpu_cores, ceil(m/mb)); static bands of consecutive M-tiles per worker.
- Small-N fallback threshold: total_ops ≤ 64×64×32 runs sequentially in the exact baseline order to avoid overhead.
- Best rejected alternative + one key reason: parallelizing the inner K-reduction with atomics/locks — would change reduction order (non-deterministic floating sums) or introduce heavy contention.

What changed and why
The original code multiplies two matrices in blocks. Think of A as M rows by K columns and B as K by N. It walks tiles by N, then by K, then by M. For each (M,N) tile, it packs a small A block and a B block, multiplies them, and adds into C. This is correct but uses only one core.

Our change is to let several helpers (threads) handle different sets of rows of C. Each helper copies its own rows of C into a private buffer, then repeats the same tiled loops (N then K) on only its rows. It never touches other rows. After all helpers finish, we put the rows back into the right places, in order. This keeps the math and the tile order per row the same and avoids races.

Tiny example: A is 6×4 and B is 4×5; mb=2, nb=3, kb=2. The baseline visits N tiles [0..3), [3..5), K blocks [0..2), [2..4), and M tiles [0..2), [2..4), [4..6). We split M tiles across two workers. Worker 1 gets rows 0..4, worker 2 gets 4..6. Each worker packs the same A and B slices as the baseline would for its rows and adds results into its own copy of C. Then we merge rows back by index 0..5.

How we made it parallel (step-by-step idea)
- Split input by M tiles: compute how many mb-sized tiles fit across M. Assign consecutive tiles to workers in bands. The number of workers is bounded by CPU cores.
- Each worker:
  - Copies only its assigned rows from the initial C (after beta scaling) into a private buffer.
  - Loops over N tiles then K blocks, packs the same A and B slices, and accumulates into a small temporary tile buffer, then adds this into its own C rows.
- No shared writes: workers write only to their own row copies.
- Merge: after all threads finish, we gather returned (row_index, row_data) pairs and sort by row index to write them into the global C in increasing order. Sorting ensures a fixed, deterministic merge order.

ASCII sketch
Input ▶ [Chunk A][Chunk B][Chunk C]
           │        │        │
        Worker1  Worker2  Worker3
           └───► Fixed-order merge ◄───┘

Why the answer is always the same (determinism)
- Same split: for a given M and mb, the number of M-tiles is fixed. We cap the thread count at min(cores, tiles) and assign contiguous bands; this mapping is the same every run.
- Same combine order: rows are merged back sorted by their index, which is a total order that does not depend on timing.
- Stable accumulation: within each worker, K-blocks are visited in order and summed into a temporary tile, then added into that worker’s rows. That mirrors the baseline grouping by K inside each (M,N) tile. Because each row is handled by exactly one worker, there are no cross-thread adds on the same cell.

Proof it works (point to evidence)
- Correctness: test cases from 1×1 up to 64×64×64 pass exact equality (bit-equal). See run_summary.txt for all cases; each line shows sizes and a pass.
- Determinism: every case runs the parallel version three times. Hashes match and we do a full element-by-element compare; det=true in all cases. Evidence is printed and logged.
- Performance: on a 256×256×256 case, the measured speedup is about 3.5× on the test machine (see perf.txt). This is consistent with using several CPU cores and low contention.

Limits & safety switches
- Small inputs: when total_ops ≤ 64×64×32, work is done sequentially to avoid thread overhead. This also guarantees zero startup cost for tiny matrices.
- Resource bounds: worker count never exceeds the number of hardware threads nor the number of M-tiles. We do not spawn unbounded goroutines/threads.
- Corner cases: empty matrices and ragged rows are rejected, as in the baseline. Cases with alpha=0 return the initial C after optional beta scaling, per baseline rules.

How to reproduce
- Build and run the tests and perf check:
  cargo run
- Rerun determinism check for a given size (example 128):
  RUSTFLAGS="" cargo run --release
  # The program already repeats the parallel run and hashes outputs.
- View results saved by the program:
  cat run_summary.txt
  cat perf.txt

Glossary
- Parallel — many helpers do different parts at the same time.
- Deterministic — same input gives the same output every time.
- Worker — a helper that processes one chunk of the data.
- Merge/combine — join partial answers in a fixed order.

Alternatives we considered (and why we didn’t pick them)
1) Parallelize the inner K reduction for each C cell across threads.
   - What: multiple threads compute partial sums over different K ranges and add to the same C cell.
   - Why it loses: needs atomic adds or locks (contention), or a reduction tree that changes floating-point order, risking non-determinism across runs. It also creates many tiny tasks.
   - Would be viable if: we accepted a tolerance (not bit-equal) and had a large SIMD-friendly reduction tree with strict scheduling.

2) Parallelize by N tiles as well, with shared C writes and locks.
   - What: assign (M,N) tiles to workers that all write into a shared C.
   - Why it loses: tiles overlap on C when K is looped, forcing synchronization or atomicity; avoiding overlap requires complex ownership protocols. Determinism is fragile.
   - Would be viable if: C were partitioned into disjoint stripes by design (e.g., block-row layout in memory) so ownership was trivial.

3) Use a dynamic work-stealing pool (Rayon) over all tiles.
   - What: spawn a task per tile with a pool that balances load.
   - Why it loses: work-stealing makes the execution order input- and timing-dependent, so floating-point addition order can vary, risking non-determinism. Also more overhead for small tiles.
   - Would be viable if: we relaxed determinism and targeted throughput only, or reworked accumulation to use pairwise fixed-order reductions per tile.

4) Task graph over K with barrier per block (wavefront-like).
   - What: for each K block, compute contributions to all tiles in parallel, then barrier, then next K.
   - Why it loses: still needs consistent assignment to C rows to avoid races, and barriers add costs. Benefits over simple row-band partitioning are limited here.
   - Would be viable if: A and B were huge and memory reuse across K-blocks dominated, making global barriers acceptable while keeping ownership of C disjoint.
