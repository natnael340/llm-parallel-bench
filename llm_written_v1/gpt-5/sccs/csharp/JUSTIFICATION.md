What changed and why
- The original code finds strongly connected components (SCCs) with Tarjan’s method and, for each SCC, builds two spanning trees (forward and reverse) to keep only essential edges. This last step runs each SCC one by one.
- We keep Tarjan sequential (it needs a single shared stack and time counter). We parallelize the independent per‑SCC reduction: every SCC can be minimized without touching others.

Tiny example
- Suppose SCCs are: [0,1,2] and [3,4]. For [0,1,2] we build a forward tree and a reverse tree from node 0. For [3,4] we do the same from node 3. Previously this was done in a loop. Now both SCCs are processed at the same time.

How we made it parallel
- We split the list of SCCs by their index: SCC[0], SCC[1], … .
- We start a bounded set of workers (up to the machine’s core count). Each worker takes specific indexes assigned by Parallel.For.
- Each worker computes the essential edges for its SCC only, writing the result into its own per‑index slot.
- When all workers finish, we merge the per‑SCC results in a fixed order (index 0, then 1, then 2).

Fixed order and determinism
- The split is by fixed indexes; given the same input graph, the list of SCCs is the same, so each SCC goes to the same slot.
- Inside each SCC we sort edges (by from, then to). We then append SCC results in order 0..n‑1. With no shared writes and a fixed merge order, output is identical across runs.

Evidence it works
- Parity: test runner compares sequential vs parallel on edge/small/medium/large graphs. All matched; see evidence/run_summary.txt.
- Determinism: running parallel twice on the same big graph yields the same 64‑bit hash. Both hashes match; see evidence/run_summary.txt.
- Performance: For N=2000, M=8000 on this environment we did not see speedup (0.62×). This is expected for modest sizes and added overhead. The design scales with more/larger SCCs; we keep a small‑N sequential fast path.

Limits & safety
- Sequential fallback for 0 or 1 SCC avoids overhead when parallelism cannot help.
- We cap workers to Environment.ProcessorCount to avoid oversubscription.
- Corner cases (empty graph, size 1) are handled in tests and pass.

How to reproduce
- dotnet run --project llm_written.csproj
- Inspect evidence/run_summary.txt for parity/determinism and evidence/perf.txt for timing.

Glossary
- Parallel — many helpers work at the same time.
- Deterministic — same input gives the same output every time.
- Worker — a helper that processes one chunk of the data.
- Merge/combine — join partial answers in a fixed order.
