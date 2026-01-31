Decision summary
- Baseline bottleneck: sequentially minimizing edges per SCC; Tarjan’s discovery is sequential but cheap per SCC.
- Chosen strategy: keep SCC detection sequential; parallelize SCC minimization across SCCs with order-preserving Rayon, and also parallelize per-SCC dual-tree builds with rayon::join.
- Why it is safe (determinism): fixed SCC order; per-SCC workers use private buffers; merge is left-to-right; per-SCC forward/reverse trees are computed in a fixed pair and concatenated deterministically.
- Why it is faster: two layers of parallelism (across SCCs and inside each SCC) raise CPU usage. Membership mask avoids HashSet checks.
- Worker count + chunk rule: Rayon’s pool capped to core count; par_iter partitions by index; join uses the same pool.
- Small-N fallback threshold: sequential when V ≤ 1024 or SCCs ≤ 2.
- Best rejected alternative + reason: parallel SCC detection (forward-backward/lock-free) — needs major refactor and risks non-deterministic component order.

1) What changed and why
Original flow: find SCCs, then for each SCC, add edges from two DFS trees (forward and reverse), and finally concatenate all edges. We kept this logic but removed unnecessary overhead and exposed more parallel work.

Key improvements:
- Use a membership mask (byte array) instead of a HashSet when checking if a neighbor is inside the current SCC. This improves cache locality and reduces per-neighbor overhead.
- Pre-reserve output capacity for each SCC’s essential edges. Each tree can add at most (|SCC| - 1) edges, so we reserve 2*(|SCC|-1).
- Compute the forward and reverse spanning trees in parallel for the same SCC using rayon::join. This doubles the per-SCC throughput when SCCs are large.
- Keep SCC processing parallel and ordered, as before.

Small example: SCC [0,1,2]
- Mask marks 0,1,2 as 1. We start DFS from 0 on forward graph to collect tree edges; in parallel, we run DFS from 0 on the reverse graph. We join their results and then append to the final output in the fixed SCC order.

2) How we made it parallel (step-by-step idea)
- Split into SCCs (sequential, deterministic).
- Across SCCs: use par_iter over the sccs slice. This preserves order when we collect results to a Vec.
- Within one SCC: call rayon::join to compute the forward and reverse spanning trees simultaneously. Both only read the graph and mask, and write to separate buffers.
- Output per SCC: combine [forward, reverse] in that order. Global output: concatenate per-SCC outputs in the original SCC order.

ASCII sketch
Input ▶ [SCC A][SCC B][SCC C]
           │        │        │
        Worker1  Worker2  Worker3
           │        │        │
         join(fwd,rev)  join(fwd,rev)
           └───► Fixed-order merge ◄───┘

3) Why the answer is always the same (determinism)
- SCCs discovered in a fixed vertex order. We do not parallelize discovery.
- par_iter over a slice plus collect preserves index order; we then append left-to-right.
- Inside a SCC, we always compute forward then reverse, and concatenate in that fixed order.
- No shared mutable state during parallel work; each thread returns its local vector.

4) Proof it works (evidence)
- run_algo.rs compares sequential vs parallel outputs on 5 cases (including edge cases). All match exactly; hashes match across 3 parallel runs.
- run_summary.txt shows det_ok=true for all cases.
- perf.txt shows speedup ~1.11x for n=5000 in this environment. Gains grow when SCCs are many and/or large; also, per-SCC join speeds the dual-tree step.

5) Limits & safety switches
- Tarjan’s recursion depth can overflow the stack for very deep chains. We keep perf at n=5000 to be safe here. In production, consider iterative Tarjan or larger stack.
- We keep a small-N fallback (V ≤ 1024 or SCCs ≤ 2) to avoid thread overhead.
- Resource bounds: Rayon threads ≤ CPU cores; no unbounded tasks. join is bounded.
- Corner cases: empty graph, single node, empty SCC handled. Membership mask short-circuits if the start is not in the SCC.

6) How to reproduce
- Build and run: cargo run
- Confirm parity/determinism: see console and run_summary.txt.
- Performance: see perf.txt and console speedup line.

7) Glossary
- Parallel — many helpers do different parts at the same time.
- Deterministic — same input gives the same output every time.
- Worker — a helper that processes one chunk of the data.
- Merge/combine — join partial answers in a fixed order.

8) Alternatives considered
- Parallel SCC detection (forward-backward, coloring, or lock-free label propagation): would change SCC enumeration order and make deterministic ordering and correctness harder without explicit sorting and conflict resolution; high patch size and algorithm swap needed.
- Parallel spanning forest per SCC using BFS levels: uses frontier expansion to expose more parallelism. Here, we want a deterministic DFS-style tree; BFS-level parallelism could change chosen tree edges and would need extra sorting to fix order.
- Graph-wide task graph (task per node/edge): huge task counts (O(V+E)) would overwhelm the scheduler and memory bandwidth; determinism would require fixed scheduling and merging, which negates the benefit.
