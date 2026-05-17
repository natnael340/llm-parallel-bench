What changed and why
The original program fills a score grid for two DNA strings. It uses two loops (rows and columns). Each cell looks at its three neighbors (top, left, and top-left) and picks the best score, never below 0. After the grid is filled, the code scans for the highest score, then “walks back” to build the best local alignment. For example, for ACGTC vs ACTC, the grid accumulates matches/mismatches and gaps until the highest-scoring local match is found.

We kept the public API the same. We added a parallel version of the grid fill only. The scan and traceback stay sequential.

How we made it parallel
We split the grid along anti-diagonals (also called wavefronts). All cells on one anti-diagonal depend only on cells from the previous anti-diagonal, so they can be computed at the same time. We assign each anti-diagonal’s cells to a fixed pool of threads with a static schedule. We place an implicit barrier at the end of each wavefront (provided by OpenMP’s for-loop) so the next wavefront starts only when the current one is done. Partial results are written into their own cells, so threads do not share writes.

ASCII sketch:
Input ▶ [Chunk A][Chunk B][Chunk C]
           │        │        │
        Worker1  Worker2  Worker3
           └───► Fixed-order merge ◄───┘
Here, each chunk is one anti-diagonal. Merge means: proceed to the next diagonal in order.

Determinism
• Same split: For a given input size, we always choose the same number of threads (capped at CPU cores) and the same diagonal boundaries.
• Same combine order: We complete diagonals strictly from top-left to bottom-right using the implicit barrier after each diagonal.
• No conflicts: Each thread writes only to its assigned cells; neighbors it reads are from earlier diagonals.

Proof it works
Our runner compares sequential vs. parallel on edge, small, medium, and large inputs. It repeats the parallel run to check determinism. All comparisons pass. See evidence/run_summary.txt for case-by-case results and hashes. We also record times for a large input; see evidence/perf.txt. On this machine, the large case timing is printed to stderr for visibility; the run still passes even if the machine is constrained.

Limits & safety switches
• Sequential fallback for tiny inputs (< ~20k cells) to avoid overhead.
• Threads are capped to core count; no oversubscription.
• Handles empty strings and size-1 cases.

How to reproduce
1) Build with OpenMP: g++ -O3 -fopenmp algo_parallel.cpp test_smith_waterman.cpp -o run_sw
2) Run tests: ./run_sw
3) Inspect evidence: cat evidence/run_summary.txt; cat evidence/perf.txt

Glossary
• Parallel — many helpers do different parts at the same time.
• Deterministic — same input gives the same output every time.
• Worker — a helper that processes one chunk of the data.
• Merge/combine — join partial answers in a fixed order.