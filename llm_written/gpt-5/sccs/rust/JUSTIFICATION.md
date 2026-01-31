Decision summary
- Baseline bottleneck: processing each strongly connected component (SCC) one after another when building minimal edge sets; work per SCC is independent.
- Chosen strategy: keep SCC detection sequential (Tarjan’s DFS), then parallelize edge minimization across SCCs using Rayon with fixed ordering.
- Why it is safe (determinism): SCC list is computed once; per-SCC work writes to private buffers; final concatenation keeps the original SCC order.
- Why it is faster: large graphs often have many SCCs; work inside each SCC can be done in parallel without conflicts; Rayon uses all cores with low overhead.
- Worker count + chunk rule: Rayon’s global pool, bounded to logical CPU count; we use par_iter, which partitions the SCC slice deterministically.
- Small-N fallback threshold: if V ≤ 1024 or E ≤ 5,000 or SCCs ≤ 2, run sequential to avoid overhead.
- Best rejected alternative + one key reason: parallel Tarjan/Kosaraju – cross-vertex dependencies and stack order make determinism and correctness hard without heavy refactor.

1) What changed and why
Originally, the program does three things in order: find SCCs (groups of nodes where each can reach each other), then for each group make two spanning trees (one in the forward graph and one in the reverse graph), then collect the edges from both trees. The code did this for each group one-by-one. That last phase is embarrassingly parallel: each group does not depend on others. We exploited that.

Small example. Suppose we have 6 nodes. The SCCs are [0,1,2] and [3,4,5]. We start a DFS from the first node in each group. For [0,1,2] we collect edges that connect them in a tree; we do the same in the reverse graph. For [3,4,5] we do the same. In the end we join edges from the first group and then the second. That order should not change when we parallelize.

2) How we made it parallel (step-by-step idea, not code)
- Split: we first build the full list of SCCs, exactly as before.
- Assign: we iterate over the list of SCCs with a parallel iterator. Each worker gets a chunk of SCCs, always in the same order.
- Work per worker: for each SCC, the worker builds a forward and reverse spanning tree and returns a vector of edges.
- Writes: workers only write to their private vectors. No shared writes happen during the parallel loop.
- Combine: we collect all per-SCC vectors into a vector-of-vectors, then concatenate them from left to right. This fixed order matches the baseline.

ASCII sketch
Input ▶ [SCC A][SCC B][SCC C]
           │        │        │
        Worker1  Worker2  Worker3
           └───► Fixed-order merge ◄───┘

3) Why the answer is always the same (determinism)
- Same split: given the same graph, Tarjan’s algorithm visits nodes in index order and produces the same SCC list. We do not parallelize that stage.
- Same combine order: we keep the SCC list order. Rayon’s par_iter over a slice plus collect preserves index order when we collect into a Vec.
- No shared state conflicts: each worker uses only local data structures and reads the immutable graph. We then append results in a single-threaded pass.
- No floating point math is involved, so there is no reduction order sensitivity.

4) Proof it works (point to evidence)
- Correctness parity: run_algo.rs builds graphs and compares outputs of the sequential and parallel versions across five sizes, including edge cases (0,1).
- Determinism: the runner computes a simple hash of outputs across three parallel runs; the hashes match exactly.
- Performance: for a large case, the runner prints sequential time, parallel time, and speedup. See perf.txt if produced; otherwise check the console log.

5) Limits & safety switches
- Small inputs: we keep it sequential when vertices ≤ 1024 or edges ≤ 5,000 or there are only up to 2 SCCs; the overhead of threads would dominate.
- Resource bounds: we use Rayon’s default pool, which caps threads to CPU cores. No busy loops or unbounded tasks are created.
- Corner cases: empty graph and single-node graphs are handled; minimize_edges_in_scc early-returns for empty SCCs; DFS start uses scc[0].

6) How to reproduce (commands)
- Build and run tests: cargo run --release
- Run only the runner binary (same): cargo run --release
- Inspect performance for large N: use the printed t_seq, t_par, and speedup near the end of output.

7) Glossary
- Parallel — many helpers do different parts at the same time.
- Deterministic — same input gives the same output every time.
- Worker — a helper that processes one chunk of the data.
- Merge/combine — join partial answers in a fixed order.

8) Alternatives we considered (and why we didn’t pick them)
- Parallel Tarjan / lock-free SCC discovery. Idea: run DFS from many vertices and try to label components concurrently. Why it loses: DFS needs a shared stack/labels with strong ordering; races hurt determinism and correctness. Would need a very different algorithm (e.g., forward-backward or coloring) and major refactor.
- Parallelize inside one SCC (node-level parallelism). Idea: split the DFS tree growth among threads. Why it loses: DFS is inherently sequential due to the stack order; coordinating visits needs locks or atomics, which adds contention and can change traversal order.
- Two-phase Kosaraju with parallel first/second passes. Idea: topological finish times and reverse graph traversal in parallel. Why it loses: the finishing-time order must be fixed; parallel walks complicate that and risk non-deterministic SCC ordering. Also higher memory traffic.
- Task-graph runtime across edges. Idea: create a task per node/edge. Why it loses: too many tasks (O(V+E)) create high scheduling overhead and memory pressure; benefits only if we completely change data layout and use work-stealing with careful determinism controls.
