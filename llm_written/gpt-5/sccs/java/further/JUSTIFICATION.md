Decision summary
- Baseline bottleneck: Per-SCC edge minimization (two DFS traversals) across many SCCs; also, adjacency stored as nested lists causes cache misses.
- Chosen strategy: Keep SCC discovery deterministic and sequential using iterative Kosaraju; convert adjacency into a CSR (compressed sparse row) layout once; parallelize the per-SCC minimization using a bounded worker pool; deterministically merge.
- Why it is safe (determinism): Fixed CSR order, fixed SCC order, canonical SCC root (minimum vertex) within each SCC, and a fixed merge order. No shared writes between workers.
- Why it is faster: CSR improves locality and reduces allocation. Each SCC is independent; workers do DFS over arrays. We observed up to ~2.3× speedup on a 12k/48k random graph.
- Worker count + chunk rule: min(available CPU cores, number of SCCs); one SCC per task.
- Small-N fallback threshold: V ≤ 1000 or single SCC uses the sequential path.
- Best rejected alternative + key reason: Parallel SCC (block or lock-based Tarjan) — high synchronization cost and determinism risk.

What changed and why
Originally, the graph was kept in ArrayList-of-ArrayList form and was traversed with stack/queue objects per DFS. That layout is simple but not cache-friendly: neighbors are spread across many small lists, and traversals allocate frequently. We changed two things:
1) We replaced recursive SCC discovery with an iterative Kosaraju method (two passes). It avoids stack overflows and gives stable order.
2) We added a CSR representation (two arrays: off and dst; and roff, rdst for the reversed graph). We build it lazily on first use and reuse it thereafter. CSR stores all neighbors in two flat arrays with one index array. This improves cache locality and reduces per-traversal overhead.

Once SCCs are known, we split the SCC list among workers. Each worker picks a single SCC, computes the forward and reverse spanning trees using array-based iterative DFS on CSR, and returns the union of edges. This yields good parallel speedup on graphs with many SCCs.

Example to picture it: Nodes [0..5]. Suppose SCCs are [0,1], [2,3,4], and [5]. For [2,3,4] the worker starts at the smallest node in that SCC (say 2), then walks neighbors by advancing through contiguous entries in the CSR arrays. Another worker handles [0,1]. A third worker gets [5], which produces no edges. The main thread waits for all and concatenates results in the order [0,1], then [2,3,4], then [5].

How we made it parallel
- Split: SCCs[0..k-1] are the units of work. P = min(cores, k) threads.
- Work per worker: On its SCC, mark nodes in a boolean mask and run two iterative DFS over CSR (forward and reverse), producing tree edges.
- Output writes: Each worker writes to partial[i]; no shared structures mutated.
- Combine: After all futures complete, concatenate partial[0], partial[1], …, partial[k-1].

Why the answer is always the same
- Same split for given input: the SCC order from iterative Kosaraju is fixed.
- Same root inside each SCC: we pick the minimum node as root (canonical) in both baseline and parallel.
- Same traversal policy: DFS using CSR with natural neighbor order; no randomness.
- Fixed combine order: concatenation in SCC index order.

Proof it works (evidence)
- Correctness: Differential tests compare canonicalized outputs between sequential (GraphSeq) and parallel (AlgoParallel). All edge, small, medium, and large tests PASS. See run_summary.txt.
- Determinism: For each case, we run the parallel algorithm three times; the hashes match each other and the sequential baseline.
- Performance: perf.txt shows several runs on a 12k-vertex, 48k-edge graph. We recorded speedups from 1.9× to 2.3× (best 2.31×). Actual speed depends on core count and SCC structure.

Limits & safety switches
- If there is one huge SCC, parallel work is limited (only one task). In that case we still benefit from CSR but not from threading; the small-N/low-SCC path avoids overhead.
- Worker cap equals CPU cores to avoid oversubscription.
- Corner cases covered: empty graph, size-1 graph, isolated nodes. CSR is rebuilt automatically if new edges are added.

How to reproduce
- Compile: javac GraphSeq.java AlgoParallel.java TestAlgo.java
- Run full test + perf: java TestAlgo
- Skip perf in constrained CI: java TestAlgo skipperf

Glossary
- CSR (Compressed Sparse Row) — a way to store a graph in two arrays: an index into neighbors and the neighbors themselves. Great for cache.
- Parallel — many helpers do different parts at the same time.
- Deterministic — same input gives the same output every time.
- Worker — a helper thread that processes one SCC.
- Merge/combine — append partial results in a set order.

Alternatives we considered and rejected
1) Parallel SCC discovery with union-find or lock-based Tarjan.
   - Why it loses: needs heavy synchronization (shared discovery state, stacks). Risk of non-deterministic order and subtle races. Gains are small vs. cost for our workload.
   - When viable: If we could accept non-deterministic SCC order or add expensive ordering.
2) Parallel BFS/DFS inside a single SCC.
   - Why it loses: shared visited sets cause contention or need fine-grained locks/atomics, which slow down DFS and can alter which edge becomes a tree edge (order dependence).
   - When viable: If SCCs are huge and we accept a different deterministic traversal policy with more complex work-stealing and fixed combine tree.
3) Task graph over graph partitions (advanced wavefront style).
   - Why it loses: Cross-partition edges require merge phases that are complex and may harm determinism. Overhead dominates unless graphs are massive and structured.
   - When viable: If the graph is extremely large and the cost of building CSR and SCCs is amortized, and we accept changing data layout more deeply.
4) Java parallel streams for SCC loop.
   - Why it loses: less control over worker count; potential oversubscription; harder to enforce order on combine. Fixed thread pool is safer and predictable.
