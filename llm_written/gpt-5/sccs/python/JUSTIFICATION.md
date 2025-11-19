What changed and why
The original program finds strongly connected components (SCCs) in a directed graph using Tarjan’s depth‑first search (DFS). Then, for each SCC, it builds two DFS spanning trees (forward and reverse) and merges their edges to keep only the essential ones. Tarjan’s DFS is stateful (uses a stack, timestamps, and lowlink values), so it must run in order. But after SCCs are known, each SCC’s edge minimization is independent. We kept SCC discovery sequential and parallelized the per‑SCC minimization.

Tiny example: Suppose the graph has SCCs [0,1,2] and [3,4]. For [0,1,2] we build a forward tree and a reverse tree, then do the same for [3,4], and finally concatenate the results.

How we made it parallel
- Split: After finding all SCCs, we sort them deterministically (by size, then by node IDs). Each worker gets one SCC.
- Work per SCC: Build a forward spanning tree and a reverse spanning tree within that SCC and output their edges (sorted for stability).
- Fixed merge: We collect results in the same SCC order we submitted (A then B then C) and concatenate them.

Sketch
Input ▶ [Chunk A][Chunk B][Chunk C]
           │        │        │
        Worker1  Worker2  Worker3
           └───► Fixed-order merge ◄───┘

Why the answer is always the same (determinism)
- Same split: For a given graph, the SCC list and its deterministic sort are always the same.
- Same combine: We merge results strictly in SCC order. Within each SCC, we sort the produced edges.
- No conflicts: Each worker uses local temporaries only; the main process performs the final merge.

Proof it works (evidence)
- Correctness parity: Results from sequential and parallel versions match on edge, small, medium, and larger graphs. See evidence/run_summary.txt (all pass lines).
- Determinism: Two parallel runs on the same medium graph produce the same hash:
  determinism-hash: da4f1d958db1c68b0b6a6a1d03d8cc72a4ab1becaaf8bf735c8416568140dfef
  See evidence/run_summary.txt.
- Performance: On our smoke test (60 SCCs, 600 nodes), overhead dominates so speedup is < 1× (see evidence/perf.txt). We keep a small‑N sequential fallback; larger N would amortize process start‑up better.

Limits & safety switches
- Small inputs: If SCC count ≤ 3, we run sequentially to avoid parallel overhead.
- Resource bounds: Workers are capped at CPU count. No oversubscription.
- Corner cases handled: empty graph and single‑node graph.

How to reproduce
- Run tests and generate evidence: python test_scc.py
- Determinism check (two parallel runs and compare hashes): python test_scc.py (hash is printed in summary)
- Inspect performance numbers: cat evidence/perf.txt

Glossary
- Parallel — many helpers do different parts at the same time.
- Deterministic — same input gives the same output every time.
- Worker — a helper that processes one chunk of the data.
- Merge/combine — join partial answers in a fixed order.
