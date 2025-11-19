What changed and why
The original program finds strongly connected components (SCCs) with Tarjan’s algorithm, then, for each SCC, it builds a forward and a reverse spanning tree and keeps those edges. In simple terms: group nodes that can reach each other, then keep just enough edges inside each group to stay connected both ways.
Example with 5 nodes (0–4): edges 0→1→2→0 and 3↔4. We get two SCCs: {0,1,2} and {3,4}. For {0,1,2} we collect a few edges to span it; for {3,4} we keep 3→4 and 4→3.

How we made it parallel
We parallelized the independent per-SCC processing. After we list SCCs, we split that list into chunks where each chunk is one SCC. Each worker gets a fixed set of SCC indices and, for each SCC, builds the forward and reverse spanning trees locally. Workers do not share data; they write into their own vectors. Finally, we merge results in index order to keep a stable output sequence.

ASCII sketch
Input ▶ [SCC0][SCC1][SCC2]
           │      │      │
        Worker1 Worker2 Worker3
           └───► Fixed-order merge ◄───┘

Why the answer is always the same
- Fixed split: we use a static schedule over the SCC index list. For the same input, the same SCCs and indices appear, so workers get the same chunks in the same order.
- Fixed combine: we concatenate partial results strictly by SCC index (0, then 1, then 2). Inside each SCC, we sort the edges to a canonical order. No shared state is written by workers.

Proof it works
Our test runner compares the original sequential version with the parallel version on edge, small, medium, and large random cases. All parity and determinism checks pass. See evidence/run_summary.txt for case details and hashes. We also run the parallel version twice per input to confirm identical outputs; hashes match.

Performance
On a small synthetic case (V=20k, E=80k) the runtime is short and overhead hides the gain (speedup ≈ 0.90×). See evidence/perf.txt. The design should help when there are many SCCs of non-trivial size; small-N fallback avoids overhead on tiny cases.

Limits & safety
- Small inputs: if SCC count ≤ 3 or only one thread, we run sequentially.
- Resource bounds: OpenMP uses up to the machine’s core count; no oversubscription is created in our code.
- Corner cases (empty graph, single node, small cycles) are covered by tests.

How to reproduce
- Build: g++ -O3 -fopenmp test_algo.cpp -o test_algo
- Run tests: ./test_algo  (writes evidence/*)
- Determinism check: run ./test_algo twice and compare hashes in evidence/run_summary.txt

Glossary
- Parallel — many helpers do different parts at the same time.
- Deterministic — same input gives the same output every time.
- Worker — a helper that processes one chunk of the data.
- Merge/combine — join partial answers in a fixed order.
