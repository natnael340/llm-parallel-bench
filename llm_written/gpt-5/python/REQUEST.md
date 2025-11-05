User request:
Parallelize the provided sequential algorithm and write a test for it. Also provide a brief justification.

Baseline code (Python, Graph with Tarjan SCC and SCC edge reduction) provided inline in the chat. Goal: produce a parallel implementation with deterministic behavior and tests.

Constraints from ParallelAgent:
- Follow PLAN → PATCH → TEST → REFINE≤2 → FINALIZE loop.
- Python: Prefer vectorization or ProcessPoolExecutor for CPU-bound; bounded workers; sequential fallback for small N.
- Deterministic partitioning and reduction order.
- Deliverables: algo_parallel.py, test_scc.py or run_scc.py, JUSTIFICATION.md. Evidence files summarizing runs.
