# Parallel BFS Implementation Justification

## Decision Summary

**Baseline bottleneck:** Sequential queue processing visits one vertex at a time, limiting throughput on graphs with wide levels.

**Chosen strategy:** Level-synchronous parallel BFS with two-phase neighbor discovery.

**Why it is safe (determinism):** Each level is processed completely before the next. Within a level, vertices are processed in their discovery order. The visited set is updated sequentially in a fixed order, ensuring the same vertices are discovered in the same order every time.

**Why it is faster:** Multiple vertices within the same BFS level can discover their neighbors in parallel, reducing the time to explore wide levels.

**Worker count + chunk rule:** Uses all available CPU cores (bounded by Runtime.getRuntime().availableProcessors()). Each vertex in the current level is assigned to a worker via parallel stream.

**Small-N fallback threshold:** Graphs with fewer than 100 vertices use the sequential algorithm to avoid thread overhead.

**Best rejected alternative:** Fully asynchronous BFS with concurrent queue. Rejected because it produces non-deterministic visit order and cannot match the sequential baseline output exactly.

## What Changed and Why

The original sequential BFS works like standing in line at a ticket counter. You start with one person (the start vertex). That person tells you about their friends (neighbors), and you add those friends to the end of the line. Then you process the next person in line, add their friends, and so on. Everyone gets processed in the exact order they joined the line.

Here's a tiny example with 8 people in a social network:

```
Person 0 knows: 1, 2
Person 1 knows: 0, 3, 4
Person 2 knows: 0, 5
Person 3 knows: 1
Person 4 knows: 1, 6
Person 5 knows: 2, 7
Person 6 knows: 4
Person 7 knows: 5
```

Starting from Person 0, the sequential process visits them in this order:
- Level 0: [0]
- Level 1: [1, 2] (discovered from 0)
- Level 2: [3, 4, 5] (discovered from 1, then 2)
- Level 3: [6, 7] (discovered from 4, then 5)

Final visit order: 0, 1, 2, 3, 4, 5, 6, 7

The sequential version is slow because it processes one person at a time, even when multiple people could be interviewed simultaneously.

## How We Made It Parallel

We changed the process to work in rounds (levels). In each round, we interview everyone from the previous round at the same time, but we carefully track who they mention in the exact order they mention them.

**Input split:** The current BFS level (all vertices at the same distance from the start) is the input. Each vertex in this level is assigned to a worker thread.

**What each worker does:** Each worker looks up the neighbors of its assigned vertex and collects them into a private list. Workers do not modify any shared data during this phase.

**Where workers write:** Each worker writes to its own private list (one list per vertex in the current level). These lists are stored in a fixed-size array, so worker 0 writes to position 0, worker 1 to position 1, and so on.

**Fixed-order merge:** After all workers finish collecting neighbors, we process the private lists sequentially in the same order as the vertices in the current level. For each neighbor in each list, we check if it has been visited. If not, we mark it as visited and add it to the next level. This sequential merge ensures the exact same discovery order as the sequential version.

Here's the process visualized:

```
Current Level ▶ [Vertex A][Vertex B][Vertex C]
                     │         │         │
                  Worker1   Worker2   Worker3
                     │         │         │
                  [A's      [B's      [C's
                neighbors] neighbors] neighbors]
                     └─────────┼─────────┘
                               ▼
                    Fixed-order sequential merge
                    (A's neighbors, then B's, then C's)
                               ▼
                          Next Level
```

## Why the Answer Is Always the Same

**Same split every time:** For a given graph and start vertex, the BFS levels are always the same. The first level is always just the start vertex. The second level is always the neighbors of the start vertex in the order they appear in the graph's neighbor list. And so on.

**Same combine order:** After workers collect neighbors in parallel, we always process them in the same order: first all neighbors from the first vertex in the current level, then all neighbors from the second vertex, and so on. This matches exactly how the sequential version would discover them.

**No conflicts:** Each worker only reads from the graph (which never changes) and writes to its own private list. The only shared data structure is the visited set, but we only update it during the sequential merge phase, not during parallel discovery. This means workers never interfere with each other.

**Deterministic visited checks:** During the sequential merge, we check and update the visited set in a fixed order for each run. If vertex A's neighbor list is [3, 5, 7], we always check 3 first, then 5, then 7. If 3 was already visited by an earlier vertex, we skip it. This happens the same way every time.

## Proof It Works

**Correctness parity:** The parallel implementation produces exactly the same output as the sequential baseline on all test cases, from empty graphs to graphs with 10,000 vertices and 50,000 edges. See run_summary.txt for the complete list of 12 test cases, all of which passed.

**Determinism:** We ran the parallel version three times on each test case and computed a hash of the output. All three runs produced identical hashes. For example, on the random graph with 1,000 vertices and 5,000 edges:
- Run 1 hash: 91bd93709037176a
- Run 2 hash: 91bd93709037176a
- Run 3 hash: 91bd93709037176a
- Sequential hash: 91bd93709037176a

All test results are documented in run_summary.txt.

