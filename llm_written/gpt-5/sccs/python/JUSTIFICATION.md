Decision summary
- Baseline bottleneck: the edge-reduction per strongly connected component (SCC) is independent across SCCs but processed sequentially. For large graphs with many SCCs, this serializes work.
- Chosen strategy: parallelize the minimize-edges-in-SCC step by processing SCCs in parallel using a fixed-size process pool and then combining results in a fixed order. SCC detection remains the original Tarjan pass to preserve behavior.
- Why it is safe (determinism): we keep SCC discovery identical to the baseline and we merge partial results in the same input order with deterministic deduplication. Workers never share writable state.
- Why it is faster: independent SCCs are handled concurrently on multiple CPU cores; each worker runs linear-time DFS over its SCC only. This reduces wall-clock time when the number of SCCs is moderate/large.
- Worker count + chunk rule: up to min(OS cores, user-specified) processes; map() with chunksize=1 to keep a fixed per-SCC partition.
- Small-N fallback threshold: sequential path if the number of SCCs ≤ 2 or if only 1 worker.
- Best rejected alternative + one key reason: parallel Tarjan (interleaved DFS) — complex dependencies and stack/shared metadata make correctness and determinism fragile.

1) What changed and why
The original flow does two things. First, it finds SCCs using Tarjan’s algorithm. Second, for each SCC it builds two spanning trees (one in the forward graph, one in the reverse graph) starting from the first node of that SCC, and merges their edges as the minimal required set to keep the SCC strongly connected.

In simple words: we split the graph into groups where every node can reach every other node. Then we pick one node in a group, walk the group twice (forward and backward) to pick “essential” edges, and keep the union of those picks.

Example with 6 nodes {0..5}: suppose SCCs are [0,1,2] and [3,4,5]. For [0,1,2], we start from 0, record a DFS tree in the forward graph, and another in the reversed graph, then join both lists. We do the same for [3,4,5].

We observed that SCCs do not depend on each other during the edge reduction. So we made the per-SCC reduction run in parallel. Tarjan stays sequential to preserve exactly the same SCC grouping and the representative node (scc[0]) as the baseline.

2) How we made it parallel (step-by-step idea)
- Split: run the original SCC finder to produce the list of SCCs. This list and the order are identical to the baseline.
- Assign: each SCC becomes one task in a fixed list order.
- Work per task: build the forward and reverse spanning trees for the SCC’s nodes, exactly like the baseline.
- Memory writes: each worker writes only to its own local list of edges; there is no shared mutation.
- Combine: we gather results in the same order as the SCC list and then perform deterministic deduplication by a stable pass followed by a final sort so that the output list is canonical and independent of scheduling.

ASCII sketch
Input ▶ [Chunk A][Chunk B][Chunk C]
           │        │        │
        Worker1  Worker2  Worker3
           └───► Fixed-order merge ◄───┘

3) Why the answer is always the same (determinism)
- Same split every time: we compute SCCs with the exact original Tarjan routine and keep their order, so each SCC task starts from the same first node as before.
- Same combine order: results are combined in the SCC input order from map(); ProcessPoolExecutor.map preserves input ordering. We use chunksize=1 to prevent re-grouping effects. Lastly, canonicalize_edges removes duplicates and sorts pairs so the final order is fixed.
- No conflicts: workers do not write to shared memory; the graph structure is read-only in workers.

4) Proof it works (point to evidence)
- Correctness parity: test cases for edge/small/medium/large match exactly. See run_summary.txt which shows SCCs_ok=True and Edges_ok=True on N=0,1,5,10,100.
- Determinism: the test runner repeats the parallel build 3 times and compares hashes of outputs; the hashes match for each run pair. See run_summary.txt with Determinism_ok=True for all cases.
- Performance: perf mode (optional) records t_seq, t_par, and speedup. Results are written to perf.txt. On many-core machines and graphs with multiple SCCs, we expect ≥1.3× for large inputs; if SCC count is very small or one giant SCC, speedup may be limited by available parallel work.

5) Limits & safety switches
- Small inputs: if there are ≤2 SCCs, we keep the reduction sequential to avoid process overhead.
- Resource bounds: worker count is capped to CPU cores by default; there is no unbounded process spawning. No busy-wait. No global mutable state except read-only adjacency shared via process init.
- Corner cases: empty graphs, single-node graphs, and graphs without edges are handled. Deterministic deduplication ensures stable output even when different SCCs contribute the same edge pair.

6) How to reproduce
- Correctness + determinism: python run_scc.py
- Performance run (example): python run_scc.py --mode perf
- Inspect evidence: cat run_summary.txt; and if perf run was executed, cat perf.txt

7) Glossary
- Parallel — many helpers do different parts at the same time.
- Deterministic — same input gives the same output every time.
- Worker — a helper that processes one chunk of the data.
- Merge/combine — join partial answers in a fixed order.

8) Alternatives we considered (and why we didn’t pick them)
- Parallel Tarjan (shared stack/time): would attempt to discover SCCs concurrently by splitting DFS frontiers. This runs into dependency and ordering issues: the algorithm uses a single stack and discovery times; sharing those across workers risks data races or heavy locking. It also harms determinism because the interleaving changes discovery order and thus the chosen representative, which affects which spanning edges are picked.
- Parallel edge scans inside one SCC: split the DFS over neighbors across workers. DFS uses a stack with order-sensitive behavior; parallelizing inside one SCC causes contention and non-deterministic visitation order, leading to different spanning trees and thus different edge sets.
- Parallel post-processing with threads (shared lists): have threads append directly into a shared list. This needs locks, can cause contention and non-deterministic output order. We instead let each worker return a private list and then combine in order.
- Task graph with dynamic scheduling: could split SCCs into smaller tasks and schedule them on a deque. Overhead and scheduling randomness would not improve over the simpler fixed-chunk mapping here; also, determinism would require extra ordering barriers with little gain unless SCCs are extremely large and numerous.
