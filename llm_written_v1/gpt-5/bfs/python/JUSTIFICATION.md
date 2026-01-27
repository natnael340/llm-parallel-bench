This repository provides a deterministic, parallelized variant of the given BFS while preserving the public API.

Files and API
- bfs_baseline.py: original sequential reference with Graph and bfs(graph, start_vertex) -> list[int].
- bfs_parallel.py: parallel implementation with identical API and behavior.
- test_bfs.py: differential test runner comparing outputs and determinism.

How bfs_parallel.py works
- The Graph class is unchanged to keep the public API stable.
- The bfs function performs a standard queue-based traversal. To preserve the exact visitation order of the original (which depends on the adjacency list order), we only parallelize the expensive per-node neighbor filtering step.
- For each dequeued vertex current, neighbors = graph.vertices[current] is partitioned via _partition into balanced contiguous chunks. We freeze the current visited set (visited_frozen) and invoke ProcessPoolExecutor.map over _filter_neighbors_chunk for each chunk. Each worker filters out already-visited nodes within its chunk.
- The concatenation of results follows chunk order (which reflects the original adjacency order), then queue.extend(filtered) appends them in that order. Because only filtering is parallel and queue operations happen in the main process, the global traversal order is identical to the baseline.

Determinism and correctness
- Determinism is ensured by:
  1) Using a single ProcessPoolExecutor per bfs call to avoid unordered task completion affecting result order.
  2) Maintaining chunk order on collection; executor.map preserves submission order.
  3) visited is only mutated in the main process, after popping from the queue, mirroring the baseline algorithm.
- A small-input fast path (parallel_threshold = 1024) avoids parallel overhead for tiny neighbor lists and keeps behavior the same.
- Worker count is bounded by max(1, min(cpu_count(), 32)). This bounds resource usage and prevents unbounded process growth.
- No shared mutable state exists across workers; each receives only a chunk and an immutable frozenset of visited.

Edge cases handled
- Missing start vertex: return [].
- Self-loops and duplicate neighbors: the visited check in the main loop prevents revisiting; duplicates pass through but do not affect order.
- Empty neighbor lists and empty graphs.

Complexity
- Asymptotic complexity remains O(V + E). Parallel filtering reduces wall-clock time for large adjacency scans; memory overhead is modest for chunk lists and frozenset copies.

Evidence (tests)
- test_bfs.py exercises fixed edge cases, randomized graphs (seeded), and determinism (multiple runs). All groups pass; repeated executions yielded identical outputs across 2+ runs on this environment.
