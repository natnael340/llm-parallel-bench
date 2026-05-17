# Request

Parallelize the following sequential algorithm (C# Tarjan's SCC with edge reduction) and write a test for it.

## Input
- C# class implementing:
  - Tarjan's SCC algorithm (O(V+E))
  - Minimal SCC edge reduction (O(V+E))
  - BuildSpanningTree helper (DFS-based)
  - ReduceEdges orchestrator

## Constraints
- Language: C#
- Must preserve deterministic output (same SCCs, same reduced edges)
- Respect public API
- Use TPL (Task Parallel Library) with bounded concurrency

## Parallelization Strategy (PLAN)
**Analysis:**
1. FindSCCs() - Tarjan's DFS is inherently sequential (single global stack, discovery time, lowlink dependencies)
2. MinimizeEdgesInSCC() - operates on individual SCCs, but each is DFS-based (sequential per SCC)
3. ReduceEdges() - **KEY OPPORTUNITY**: Once SCCs are found, processing each SCC is independent

**Loop-carried deps:** None between SCCs in the minimize phase.
**Shared state:** Only the final reducedEdges list (can be collected with thread-safe merge).
**Ordering:** SCC discovery order must be deterministic; edge collection order can be fixed by sorting SCCs by first node ID.

**Strategy:**
- Keep FindSCCs() sequential (required for correctness).
- Parallelize the `foreach (var scc in SCCs)` loop in ReduceEdges() using Parallel.ForEach with bounded concurrency.
- Use ConcurrentBag or lock-protected list for collecting results, then sort for determinism.
- Sequential fallback for SCC count < 4.

**Minimal change set:**
- File: Graph_Parallel.cs
- Region: ReduceEdges() method body
