Decision summary
- Baseline bottleneck: The loop that expands neighbors from the current BFS frontier; it visits many edges one by one and enqueues neighbors in a single thread.
- Chosen strategy: Level‑synchronous BFS with parallel neighbor expansion; each level’s frontier is partitioned into fixed chunks processed by a bounded worker pool.
- Why it is safe (determinism): We split the frontier by index in a fixed way and concatenate partial results in chunk-index order, then perform a stable first-unique pass. With a fixed input, the split and the merge order are the same every run.
- Why it is faster: Work over many vertices/edges at a level is independent; doing it on multiple cores reduces wall-clock time. We avoid locks and shared writes; each worker writes to its own buffer.
- Worker count + chunk rule: workers = min(ProcessorCount, frontier.Count). Chunk size = ceil(frontier.Count / workers). Each worker handles a contiguous index range.
- Small-N fallback threshold: If graph has < 512 vertices or the frontier < 1024, use the sequential path to avoid overhead.
- Best rejected alternative + one key reason: Global concurrent visited + lock-free queue; loses determinism and adds contention on shared structures.

1) What changed and why
The original BFS starts from a node, visits it, and then walks outwards, level by level. It keeps a queue and a set of visited nodes. For each node pulled from the queue, it adds its unvisited neighbors to the queue. This is simple but uses one core, even when a level has thousands of nodes.

We kept the same behavior but changed how we process each level. Instead of one thread doing all neighbor checks, we split the current level (the frontier) into slices. Each slice is handled by a worker that looks at its nodes’ neighbors and collects candidates privately. This targets the main bottleneck: expanding neighbors.

For example, imagine nodes [0,1,2,3,4,5] in the frontier. Workers might process [0,1], [2,3], and [4,5] in parallel. Each builds its own list of candidate next nodes. We then join these lists in order (chunk 0, chunk 1, chunk 2) and keep only the first time we see each node to form the next frontier.

2) How we made it parallel (step-by-step idea, not code)
- Split input: Take the current frontier list and divide it into contiguous chunks based on how many workers we will use.
- Per-worker work: For each node in its chunk, the worker reads the adjacency list and copies neighbors that are not yet visited into its private list.
- Private outputs: Workers do not share outputs. They only read the global visited set during this phase.
- Fixed merge: After all workers finish, we concatenate their lists in chunk order, then run a stable first-unique pass to remove duplicates while preserving the first appearance order. This becomes the next frontier.

ASCII sketch:
Input ▶ [Chunk A][Chunk B][Chunk C]
           │        │        │
        Worker1  Worker2  Worker3
           └───► Fixed-order merge ◄───┘

3) Why the answer is always the same (determinism)
- Same split: For a given input size, we fix the number of workers to min(cores, frontier length) and use contiguous ranges. That split is identical across runs.
- Same combine: We always concatenate chunk outputs by increasing chunk index and then do a stable first-unique pass. If the same neighbor appears from multiple chunks, the one that appears first in the merge order is kept. That order is fixed.
- No conflicts: During expansion, workers do not write shared state. Only after the merge do we touch global state (forming the next frontier), and we do it on a single thread.

4) Proof it works (point to evidence)
- Correctness parity: In run_summary.txt, all cases (empty graph, single node, a 10-node line, a 64×64 grid, and an 8k-node random graph) report seq==par: True.
- Determinism: The same parallel BFS run twice yields identical hashes on every case. Example from run_summary.txt: grid64x64 hash1=3E88…, hash2=3E88…; rand8k hash1=6B1C…, hash2=6B1C….
- Performance: On rand8k, perf.txt shows seq_ms=14, par_ms=7, speedup=2.00 on this machine. On the grid case, sizes are small and the runtime is dominated by overhead (speedup ~1.00). This matches expectations.

5) Limits & safety switches
- Small inputs: We keep processing sequential if the graph has < 512 vertices, and we also use a sequential path if the frontier is < 1024 at a level. This avoids paying thread/task overhead when there is not enough work.
- Resource bounds: We limit workers to the number of cores (ProcessorCount) and never spawn more tasks than needed.
- Corner cases: Empty graph, start not present, single vertex graphs all work and are covered by tests. The algorithm also handles duplicate edges; the stable unique pass removes repeated neighbors cleanly.

6) How to reproduce (copy-paste commands)
- Run differential tests and write reports:
  dotnet run
- Re-run to check determinism manually (hashes should match the first run):
  dotnet run
- View results:
  cat run_summary.txt
  cat perf.txt

7) Glossary
- Parallel — many helpers do different parts at the same time.
- Deterministic — same input gives the same output every time.
- Worker — a helper that processes one chunk of the data.
- Merge/combine — join partial answers in a fixed order.

8) Alternatives we considered (and why we didn’t pick them)
1) Global concurrent visited + lock-free queue
   a) Each thread dequeues and enqueues neighbors into a shared queue while marking visited in a shared concurrent set.
   b) Loses determinism: enqueue order varies with timing, so output order can change. High contention on queue and set would also cost performance.
   c) Viable if we accept non-deterministic order or redefine output to be a set, not an ordered list.

2) Parallel for over edges with atomic visited writes
   a) Flatten adjacency to an edge list and process edges in parallel, marking discovered nodes atomically.
   b) Breaks BFS level semantics without careful staging; also requires a major data layout change (>250 LOC or touching Graph.cs), violating patch bounds.
   c) Viable if we could change data layout and add a separate level array and fixed-order reductions.

3) Task-graph (wavefront) with fine-grained tasks per vertex
   a) Create a task per vertex expansion and let a scheduler run them respecting levels.
   b) Overhead dominates for medium N due to thousands of tiny tasks; harder to guarantee fixed order without extra buffers; risk of false sharing.
   c) Viable if levels are very large and we batch tasks or if a custom scheduler with deterministic queues is allowed.
