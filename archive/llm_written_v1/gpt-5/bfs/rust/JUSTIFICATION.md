Decision summary
- Baseline bottleneck: Breadth-First Search (BFS) scans the neighbors of each frontier vertex one by one; all work of a level is processed on one thread.
- Chosen strategy: Level-synchronous parallel BFS with fixed chunking of the frontier and fixed-order merge.
- Why it is safe (determinism): Each level’s frontier is split into deterministic chunks, each worker writes only to its own buffer, and we merge in chunk index order while guarding against duplicates.
- Why it is faster: Many neighbor lists are scanned in parallel; no locks on the hot-path except per-chunk output. Work scales with the number of CPU cores.
- Worker count + chunk rule: Workers = min(available cores, current frontier size). The frontier is divided into contiguous chunks with sizes differing by at most 1.
- Small-N fallback threshold: For frontiers ≤ 64 or 1 core, we run sequentially.
- Best rejected alternative + one key reason: Parallel queue with shared visited set — needs fine-grained locking or atomics per vertex; contention would dominate and determinism would be hard.

1) What changed and why
The original process takes one starting node and explores the graph layer by layer. It uses a queue: take one node, add it to the answer, then for each of its neighbors, if we haven’t seen it before, push it to the queue. This is repeated until the queue is empty. The result order matches the moment nodes are first visited.

In plain words: we explore in waves. First the start node, then all its neighbors, then all their unvisited neighbors, and so on. For a small picture with 6 nodes where 0 connects to 1,2; 1 connects to 3; 2 connects to 4; and 4 connects to 5, the order is: 0, 1, 2, 3, 4, 5.

We changed the code to process each wave (one BFS level) using several workers at once. Each worker gets a slice of the frontier (the nodes to expand next). Workers scan neighbors independently and write possible next nodes into a private buffer. After all workers finish, we combine these buffers in a fixed order and remove duplicates. Then we move on to the next wave. For tiny waves we keep the old sequential path to avoid overhead.

2) How we made it parallel (step-by-step idea, not code)
- Split: At each level, take the current frontier list and cut it into K contiguous chunks, where K is the number of workers (bounded by core count and frontier length).
- Work per worker: For every node in its chunk, a worker reads the node’s neighbor list and collects new candidates not yet seen in this level. It uses a small local set to avoid repeats inside its chunk.
- Write destination: Each worker writes to its own private vector. No other worker touches it.
- Combine: After all workers finish, we merge vectors in chunk index order: chunk 0, then 1, then 2, … While merging, we check a shared visited set and append to the global result and the next frontier only if the node is still new.

ASCII sketch:
Input ▶ [Chunk A][Chunk B][Chunk C]
           │        │        │
        Worker1  Worker2  Worker3
           └───► Fixed-order merge ◄───┘

3) Why the answer is always the same (determinism)
- Same split: For a given input and core count, the chunk sizes are computed the same way every time (contiguous slices, sizes differ by at most 1). We also include a sequential fallback for very small frontiers to fully match the baseline path.
- Same combine order: We merge the partial vectors in index order (0,1,2,…). If a node is found by several chunks, the first chunk wins because we check a single visited set when merging. This gives a single, predictable order for all nodes of a level.
- No conflicts: Workers never write to shared state while scanning. They write only to their local vector; we use a per-chunk mutex just to place the vector into a slot safely, not on every output push. The global visited and result vectors are touched only during the single-threaded merge step.

4) Proof it works (point to evidence)
- Correctness parity: Our test suite compares the original sequential run and the new parallel run on 13 cases: empty, start-missing, single edge, a chain, a star, multiple random small graphs, and three random medium graphs. All passed. See run_summary.txt.
- Determinism: For each case, we run parallel twice and check it equals itself and the sequential output. We also print a hash of the output for quick checks; the hashes are in run_summary.txt.
- Performance: On a synthetic graph with 20,000 nodes and 4 extra edges per node, using 16 cores, the speedup was 2.275× in an unoptimized build (see perf.txt). Optimized builds are expected to improve further.

5) Limits & safety switches
- Small inputs: When the frontier size is ≤ 64 or only one core is available, we run the sequential path to avoid overhead. This threshold can be tuned.
- Resource bounds: We cap workers by core count and the frontier length. We avoid oversubscription by using Rust’s standard threads and a per-level scope; no busy spin, no unbounded goroutines.
- Corner cases: Empty graph and missing start node return an empty list. Isolated nodes and skewed degrees work because each level recomputes the frontier and we always guard with the visited set.

6) How to reproduce (copy-paste commands)
- Run tests and determinism checks:
  cargo run > out.txt 2>&1; tail -n +1 run_summary.txt out.txt
- Check performance run numbers:
  cat perf.txt
- Repeat determinism for a single large case (hash compare of two runs):
  cargo run > run1.txt; cargo run > run2.txt; diff run1.txt run2.txt || true

7) Glossary
- Parallel — many helpers do different parts at the same time.
- Deterministic — same input gives the same output every time.
- Worker — a helper that processes one chunk of the data.
- Merge/combine — join partial answers in a fixed order.

8) Alternatives we considered (and why we didn’t pick them)
1) Global concurrent queue with shared visited set
   a) Threads pop vertices and push neighbors into a shared work queue; a shared visited set prevents repeats.
   b) Loses here due to contention: many atomic operations or locks on the queue and the visited set. Order would depend on scheduling, breaking determinism unless we add a heavy ordering layer. It would also require changing several structures (queue, visited) and exceed our bounded patch for a clean deterministic design.
   c) Might be viable if we accept non-deterministic order, or if we move to a lock-free, per-bucket visited with hashing and accept tolerance on order.

2) Two-phase bitmap visited with atomics and prefix-sum compaction
   a) Each thread marks a global bitmap for discovered nodes; then we do a parallel prefix-sum to compact frontier nodes in order.
   b) Loses here because it needs a different graph index layout (dense 0..N-1 ids) and a larger refactor (data layout change) beyond our small bounded patch. Also, it adds complexity to keep the exact original order when duplicate discoveries happen.
   c) Would be viable if the graph used dense integer ids with a fixed upper bound and we were allowed a structural refactor.

3) Wavefront with per-level sorting to restore order
   a) Expand in parallel and then sort the next frontier to a canonical order.
   b) Sorting adds O(F log F) overhead per level and changes the order if the baseline depends on adjacency list order. Here we kept true BFS-with-adjacency-order semantics; sorting would not match.
   c) Would be viable if the baseline did not promise neighbor-order stability or if we accept a different canonical order.
