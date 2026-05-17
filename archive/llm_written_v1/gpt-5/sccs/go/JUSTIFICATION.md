What changed and why
The original program finds strongly connected components (SCCs) with Tarjan’s method. For each SCC it builds two depth‑first spanning trees (forward and reverse) and merges their edges. This reduces edges inside SCCs. In the original flow, SCCs are handled one after another on a single thread.

We parallelized the independent per‑SCC work. Tarjan’s search still runs once to partition the graph. After we have the list of SCCs, each SCC can be minimized without touching others. We kept the algorithm of building the two spanning trees the same, and we added stable sorting of the merged edges within each SCC so results are deterministic.

Small example
Say the graph has nodes [0 1 2 3 4] forming one SCC by a ring 0→1→2→3→4→0 and two extra edges 0→2 and 3→1. We compute a forward spanning tree from 0, a reverse tree from 0, and merge their edges. Only SCC operations are parallelizable; Tarjan’s DFS is not changed.

How we made it parallel
- Split: After FindSCCs, we get SCC[0], SCC[1], … in a fixed order.
- Workers: A bounded worker pool (up to CPU count) takes jobs {index, SCC}.
- Per‑job: Each worker runs MinimizeEdgesInSCC on its SCC (same logic as before).
- Merge: We collect results into an array by index and then concatenate in increasing index order. We also sort edges inside each SCC’s result to have a canonical order.

Why the answer is always the same
- Same split: Given the same graph, Tarjan returns the same SCC list ordering; the job indices are fixed.
- Same combine order: Results are written back by index and concatenated from 0..N-1.
- No conflicts: Workers use only local temporaries; the graph is read‑only.
- Deterministic per‑SCC: The edge sets are deduplicated via a map and then sorted, so the exact edge order is fixed.

Proof it works
- test_algo_test.go checks equality of sequential vs parallel outputs on edge, small, and medium random cases.
- It also runs the parallel path twice and compares SHA‑256 hashes to prove determinism.
- evidence/run_summary.txt contains the pass summary; evidence/perf.txt reports a smoke performance run on a larger graph.

Limits & safety
- A fast path falls back to sequential when SCC count < 4 to avoid overhead.
- Workers are capped at min(NumCPU, GOMAXPROCS, #SCCs).
- Empty graphs and size‑1 are handled.

How to reproduce
- go test -v .
- go run .  (produces evidence files and prints a summary)
- View evidence: cat evidence/run_summary.txt; cat evidence/perf.txt

Glossary
- Parallel — many helpers do different parts at the same time.
- Deterministic — same input gives the same output every time.
- Worker — a helper that processes one chunk of the data.
- Merge/combine — join partial answers in a fixed order.