**Performance:** We tested on graphs with up to 40,000 vertices. The largest random graph (10,000 vertices, 50,000 edges) achieved a speedup of 2.14x on a 16-core system. Grid graphs showed poor speedup due to their shallow BFS trees (many levels with few vertices each), which limits parallelism. See perf.txt for detailed timing results.

## Limits and Safety Switches

**Small inputs:** Graphs with fewer than 100 vertices are processed sequentially. Below this threshold, the overhead of creating threads and managing parallel streams outweighs any benefit. The sequential version is faster for small graphs.

**Resource bounds:** The parallel implementation uses a ForkJoinPool bounded to the number of available processors (Runtime.getRuntime().availableProcessors()). This prevents oversubscription and ensures we don't create more threads than the system can efficiently handle.

**Corner cases handled:**
- Empty graph: Returns empty list (no vertices to visit)
- Invalid start vertex: Returns empty list (vertex not in graph)
- Single vertex: Returns list with just that vertex
- Disconnected graph: Only visits vertices reachable from start
- Very small levels (fewer than 4 vertices): Processed sequentially to avoid parallel overhead

## How to Reproduce

**Rerun correctness and determinism tests:**
```
javac Graph.java BfsSequential.java BfsParallel.java TestBfs.java
java TestBfs
```

**Rerun performance tests:**
```
javac Graph.java BfsSequential.java BfsParallel.java PerfBfs.java
java PerfBfs
```

**Check test summary:**
```
cat run_summary.txt
```

**Check performance results:**
```
cat perf.txt
```

## Alternatives We Considered

### 1. Fully Asynchronous BFS with Concurrent Queue

**What it would do:** Use a thread-safe concurrent queue (like ConcurrentLinkedQueue) and let multiple threads pull vertices from the queue and add newly discovered neighbors back to it without any synchronization barriers between levels.

**Why it loses here:** BFS visit order depends on the exact sequence in which vertices are discovered. With a concurrent queue, the order depends on thread scheduling, which is non-deterministic. Thread 1 might discover vertex 5 before Thread 2 discovers vertex 3, or vice versa, depending on CPU load and OS scheduling. This means the output would differ from the sequential baseline and could change between runs. We need exact output matching for correctness verification.

**What would make it viable:** If the requirement were only to visit all reachable vertices (not to match the exact sequential order), this approach would work and could be faster. It's suitable for applications like connected component detection where order doesn't matter.

### 2. Direction-Optimizing BFS (Top-Down and Bottom-Up)

**What it would do:** Switch between two strategies based on the frontier size. When the frontier (current level) is small, use top-down exploration (like our approach). When the frontier is large (more than half the graph), switch to bottom-up: for each unvisited vertex, check if any of its neighbors are in the frontier.

**Why it loses here:** This requires significant changes to the Graph data structure. The current Graph only stores outgoing edges (neighbors of each vertex). Bottom-up BFS needs incoming edges (which vertices point to each vertex). Adding this would require modifying Graph.java to maintain a reverse adjacency list, which violates the constraint to preserve the existing API. It would also require more than 250 lines of code changes across multiple files.

**What would make it viable:** If we could modify the Graph class to store both forward and backward edges, and if the graphs were very large (millions of vertices) with highly variable level sizes, this could provide 2-5x better performance on scale-free graphs.

### 3. Graph Partitioning with Independent Subgraph BFS

**What it would do:** Divide the graph into multiple partitions (subgraphs) and run BFS on each partition in parallel. Merge results at partition boundaries.

**Why it loses here:** BFS is inherently sequential across levels. Even if we partition the graph, we still need to synchronize at each level to ensure correct distances. The partitioning overhead (computing a good partition, managing boundary vertices, merging partial results) is substantial. For the graph sizes we tested (up to 40,000 vertices), this overhead would dominate any parallel benefit. Additionally, ensuring deterministic visit order across partition boundaries would require complex coordination logic.

**What would make it viable:** For massive graphs (tens of millions of vertices) that don't fit in memory, partitioning becomes necessary. Distributed BFS systems like Pregel or GraphLab use this approach, but they accept approximate results or relaxed ordering guarantees.

### 4. Wavefront Pattern with Task Graph

**What it would do:** Model the BFS as a task dependency graph where each vertex's processing depends on its parent being processed. Use a work-stealing task scheduler to execute independent tasks (vertices at the same level) in parallel.

**Why it loses here:** This adds significant complexity (200+ lines of task management code) for minimal benefit over our simpler level-synchronous approach. The task creation overhead (one task per vertex per level) would be high. For BFS, the level-synchronous pattern is simpler and achieves the same parallelism: all vertices at the same level are independent and can be processed in parallel. The task graph approach is better suited for irregular computations where dependencies don't align neatly into levels.

**What would make it viable:** For algorithms with complex, irregular dependencies (like iterative graph algorithms where convergence is non-uniform), a task graph can expose more parallelism than level-synchronous execution. But BFS has a regular, level-based structure that doesn't benefit from this complexity.
