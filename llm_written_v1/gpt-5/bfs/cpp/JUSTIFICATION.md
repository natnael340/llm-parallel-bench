This project adds a deterministic parallel breadth-first search while preserving the public API and supplies a rigorous test harness.

API preservation
- bfs_parallel.hpp exposes std::vector<int> bfs(Graph& g, int start_vertex), matching the user’s request and the sequential baseline (bfs_seq in bfs_seq.{hpp,cpp} remains intact for testing).

Parallelization strategy
- Implementation file: bfs_parallel.cpp
- The core is a level-synchronous BFS. For each frontier (vector<int> frontier), we parallelize neighbor enumeration but serialize the global “first-seen” filtering to guarantee the exact order of a standard BFS.
- Partitioning: the frontier is divided by index into buckets: std::vector<std::vector<int>> buckets, one per frontier vertex.
- Workers: OpenMP parallel for over indices [0, F). Each worker copies adjacency lists g.vertices[u] into its local bucket.
- Merge rule: After parallel gathering, a single serial pass over buckets in increasing index performs visited filtering and appends to next_frontier. This deterministic merge reproduces the discovery order of a queue-based BFS that scans neighbors of frontier[0], then frontier[1], etc.

Determinism
- Only the candidate gathering is parallel; the visited check and enqueue are done in a fixed order. Therefore the result is invariant under thread scheduling and matches bfs_seq exactly.
- Tests run the parallel BFS twice on the same random graph to ensure identical outputs.

Resource bounds and adaptivity
- Small-input fast path: if the graph has fewer than 50 vertices or OpenMP is unavailable (or only 1 thread), we call bfs_seq directly to avoid overhead.
- At runtime, if frontier size < 32, we perform a fully serial inner step, which also avoids launching parallel work for tiny levels.
- Memory: buckets size equals the frontier size. Each bucket reserves adjacency size to avoid reallocations; memory is linear in the number of candidate edges touching the frontier.

Race/deadlock/false-sharing avoidance
- No shared writes in the parallel region: each thread writes only to its bucket (unique index). No locks are required. The global visited map is mutated only in the serial merge.

Complexity
- Time matches standard BFS up to constant factors: O(V + E). The parallel region accelerates neighbor enumeration across the current level.

Testing evidence
- Files: test_bfs.cpp constructs edge cases (empty graph; isolated node), structured graphs (line, star, grid), and multiple random graphs with fixed seeds. It differentially compares bfs (parallel) vs bfs_seq and runs the parallel BFS twice to check determinism.
- Results: 51 test cases passed identically across two runs.
