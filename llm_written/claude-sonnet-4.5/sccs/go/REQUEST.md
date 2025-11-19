# Parallelization Request

## Input Algorithm
Tarjan's Strongly Connected Components (SCC) algorithm with minimal edge reduction.

**Language**: Go

**Key Components**:
1. `FindSCCs()` - Tarjan's DFS-based algorithm to find all SCCs in a directed graph
2. `MinimizeEdgesInSCC()` - For each SCC, compute a minimal edge set using forward + reverse spanning trees
3. `ReduceEdges()` - Orchestrates SCC finding and per-SCC edge minimization

## Constraints
- Maintain deterministic output (same input → same output)
- Preserve correctness of SCC detection and edge reduction
- Use bounded concurrency (cap at CPU count)
- No unbounded goroutines
- Avoid data races

## Parallelization Target
The `ReduceEdges()` method processes each SCC independently in `MinimizeEdgesInSCC()`. This per-SCC work is the parallelization opportunity.

## Deliverables
1. `algo_parallel.go` - Parallel implementation
2. `test_scc.go` - Differential test harness
3. `JUSTIFICATION.md` - Plain-language explanation with evidence
