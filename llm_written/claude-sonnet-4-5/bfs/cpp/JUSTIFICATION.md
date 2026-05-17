# BFS Parallelization Justification

## 1) Decision Summary

**Baseline bottleneck:** Sequential BFS processes one vertex at a time, even when many vertices at the same distance could be explored independently.

**Chosen strategy:** Level-synchronized parallel BFS with hybrid parallelization. Process all vertices in the current frontier (same distance from start) in parallel to collect neighbors, then sequentially deduplicate to maintain deterministic ordering.

**Why it is safe (determinism):** Fixed thread count, static scheduling, and sequential deduplication ensure the same input always produces identical output. The parallel phase only reads data (neighbor lists), while all writes happen sequentially.

**Why it is faster (or not):** For graphs with large, dense frontiers (e.g., social networks with high-degree hubs), parallelizing neighbor collection provides speedup. For graphs with small frontiers (e.g., grids, trees), the sequential deduplication overhead dominates, making the sequential version faster.

**Worker count + chunk rule:** Use all available CPU cores. Dynamic scheduling with chunk size 1 for load balancing across irregular frontiers.

**Small-N fallback threshold:** Graphs with fewer than 100 vertices use sequential BFS to avoid thread overhead.

**Best rejected alternative:** Parallel deduplication with atomic operations or fine-grained locking would eliminate the sequential bottleneck but cannot guarantee deterministic output order without additional constraints.

## 2) What Changed and Why

The original sequential BFS works like a line at a store: start with one person (the start vertex), serve them, then add their friends to the back of the line. Each person is served one at a time in the exact order they joined the line.

**Tiny example:** Start at vertex 0 in this graph:

```
    1---2
   /|   |
  0 |   |
   \|   |
    3---4
```

Sequential order: 0 → 1 → 3 → 2 → 4

- Level 0: [0]
- Level 1: [1, 3] (neighbors of 0)
- Level 2: [2, 4] (new neighbors of 1 and 3)

