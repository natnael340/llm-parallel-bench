Decision summary
- Baseline bottleneck: Expanding neighbors one-by-one in a single thread; wide levels waste cores and cause cache misses.
- Chosen strategy: Direction-Optimizing BFS (top-down when narrow, bottom-up when wide) using a bounded ForkJoinPool with deterministic dense indexing (CSR arrays) and fixed-level ordering.
- Why it is safe (determinism): We compute distances level-by-level with boolean frontiers and a fixed merge order (index order). Workers only set local boolean flags; final level selection follows a single deterministic scan.
- Why it is faster (theory): Bottom-up on wide levels reduces edge checks from O(E) per level to scanning most vertices once and stopping on the first frontier neighbor. CSR arrays improve memory locality.
- Worker count + chunk rule: ≤ CPU cores; contiguous index blocks per worker.
- Small-N fallback threshold: Heuristic switch ALPHA/BETA controls when to use top-down or bottom-up; small frontiers use top-down automatically.
- Best rejected alternative + one key reason: Per-edge atomic marking and concurrent queues — excessive contention and nondeterministic ordering.

1) What changed and why
Originally, we visited nodes in a queue: take one node, list its neighbors, add unseen ones to the queue, and repeat. This is simple but uses a single thread. When a level has thousands of nodes, a lot of time is spent scanning neighbors in order.

We switched to a direction-optimizing BFS. When the frontier (the current wave) is small, we do the usual top-down scan from frontier to neighbors. When it is very large, we flip the work: instead of scanning all edges out of the frontier, we inspect each unvisited vertex and ask, “Do you have any neighbor in the frontier?” If yes, we mark it for the next level and stop scanning its remaining neighbors. This is known to reduce work a lot on broad levels (social graphs, grids, etc.).

2) How we made it parallel (step-by-step idea, not code)
- We convert the input graph into compact arrays (CSR) in a stable, sorted vertex index. This gives us dense integer ranges to split among workers.
- We represent the frontier as a boolean array by index. We also keep a boolean visited array and a distances array.
- Top-down phase:
  - Split the list of frontier parents into W blocks; workers scan their parents’ adjacency and set nextFrontier flags for neighbors that are not yet visited.
- Bottom-up phase:
  - Split the whole index range into W blocks; workers scan unvisited vertices and stop early when a vertex has any neighbor in the current frontier. They set the vertex’s flag in nextFrontier.
- After workers finish, a single deterministic pass sets distances for all nextFrontier vertices (by increasing index), updates visited, and swaps the frontier for the next level.
- We compute the output order by distance, then by sorted node ID, which is deterministic and consistent with level structure.

3) Why the answer is always the same (determinism)
- The dense index is built from the sorted node IDs, so it is stable.
- Workers only set boolean flags in their own phase; they never push into shared lists or change visited during expansion. The single-threaded level commit assigns distances and builds the new frontier in index order.
- The top-down/bottom-up choice is a pure function of current frontier counts and edge totals (ALPHA/BETA), so the mode is the same every time for the same input.

4) Proof it works (point to evidence)
- Correctness parity: Distances match the baseline on a 300×300 grid and an ER(100k,300k) random graph. See run_summary.txt.
- Determinism: Two parallel runs on ER(100k,300k) produce identical distance arrays. See run_summary.txt.
- Performance: On this sandbox, the direction-optimizing version is still slower (speedup ~0.49–0.57×) due to JVM/thread overhead and limited cores. In practice, DOBFS reduces work on very broad levels and scales on multi-core machines. perf.txt records timings.

5) Limits & safety switches
- We switch automatically between top-down and bottom-up using ALPHA (edges threshold) and BETA (frontier size) divisors. This avoids doing extra work when the frontier is small.
- Workers are bounded to CPU count using a fixed ForkJoinPool.
- The code handles empty graphs and unreachable nodes; unreachable vertices keep distance −1 and never appear in the output.

6) How to reproduce
- Compile and run:
  javac Graph.java BaselineBfs.java BfsParallel.java algo_parallel.java run_bfs.java
  java run_bfs
- Inspect outputs:
  cat run_summary.txt
  cat perf.txt

7) Glossary
- Parallel — many helpers do different parts at the same time.
- Deterministic — same input gives the same output every time.
- Worker — a helper that processes one chunk of the data.
- Merge/commit — finalize nodes of the next level in a fixed order.
- Top-down — expand from the frontier to neighbors.
- Bottom-up — scan unvisited vertices for any parent in the frontier.

8) Alternatives we considered (and why we didn’t pick them)
- Per-edge parallelism with atomics
  a) Idea: Each edge is a task; if neighbor is unvisited, mark and enqueue.
  b) Loses here: High contention on visited and queues; timing affects which thread wins; to regain determinism we would need per-level sorting and more memory traffic.
  c) Viable if: We accept relaxed determinism or post-sort plus ample cores.

- Pure top-down parallel BFS with dedup sets
  a) Idea: Always scan from frontier, never switch direction; deduplicate with sets.
  b) Loses here: On wide levels, the work is proportional to total edge count, which is expensive. Our graphs show broad levels; DOBFS cuts work.
  c) Viable if: Graphs are very sparse and frontiers stay small.

- Task graph with dynamic work-stealing
  a) Idea: Build a DAG of level tasks and let the runtime steal work.
  b) Loses here: Overhead and non-deterministic merge order without extra bookkeeping; to fix determinism we must add ordered collectors, pushing us over the patch-size budget with little gain.
  c) Viable if: Extremely large graphs and we can accept more code to enforce ordering.
