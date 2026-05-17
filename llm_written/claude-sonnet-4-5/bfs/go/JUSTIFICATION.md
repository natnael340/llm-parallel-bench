# Parallel BFS Implementation - Justification

## Decision Summary

**Baseline bottleneck:** Sequential BFS processes one vertex at a time, visiting neighbors in queue order. For large graphs, this can be slow.

**Chosen strategy:** Level-synchronous parallel BFS with worker pool. Each BFS level is processed in parallel by dividing the current frontier into chunks.

**Why it is safe (determinism):** Adjacency lists are sorted once at the start. Workers process fixed chunks in a fixed order. Results are merged in worker order (which matches chunk order). Same input always produces the same chunk assignment and merge order.

**Why it is faster:** For graphs with wide levels (many vertices at the same distance from start), multiple workers can discover neighbors simultaneously instead of one-by-one.

**Worker count + chunk rule:** Uses all available CPU cores. Chunks are created by dividing the current level size by worker count, ensuring balanced work distribution.

**Small-N fallback threshold:** Graphs with fewer than 100 vertices use pure sequential BFS. Frontiers smaller than 20 vertices also use sequential processing within a level.

**Best rejected alternative:** Asynchronous work-stealing BFS would allow workers to grab vertices from a shared queue without waiting for level completion. Rejected because it breaks BFS semantics (level order) and introduces non-deterministic discovery order.

## What Changed and Why

The original BFS algorithm works like exploring a building floor-by-floor. You start at the entrance (the start vertex), visit all rooms on the ground floor, then all rooms on the first floor, then the second floor, and so on. You never skip ahead to a higher floor until you've finished the current floor.

In the sequential version, you use a queue (like a to-do list). You visit one room, write down all the doors you find, then move to the next room on your list. Each room is visited exactly once, and you mark visited rooms to avoid going back.

**Tiny example:** Imagine a social network with 8 people. Person 0 knows persons 1, 2, and 3. Person 1 knows 4 and 5. Person 2 knows 6. Person 3 knows 7.

Starting from person 0:
- **Level 0:** Visit person 0
- **Level 1:** Visit persons 1, 2, 3 (all friends of 0)
- **Level 2:** Visit persons 4, 5, 6, 7 (friends of level 1)

The sequential version visits them one-by-one: 0, then 1, then 2, then 3, then 4, then 5, then 6, then 7.

## How We Made It Parallel

The key insight is that within a single level, we can visit multiple rooms at the same time because they don't depend on each other. We can't skip to the next level early, but we can split the current level's work among multiple workers.

**How the input is split into independent chunks:**
- When we have a level with many vertices (say 100 vertices at distance 3 from the start), we divide them into equal chunks.
- If we have 4 workers and 100 vertices, worker 1 gets vertices 0-24, worker 2 gets 25-49, worker 3 gets 50-74, and worker 4 gets 75-99.
- The chunk assignment is always the same for a given level size and worker count.

**What each worker does on its own chunk:**
- Each worker visits its assigned vertices and discovers their neighbors.
- The worker keeps a private list of newly discovered neighbors.
- The worker checks a shared "visited" map to avoid rediscovering vertices that other workers or previous levels already found.

**Where each worker writes its outputs:**
- Each worker writes to its own private buffer (no sharing during discovery).
- When done, the worker sends its buffer back to the main coordinator through a numbered channel.

**How partial results are combined in a FIXED order:**
- The coordinator collects all worker results.
- Results are sorted by worker ID (worker 0's results first, then worker 1's, etc.).
- The coordinator merges them in this fixed order, removing duplicates.
- This merged list becomes the next level's frontier.

**ASCII sketch:**
```
Current Level ▶ [Vertex 0-24][Vertex 25-49][Vertex 50-74][Vertex 75-99]
                      │             │             │             │
                  Worker 0      Worker 1      Worker 2      Worker 3
                      │             │             │             │
                 [neighbors]   [neighbors]   [neighbors]   [neighbors]
                      └─────────────┴─────────────┴─────────────┘
                                          │
                              Fixed-order merge (0→1→2→3)
                                          │
                                    Next Level
```

## Why the Answer Is Always the Same (Determinism)

**Same split every time:** For a given graph and worker count, the chunk boundaries are calculated the same way every run. Vertex 0-24 always go to worker 0, etc.

**Same combine order:** We always merge worker 0's results first, then worker 1's, then worker 2's, and so on. This is enforced by sorting results by worker ID before merging.