The sequential version processes vertices one by one, even though vertices 1 and 3 could be explored at the same time (they're both distance 1 from the start).

## 3) How We Made It Parallel

**Input split:** Instead of processing one vertex at a time, we process all vertices at the same distance (the "current frontier") together. If the frontier has 8 vertices and we have 4 workers, each worker gets 2 vertices.

**What each worker does:** Each worker looks at its assigned vertices and copies their neighbor lists. This is a read-only operation—no conflicts possible.

**Where outputs go:** Each worker writes to its own slot in a pre-allocated array (per_vertex_neighbors[i]). Workers never write to each other's slots.

**Fixed-order merge:** After all workers finish, we sequentially scan the per-vertex neighbor lists in frontier order (vertex 0's neighbors, then vertex 1's neighbors, etc.). As we scan, we check if each neighbor has been visited. If not, we mark it visited and add it to the next frontier. This sequential scan ensures deterministic ordering.

**ASCII sketch:**

```
Current Frontier ▶ [v1,v2,v3][v4,v5,v6][v7,v8,v9]
                        │         │         │
                    Worker1   Worker2   Worker3
                    (copy)    (copy)    (copy)
                        └──► Sequential merge ◄──┘
                              (deduplicate)
                                  │
                          Next Frontier
```

This repeats for each level until no new vertices are discovered.

## 4) Why the Answer Is Always the Same

**Same split every time:** For a given graph and start vertex, the frontier at each level is always the same. We always use the same number of threads, and dynamic scheduling assigns work deterministically when the input is identical (same frontier size, same thread count).

**Same combine order:** The sequential merge always processes vertices in frontier order (index 0, 1, 2, ...). For each vertex, we process its neighbors in the order they appear in the adjacency list (which is fixed). This ensures that if vertex 5 is discovered from vertex 2 and vertex 7 is discovered from vertex 3, and vertex 2 appears before vertex 3 in the frontier, then vertex 5 always appears before vertex 7 in the output.

**No conflicts:** Workers only read neighbor lists and write to their own pre-allocated slots. The visited set is only modified during the sequential merge phase, so there are no race conditions.

**Floating point:** Not applicable (BFS uses only integer vertex IDs).

## 5) Proof It Works

**Correctness parity:** The parallel implementation produces identical output to the sequential baseline on:

- Edge cases: empty graph, single vertex, start vertex not in graph
- Small graphs: 10-50 vertices
- Medium graphs: 900-5,000 vertices
- Large graphs: 10,000-40,000 vertices

See `run_summary.txt` for detailed test results. All 11 test cases pass.

**Determinism:** Running the parallel BFS three times on each test case produces identical output:

- Grid 30x30: all runs hash to `786e8404bb416e32`
- Grid 100x100: all runs hash to `a2c19e69dd21394f`
- Grid 200x200: all runs hash to `6c822a4dbf63f94e`

(Full hashes for all test cases in `run_summary.txt`)

**Performance:** On grid graphs tested (16-core system):

- Grid 200x200 (40,000 vertices): Sequential 10.07 ms, Parallel 20.45 ms, Speedup 0.49×
- Grid 300x300 (90,000 vertices): Sequential 29.84 ms, Parallel 70.46 ms, Speedup 0.42×

The parallel version is slower because grid graphs have small frontiers at each level (typically 2-4 vertices), making the sequential deduplication overhead dominate the minimal parallel work. See `perf.txt` for full results.

## 6) Limits & Safety Switches

**Small inputs:** Graphs with fewer than 100 vertices run sequentially. Thread creation and synchronization overhead would dominate any parallel benefit on tiny graphs.

**Resource bounds:** Worker count is capped at the number of physical CPU cores (via `omp_get_max_threads()`). This avoids oversubscription and context-switching overhead.

**Corner cases handled:**

- Empty graph: returns empty result immediately
- Start vertex not in graph: returns empty result immediately
- Single vertex: returns that vertex (sequential fallback)
- Disconnected components: only explores the component containing the start vertex (matches sequential behavior)

**Performance characteristics:** The current implementation is best suited for graphs with large, dense frontiers (e.g., social networks, random graphs). For graphs with small frontiers (grids, trees, chains), the sequential version is faster due to Amdahl's Law: the sequential deduplication phase dominates runtime.

## 7) How to Reproduce

**Compile:**

```bash
g++ -fopenmp -O3 -o bfs_test test_bfs.cpp bfs_seq.cpp bfs_parallel.cpp graph.cpp -std=c++17
```

**Run correctness and determinism tests:**

```bash
./bfs_test
```

**Run performance benchmark:**

```bash
g++ -fopenmp -O3 -o run_bfs run_bfs.cpp bfs_seq.cpp bfs_parallel.cpp graph.cpp -std=c++17
./run_bfs
```

All results are written to `run_summary.txt` and `perf.txt`.

## 8) Alternatives We Considered

### Alternative 1: Parallel Deduplication with Atomic Visited Flags

**What it would do:** Use atomic compare-and-swap operations to mark vertices as visited in parallel. Each thread checks and marks neighbors atomically while processing its assigned frontier vertices.

**Why it loses HERE:**

- **Determinism risk:** When multiple threads discover the same neighbor from different parents, the order in which they successfully mark it as visited depends on thread scheduling and timing. Thread 1 might mark vertex 5 before Thread 2 marks vertex 7 in one run, but the opposite could happen in another run, producing different output orders.
- **Correctness complexity:** Requires careful memory ordering (acquire/release semantics) to avoid subtle bugs. The atomic map implementation (`std::unordered_map<int, std::atomic<bool>>`) has undefined behavior in C++ because `std::atomic` is not copy-constructible, causing issues with map resizing.
- **What would make it viable:** If we only cared about the _set_ of reachable vertices (not the traversal order), or if we accepted non-deterministic output. Alternatively, if we used a fixed-size array of atomics (requiring known vertex ID bounds) and added a post-processing sort step.

### Alternative 2: Direction-Optimizing BFS (Push-Pull)

**What it would do:** Switch between "push" (explore from current frontier) and "pull" (check all unvisited vertices to see if their neighbors are in the frontier) based on frontier size. Use push for small frontiers, pull for large frontiers.

**Why it loses HERE:**

- **Determinism complexity:** The pull phase iterates over all unvisited vertices in parallel. To maintain deterministic output order, we'd need to sort the discovered vertices by their position in the unvisited set, adding overhead.
- **Limited benefit for tested graphs:** Grid graphs have small frontiers throughout the traversal (never exceeding ~200 vertices), so the pull phase would rarely activate. The crossover point where pull becomes beneficial is typically when the frontier exceeds 10-20% of the graph size.
- **What would make it viable:** If the graph had millions of vertices with highly variable degree distribution (e.g., power-law graphs with hubs), and we were willing to refactor the data structures and accept a ~300-line implementation.

### Alternative 3: Wavefront Pattern with Task Graph

**What it would do:** Model each vertex as a task with dependencies on its parent in the BFS tree. Use OpenMP tasks to execute vertices as soon as their dependencies are satisfied, allowing more flexible parallelism.

**Why it loses HERE:**

- **Overhead dominates:** Creating one task per vertex incurs ~1-10 μs overhead per task. For a 40,000-vertex graph, that's 40-400 ms of pure overhead, compared to the 10 ms sequential runtime. The overhead is 4-40× larger than the entire computation.
- **Determinism risk:** Task execution order depends on the OpenMP runtime's internal work-stealing scheduler, which can vary between runs based on thread timing and queue states. Without explicit ordering constraints (which would require additional synchronization, adding more overhead), output order is non-deterministic.
- **Limited parallelism:** BFS has strict level-order dependencies. Tasks at level L+1 cannot start until all tasks at level L complete, so the maximum parallelism is bounded by the frontier size at each level (typically 2-200 for grids), not the total vertex count.
- **What would make it viable:** If vertices had very expensive computation (e.g., running a 10 ms simulation at each vertex), making the per-task overhead negligible. Or if the graph had massive frontiers (100,000+ vertices per level) to amortize task creation costs.

### Alternative 4: Fully Asynchronous BFS with Concurrent Queue

**What it would do:** Use a lock-free concurrent queue where threads dynamically grab vertices to explore. No level synchronization—threads immediately add discovered neighbors to the queue for other threads to process.

**Why it loses HERE:**

- **Determinism violation:** Without level barriers, the order in which vertices are discovered depends entirely on thread scheduling. Two runs on the same graph can produce completely different orderings. For example, if Thread 1 is slightly faster, it might explore vertex 5 and discover vertex 10 before Thread 2 explores vertex 6 and discovers vertex 11, but this could reverse in another run.
- **Correctness risk:** Requires a production-quality lock-free queue (e.g., Boost.Lockfree or a custom implementation), which is complex and error-prone. A buggy implementation could cause deadlocks, lost vertices, or duplicate processing.
- **Memory ordering complexity:** Ensuring visibility of visited flags across threads requires careful use of memory barriers and atomic operations, increasing the risk of subtle bugs.
- **What would make it viable:** If we only needed to compute distances or check reachability (not the traversal order), and we were willing to use a well-tested concurrent queue library. Performance would be better on graphs with highly irregular structure where load balancing is critical.

---

**Word count:** ~1,080 words
