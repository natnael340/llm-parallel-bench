User request:
Parallelize the following sequential algorithm and write a test for it.

Provided code (C#) implements:
- A Graph class with adjacency and reverse adjacency lists.
- Tarjan’s SCC algorithm (FindSCCs with TarjanDFS).
- Minimal SCC edge reduction via two DFS spanning trees within each SCC (MinimizeEdgesInSCC + BuildSpanningTree).
- ReduceEdges runs FindSCCs then sequentially processes each SCC to compute essential edges.

Constraints from ParallelAgent contract:
- Provide a deterministic, resource-bounded parallel implementation.
- Keep public API intact; minimal changes.
- Provide tests comparing baseline vs parallel on multiple sizes, check determinism, and light perf.
- Deliverables: algo_parallel.cs, test runner, JUSTIFICATION.md, evidence files.

Chosen approach:
- Preserve sequential Tarjan (global stack dependence).
- Parallelize the per-SCC edge reduction stage with bounded degree using TPL.
- Fixed partitioning by SCC index; per-index result buffer; ordered merge ensures deterministic output.
- Sort edges within each SCC result to ensure deterministic ordering regardless of hash set enumeration.
- Keep a sequential baseline (algo_sequential.cs) for differential tests.
