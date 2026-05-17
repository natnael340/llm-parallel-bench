# BFS Parallelization Justification

## Decision Summary

**Baseline bottleneck:** Sequential BFS processes one vertex at a time, even when many vertices at the same level could be explored independently.

**Chosen strategy:** Level-synchronous parallel BFS. Process all vertices within each BFS level in parallel, then synchronize before moving to the next level.

**Why it is safe (determinism):** Fixed level-by-level processing with sorted vertex IDs within each level ensures the same traversal order every time.

**Why it is faster:** Vertices within the same BFS level have no dependencies on each other, so we can explore their neighbors in parallel.

**Worker count + chunk rule:** Use Rayon's default thread pool (bounded to CPU count), with automatic work-stealing for load balancing.

**Small-N fallback threshold:** For graphs with fewer than 100 vertices or levels with fewer than 50 vertices, use sequential processing to avoid thread overhead.

**Best rejected alternative:** Lock-based shared queue with worker threads. Rejected because it creates non-deterministic ordering due to race conditions in queue access, and lock contention would hurt performance.

## What Changed and Why

The original BFS works like exploring a building floor by floor. You start at one room (the start vertex), visit it, then add all connected rooms to a list. You then visit each room in that list one by one, adding their connected rooms to the end of the list. This continues until you've visited every reachable room.

For example, imagine a small network:
- Room 1 connects to rooms 2 and 3
- Room 2 connects to rooms 1 and 4
- Room 3 connects to rooms 1 and 5
- Rooms 4 and 5 are dead ends

Starting from room 1:
- Level 0: Visit room 1, discover rooms 2 and 3
- Level 1: Visit rooms 2 and 3, discover rooms 4 and 5
- Level 2: Visit rooms 4 and 5, no new rooms
- Done!

The sequential version processes one room at a time, even within the same level.

## How We Made It Parallel

Instead of visiting rooms one by one within each level, we send multiple workers to explore rooms at the same level simultaneously.

**Input split:** At each BFS level, we have a "frontier" of vertices to explore. We split this frontier among available workers. For example, if level 3 has 100 vertices and we have 4 workers, each worker gets approximately 25 vertices.

**What each worker does:** Each worker takes its assigned vertices and looks up all their neighbors in the graph. The worker collects these neighbors into its own private list, checking against the global visited set to avoid duplicates.

**Where workers write:** Each worker writes to its own private temporary buffer. No two workers write to the same memory location during the parallel phase.

**Fixed-order merge:** After all workers finish exploring their vertices, we:
1. Collect all discovered neighbors from all workers
2. Sort them by vertex ID
3. Remove duplicates (keeping the first occurrence)
4. Mark them as visited in a deterministic order
5. Add them to the result list in sorted order

ASCII sketch:

    Input ▶ [Level vertices: 10, 15, 20, 25]
               │        │        │        │
            Worker1  Worker2  Worker3  Worker4
            finds:   finds:   finds:   finds:
            [30,35]  [40,30]  [45]     [50,35]
               └──────────┴────────┴────────┘
                          │
                   Sort & deduplicate
                          │
                   [30, 35, 40, 45, 50] ◄─ Next level frontier

## Why the Answer Is Always the Same

**Same split every time:** For a given graph and start vertex, the BFS levels are always the same. At each level, we process vertices in sorted order, so the work distribution is identical across runs.

**Same combine order:** Within each level, we sort discovered vertices by ID before adding them to the next frontier. This means level N+1 always contains the same vertices in the same order, regardless of which worker discovered them.

**No conflicts:** Workers only read the graph structure (immutable) and the visited set (read-only during parallel phase). Each worker writes only to its own temporary buffer. The visited set is updated only during the sequential merge phase between levels.

**Deterministic visited checks:** We check the visited set before adding vertices to the next frontier, and we process the frontier in sorted order. This ensures that if vertex A and vertex B both lead to vertex C, vertex C is always discovered from the same parent in the same level.

## Proof It Works

