You are asked to parallelize a C++ graph algorithm.

The algorithm finds Strongly Connected Components (SCCs) in a directed graph and then, for each SCC, finds a minimal set of edges that preserves the connectivity of that component.

The provided code is in a single C++ file and contains a `Graph` class with the following key methods:
- `FindSCCs()`: Implements Tarjan's algorithm to find all SCCs. This is a sequential, recursive DFS-based algorithm.
- `MinimizeEdgesInSCC(const vector<int>& scc)`: For a given SCC, it builds two spanning trees (one on the forward graph, one on the reverse graph) and merges the edges to find a minimal set of edges that keeps the SCC strongly connected.
- `ReduceEdges()`: The main entry point that first calls `FindSCCs()` and then iterates through each SCC, calling `MinimizeEdgesInSCC` on it, and collecting the results.

Your task is to create a parallel, deterministic, and resource-bounded version of this algorithm, along with a rigorous differential test suite and a final justification document.

**Constraints:**
- The parallel implementation must be correct and deterministic.
- The solution should be resource-bounded (e.g., not spawning an excessive number of threads).
- A differential test harness is required to prove correctness against the original sequential version and to verify determinism.
- A short, evidence-backed justification for the parallelization strategy must be provided.
