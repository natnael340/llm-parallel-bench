Decision summary
- Baseline bottleneck: reduceEdges() walks every strongly connected component (SCC) and, for each SCC, builds two spanning trees. On graphs with many SCCs this outer loop is the hot path and is embarrassingly parallel.
- Chosen strategy: Keep SCC discovery sequential and deterministic; parallelize the per-SCC edge minimization using a fixed-size worker pool, each worker writing into its own slot; combine in the original SCC order.
- Why it is safe (determinism): We use a fixed partition (SCC index 0..k-1) and merge results strictly in index order. Workers do not share mutable state; no races.
- Why it is faster: Each SCC’s two DFS traversals are independent. Running them in parallel across SCCs uses all cores on graphs with many SCCs.
- Worker count + chunk rule: min(available CPU cores, number of SCCs). Each task handles exactly one SCC.
- Small-N fallback threshold: V <= 1000 or single SCC → run sequentially (thread overhead would dominate).
- Best rejected alternative + one key reason: Parallel Tarjan/Kosaraju (intra-SCC parallelism) — correctness/determinism risk due to shared discovery state and non-deterministic traversal order.

What changed and why
The original process has two stages: first, find SCCs; second, for each SCC, pick a minimal set of edges by building a forward and a reverse spanning tree rooted at any node in that SCC and merge those trees. The SCC stage in the user code used recursive Tarjan’s DFS. That can blow the stack on deep or large graphs and is hard to parallelize without races.

We replaced the SCC discovery with an equivalent, iterative Kosaraju process to avoid recursion depth issues and to make the result order deterministic on the same input. After we obtain the list of SCCs, we split that list among workers. Each worker receives one SCC, runs the two DFS-based spanning tree builds over only the nodes in its SCC, and returns its edges. No worker touches another worker’s data.

Tiny example: Suppose the graph has nodes [0,1,2,3,4] and edges 0→1, 1→0, 2→3, 3→2, and 1→2. SCCs are [0,1] and [2,3] and [4]. Each SCC is processed alone. The worker for [0,1] computes its two trees; another worker does [2,3]; [4] yields no edges. We then append results in the order we discovered the SCCs.

How we made it parallel (conceptually)
- Split: After SCC discovery we have SCCs[0..k-1]. We create up to P workers, where P = min(cores, k).
- Work per worker: For SCC i, build a forward spanning tree on the original graph and another on the reversed graph, both restricted to nodes in SCC i. Return the union of these edges.
- Output writes: Each worker writes its answer into a private slot partial[i]. No shared lists are mutated.
- Combine: The main thread waits for all tasks to finish, then merges partial[0], partial[1], …, partial[k-1] into the final list. The combine order is fixed.

ASCII sketch
Input ▶ [Chunk A][Chunk B][Chunk C]
           │        │        │
        Worker1  Worker2  Worker3
           └───► Fixed-order merge ◄───┘

Why the answer is always the same (determinism)
- Fixed split: Given the same graph, SCCs are found by the same iterative Kosaraju walk, producing the same SCC list order.
- Fixed combine: We merge results by increasing SCC index. No task can reorder edges across SCCs.
- No conflicts: Workers use only local variables and write to unique partial[i] slots. There is no shared mutation or floating-point reduction.

Proof it works (evidence)
- Correctness parity: The test harness runs edge, small, medium, and large cases. All cases report PASS.
- Determinism: We run the parallel reduceEdges three times per case and hash the canonicalized edge list. The three hashes are equal and match the sequential baseline. See run_summary.txt.
- Performance: On a 12k-vertex, 48k-edge random graph, perf.txt records the best of three parallel timings versus sequential, and reports the speedup. On typical 4–8 core CPUs we expect ≥1.3× where many SCCs exist. If the graph has one giant SCC, speedup will be limited (explained below).

Limits & safety switches
- Small inputs: For V ≤ 1000 or a single SCC, we use the sequential path; threads would cost more than they save.
- Resource bounds: The worker pool is capped at CPU cores and at the number of SCCs, whichever is smaller. This prevents oversubscription.
- Corner cases: Empty graph, single-node graph, and graphs with isolated nodes are covered. Iterative SCC avoids stack overflow on deep graphs.

How to reproduce
- Compile and run tests: javac GraphSeq.java AlgoParallel.java TestAlgo.java && java TestAlgo
- Determinism check alone (run twice): java TestAlgo && java TestAlgo
- Performance with large graph (skip with skipperf): java TestAlgo

Glossary
- Parallel — many helpers do different parts at the same time.
- Deterministic — same input gives the same output every time.
- Worker — a helper that processes one chunk of the data.
- Merge/combine — join partial answers in a fixed order.

Alternatives we considered (and why we didn’t pick them)
1) Parallel Tarjan (run DFS in multiple threads over shared arrays disc/low/stack). This would need locks or atomics around discovery and the shared stack, which harms speed and makes order non-deterministic; correcting for races is complex and brittle.
2) Parallelize within each spanning tree (parallel DFS/BFS over nodes of a single SCC). Each SCC’s edges would require shared visited sets; coordinating that needs locks and could create non-deterministic visitation order, changing which edges become tree edges.
3) Graph partitioning into blocks then running SCC per block with a task graph (advanced). For general graphs, cross-block edges force a complex merge phase (condensation DAG stitching). That adds heavy overhead and correctness risk for no gain here since SCC discovery already linearizes the work cleanly.
4) ForkJoin parallel streams over SCCs. This makes worker count less predictable and may oversubscribe in environments that also use threads elsewhere. Our fixed thread pool provides tighter resource bounds.
