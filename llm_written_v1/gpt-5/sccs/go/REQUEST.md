User request:
Parallelize the provided Go sequential algorithm and write tests for it. Also provide a brief justification.

Algorithm summary:
- Graph type with adjacency lists and reverse adjacency lists.
- Tarjan's SCC algorithm to find strongly connected components.
- For each SCC, builds forward and reverse spanning trees and merges edges to minimize edges within SCC.
- ReduceEdges finds SCCs, logs counts, and returns reduced edges.

Constraints/Goals per ParallelAgent contract:
- Produce minimal deterministic parallel implementation in Go.
- Use bounded worker pool, preserve order if required, no data races, no global shared state.
- Create test that runs baseline sequential vs parallel and checks equality, determinism, and simple perf gate.
- Provide CLI runner and evidence files.
- Deliver files: algo_parallel.go, test_algo.go (and runner), JUSTIFICATION.md.