**No conflicts:** Each worker only writes to its own private buffer during discovery. The only shared structure is the "visited" map, which uses thread-safe operations (sync.Map in Go). When merging, we process results sequentially in a single thread, so there's no race.

**Sorted adjacency lists:** Before starting BFS, we sort all neighbor lists. This means when worker 0 visits vertex 5, it always sees neighbors in the same order (say [10, 15, 20] instead of random order). This ensures consistent discovery order within each worker.

**For floating point:** Not applicable - BFS only uses integers (vertex IDs).

## Proof It Works

**Correctness parity:**
- The parallel implementation produces identical output to the sequential baseline on all test cases.
- Test cases include: empty graph, single vertex, small chain (5 vertices), small star (10 vertices), medium grid (100 vertices), medium complete graph (50 vertices), large grid (2500 vertices), large random sparse graph (1000 vertices), and large binary tree (1023 vertices).
- All 9 correctness tests passed. See `run_summary.txt` for full details.

**Determinism:**
- Each test case was run 3 times with the parallel implementation.
- All 3 runs produced identical results, verified by SHA-256 hash comparison.
- Example hashes from `run_summary.txt`:
  - `large_grid_50x50`: hash `f48d5a936abd2a2f...` (all 3 runs)
  - `large_random_sparse_1000`: hash `3b2969d8f1118b8d...` (all 3 runs)
- All 9 determinism tests passed.

**Performance:**
- Tested on graphs ranging from 500 to 10,000 vertices.
- **Important finding:** The parallel version is slower than sequential for all tested graph sizes.
- On a 16-core system with a 10,000-vertex graph:
  - Sequential: 23.0 ms
  - Parallel: 37.1 ms
  - Speedup: 0.62× (slower, not faster)
  - Efficiency: 3.9%
- See `perf.txt` for complete performance data.

**Why is it slower?** BFS has inherent limitations for parallelization:
1. **Level synchronization:** Each level must complete before the next begins. This is a hard dependency in BFS.
2. **Small parallel work:** Each level often has limited vertices, so there's not much work to parallelize.
3. **Overhead dominates:** Creating goroutines, synchronizing with channels and sync.Map, and merging results costs more than the actual neighbor discovery for these graph sizes.
4. **Memory bandwidth:** Graph traversal is memory-bound, not CPU-bound. Multiple workers compete for the same memory bandwidth.

## Limits & Safety Switches

**Small inputs:** Graphs with fewer than 100 vertices always use sequential BFS. This threshold was chosen because the parallel overhead (goroutine creation, synchronization) exceeds any potential benefit for small graphs.

**Small frontiers:** Even in large graphs, if a particular level has fewer than 20 vertices, we process it sequentially. This handles cases where the graph has a narrow "waist" (e.g., a long chain).

**Resource bounds:** Worker count is capped at the number of CPU cores (`runtime.NumCPU()`). We never create more workers than cores, avoiding oversubscription and context-switching overhead.

**Corner cases handled:**
- Empty graph (no vertices): Returns empty result immediately.
- Start vertex not in graph: Returns empty result immediately.
- Disconnected graphs: Only visits the connected component containing the start vertex.
- Self-loops: Handled correctly by the visited check.

## How to Reproduce

All commands assume you're in the project directory with the Go files.

**Rerun correctness parity:**
```bash
go run bfs_sequential.go bfs_parallel.go test_bfs.go run_bfs.go
```
This runs 9 correctness tests comparing sequential vs parallel output. Results are written to `run_summary.txt`.

**Rerun determinism checks:**
The above command also runs determinism tests (3 parallel runs per test case with hash comparison). Check `run_summary.txt` for the "DETERMINISM TESTS" section.

**Rerun performance tests:**
```bash
go run bfs_sequential.go bfs_parallel.go perf_bfs.go
```
This benchmarks both implementations on graphs of 500, 2000, 5000, and 10,000 vertices. Results are written to `perf.txt`.

## Alternatives We Considered

### 1. Asynchronous Work-Stealing BFS

**What it would do:** Instead of waiting for each level to complete, workers would grab vertices from a shared queue as soon as they're available. This eliminates level synchronization barriers.

**Why it loses HERE:**
- **Breaks BFS semantics:** BFS requires visiting vertices in level order (distance 1, then distance 2, then distance 3, etc.). Work-stealing would visit vertices in whatever order workers happen to grab them, producing a different traversal order than the sequential baseline.
- **Non-deterministic:** The order in which workers grab vertices from a shared queue depends on thread scheduling, which is non-deterministic. Same input could produce different output across runs.
- **Correctness risk:** While it would still visit all reachable vertices, the output order wouldn't match the sequential baseline, failing our correctness tests.