**Correctness parity:**
- The parallel implementation produces identical output to the sequential baseline on:
  - Edge cases: empty graph, disconnected components
  - Small graphs: 6 vertices (tree)
  - Medium graphs: 100 vertices (grid)
  - Large graphs: 10,000 vertices (grid and random)
  - Various topologies: trees, grids, stars, random graphs
- See `run_summary.txt` for detailed test results showing 100% match rate across all 8 test cases.

**Determinism:**
- Running the parallel BFS three times on the same graph produces identical results.
- Test results from `run_summary.txt`:
  - small_tree: Hash `42e0c70b319b6ed3` (all 3 runs match)
  - medium_grid: Hash `06d9691786d50e7a` (all 3 runs match)
  - large_grid: Hash `89e9d5f513430cc4` (all 3 runs match)
  - star_500: Hash `c9bd1157baa044b2` (all 3 runs match)
  - star_2000: Hash `0e7cd909e629b07f` (all 3 runs match)
  - random_1000_deg20: Hash `13a263c02bf1da17` (all 3 runs match)
- All hashes match across runs, confirming determinism.

**Performance:**
- Tested on random graphs with high average degree (where BFS has wider levels):
  - **Random graph, 5000 vertices, avg degree 20:**
    - Sequential: 115.72 ms
    - Parallel: 57.56 ms
    - Speedup: 2.01×
    - Threads: 16
    - Efficiency: 12.6%
  - **Random graph, 10000 vertices, avg degree 30:**
    - Sequential: 287.21 ms
    - Parallel: 168.95 ms
    - Speedup: 1.70×
    - Threads: 16
    - Efficiency: 10.6%
- See `perf.txt` for complete performance data.

The efficiency is moderate (10-13%) because BFS has inherent limitations:
- **Amdahl's Law:** Early and late BFS levels have few vertices, limiting parallelism
- **Graph topology:** Even random graphs have varying level widths
- **Synchronization overhead:** Level barriers prevent continuous parallel work

Grid graphs show no speedup (0.22×) because their BFS levels are very narrow (width grows as square root of distance), making thread overhead dominate.

## Limits & Safety Switches

**Small inputs:** Graphs with fewer than 100 vertices use sequential BFS. At this scale, thread creation and synchronization overhead exceeds any parallel benefit. Similarly, if a BFS level has fewer than 50 vertices, we process it sequentially.

**Resource bounds:** Rayon's thread pool is automatically bounded to the number of physical CPU cores. We never create more threads than cores, avoiding oversubscription and context-switching overhead.

**Corner cases handled:**
- Empty graph or non-existent start vertex: returns empty result immediately
- Single vertex: returns that vertex without creating threads
- Disconnected graph: correctly explores only the connected component containing the start vertex
- Self-loops and duplicate edges: handled correctly by the visited set

## How to Reproduce

**All tests (correctness, determinism, performance):**
```bash
cargo run --release
```

**Debug mode (slower but shows all output):**
```bash
cargo run
```

**Run unit tests:**
```bash
cargo test
```

The test runner automatically:
- Runs correctness tests comparing sequential vs parallel output
- Runs determinism checks with 3 parallel runs per test case
- Runs performance benchmarks on large graphs
- Writes results to `run_summary.txt` and `perf.txt`

## Alternatives We Considered

### 1. Lock-Based Shared Queue with Worker Threads

**What it would do:** Create a thread-safe queue protected by a mutex. Multiple worker threads continuously pull vertices from the queue, explore neighbors, and push new vertices back to the queue.

**Why it loses here:**
- **Non-deterministic ordering:** When multiple threads push to the queue simultaneously, the order depends on thread scheduling, which varies between runs. Even with a mutex, the interleaving of pushes is non-deterministic.
- **Lock contention:** Every queue access requires acquiring the mutex. With 16 threads all trying to push/pop frequently, we'd spend significant time waiting for locks rather than doing useful work. On the random_5000 graph, this would likely reduce speedup from 2.0× to under 1.5×.
- **Determinism risk:** To make this deterministic, we'd need to either process vertices in a fixed order (defeating the purpose of parallelism) or sort the entire result afterward (which doesn't guarantee the same BFS tree structure).

**What would make it viable:** If we only cared about finding reachable vertices (not the specific BFS order), and if the graph were sparse enough that lock contention was minimal. But BFS semantics require level-by-level ordering for correctness.

### 2. Direction-Optimizing BFS with Top-Down and Bottom-Up Phases

**What it would do:** Use top-down exploration (frontier → neighbors) for small frontiers and bottom-up exploration (unvisited → check if any neighbor in frontier) for large frontiers. This can reduce edge traversals on scale-free graphs.

**Why it loses here:**
- **Complexity vs. benefit:** This requires maintaining both a frontier set and an unvisited set, plus logic to switch between modes. For the given graph structure (HashMap of adjacency lists), bottom-up would require iterating all unvisited vertices and checking membership in the frontier set, which is expensive.
- **Determinism complexity:** Bottom-up phase processes vertices in hash table iteration order, which is non-deterministic in Rust's HashMap. We'd need to sort vertices at every phase switch, adding overhead that would likely exceed 50ms per level on large graphs.
- **Memory bandwidth:** Bottom-up phase has poor cache locality when checking frontier membership for many vertices, especially on graphs that fit in cache. Our test graphs (5000-10000 vertices) fit in L3 cache, making this approach slower.

**What would make it viable:** Very large scale-free graphs (millions of vertices) where some BFS levels contain over 10% of all vertices. The bottom-up phase shines when the frontier is huge relative to the unvisited set. Our target graphs are smaller and more uniform.

### 3. Wavefront Pattern with Atomic Visited Flags

**What it would do:** Replace the HashSet with an atomic bitset or array of atomic bools. Workers use compare-and-swap to claim vertices atomically, allowing lock-free parallel exploration without level synchronization.

**Why it loses here:**
- **Determinism risk:** Workers race to claim vertices. The order in which vertices are visited depends on which thread wins the race, varying between runs. Even if we sort the final result, the BFS tree structure (which parent discovered each vertex) would differ, violating BFS semantics.
- **Memory overhead:** The graph uses i32 vertex IDs, which could be sparse (e.g., IDs 1, 1000, 50000). An atomic array would need to cover the full range, wasting memory. A concurrent hash map is slower than level-synchronous access. For our test graphs with 10000 vertices, this would require 40KB of atomic flags vs 8KB for the HashSet.
- **False sharing:** Atomic flags in adjacent memory locations cause cache line bouncing between cores, hurting performance. We'd need careful padding (8-16 bytes per flag), multiplying memory overhead to 80-160KB. This would likely reduce speedup from 2.0× to under 1.2× due to cache thrashing.

**What would make it viable:** If determinism weren't required (e.g., just checking reachability), and if vertex IDs were dense (0 to N-1), and if we had a very large graph where level synchronization overhead dominated. None of these apply here.

### 4. Graph Partitioning with Independent Subgraph BFS

**What it would do:** Partition the graph into subgraphs, run BFS independently on each partition, then merge results. Each worker owns a partition and explores it without synchronization.

**Why it loses here:**
- **BFS semantics violation:** BFS requires exploring vertices in order of distance from the start. If we partition the graph, vertices at distance 3 in one partition might be explored before vertices at distance 2 in another partition, breaking BFS correctness. This would cause our correctness tests to fail.
- **Merge complexity:** After independent exploration, we'd need to reconcile which vertices were visited at which levels across partitions. This requires a complex merge that essentially re-does the BFS to determine correct levels, taking longer than the original BFS.
- **Partitioning overhead:** Good graph partitioning (minimizing cross-partition edges) is expensive, often taking longer than the BFS itself for graphs of this size. METIS partitioning on our 10000-vertex graph would take approximately 200-300ms, exceeding the entire BFS time.

**What would make it viable:** If we were doing multiple independent BFS traversals from different start vertices, we could partition once and reuse it. Or if we only needed approximate distances (e.g., for graph analytics where exact BFS order doesn't matter). Neither applies to this single-source BFS requirement.

---

**Word count:** ~1,850 words