**What would make it viable:** If we only cared about finding all reachable vertices (not the specific BFS order), work-stealing would be acceptable. For example, in a reachability check ("can we get from A to B?"), order doesn't matter.

### 2. Direction-Optimizing BFS (Push-Pull)

**What it would do:** For levels with large frontiers, switch from "push" mode (current frontier discovers neighbors) to "pull" mode (unvisited vertices check if any frontier vertex points to them). This can be faster for high-degree graphs.

**Why it loses HERE:**
- **Complexity vs benefit:** Implementing push-pull requires maintaining both forward and backward edge lists, doubling memory usage. It also requires heuristics to decide when to switch modes.
- **Patch size limit:** This would require changing the graph data structure (adding reverse edges), modifying the BFS loop logic, and adding mode-switching heuristics. Estimated 4+ files changed and 300+ lines of code.
- **Determinism risk:** The mode-switching heuristic (e.g., "switch when frontier size > 10% of graph") could behave differently across runs if graph structure changes slightly, risking non-determinism.
- **Limited applicability:** Push-pull helps most on scale-free graphs (social networks, web graphs) with very high-degree vertices. Our test graphs are mostly uniform-degree (grids, trees), where push-pull offers little benefit.

**What would make it viable:** For massive graphs (millions of vertices) with power-law degree distributions, push-pull can provide 2-5× speedup. It would be worth the complexity if we were targeting that specific use case.

### 3. GPU-Based BFS

**What it would do:** Offload BFS computation to a GPU, which can process thousands of vertices in parallel using CUDA or OpenCL.

**Why it loses HERE:**
- **Overhead dominates:** Transferring the graph to GPU memory and results back to CPU takes longer than the actual BFS computation for graphs under 100,000 vertices.
- **Language constraint:** The baseline is in Go, which has limited GPU support. We'd need to use CGo to call CUDA libraries, adding significant complexity.
- **Patch size limit:** This would require rewriting the entire algorithm in CUDA C, creating a separate GPU memory management layer, and adding host-device synchronization. Estimated 5+ new files and 500+ lines of code.
- **Determinism risk:** GPU thread scheduling is non-deterministic by default. Achieving deterministic output would require careful atomic operations and fixed thread-block assignments, further increasing complexity.

**What would make it viable:** For graphs with 10+ million vertices and high parallelism (wide levels), GPU BFS can achieve 10-100× speedup over CPU. This is common in scientific computing (protein networks, circuit simulation).

### 4. Wavefront/Level-Fusion BFS

**What it would do:** Instead of strict level-by-level processing, allow workers to speculatively start processing level N+1 while level N is still finishing. Use a dependency tracker to ensure correctness.

**Why it loses HERE:**
- **Dependency tracking overhead:** Each vertex would need a "level" tag and a dependency counter. Workers would need to check dependencies before processing each vertex, adding synchronization overhead.
- **Complexity:** Implementing correct dependency tracking requires careful lock-free data structures or fine-grained locking. Estimated 250+ lines of new code.
- **Limited benefit for BFS:** Unlike algorithms with independent subproblems (e.g., dynamic programming), BFS has strict level dependencies. Speculative execution would often be wasted work when dependencies aren't satisfied.
- **Determinism risk:** Speculative execution order depends on which worker finishes first, introducing non-determinism unless we add additional ordering constraints (which negates the performance benefit).

**What would make it viable:** For algorithms with looser dependencies (e.g., Bellman-Ford shortest paths, where you can relax edges in any order), wavefront approaches can provide 2-3× speedup. BFS's strict level structure makes it a poor fit.

## Conclusion

The parallel BFS implementation is **correct** and **deterministic**, matching the sequential baseline exactly on all test cases. However, it is **not faster** for the tested graph sizes due to BFS's inherent synchronization requirements and the overhead of parallelization.

This is a valuable lesson: not all algorithms benefit from parallelization. BFS is fundamentally limited by Amdahl's Law—the sequential level-synchronization barrier prevents scaling beyond a small number of cores. For practical BFS applications on graphs under 100,000 vertices, the sequential implementation is recommended.

The parallel implementation serves as a correct reference for how to parallelize BFS while maintaining determinism, which may be useful for educational purposes or as a building block for more complex graph algorithms.
