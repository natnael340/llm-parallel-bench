# Parallel BFS Implementation Justification

## Decision Summary

- **Baseline bottleneck:** The sequential BFS processes one node at a time, making it slow for large, dense graphs where many nodes could be explored simultaneously.
- **Chosen strategy:** A level-synchronous parallel BFS using Java's parallel streams and a `ForkJoinPool`.
- **Why it is safe (determinism):** Each level's newly discovered nodes are collected and then explicitly sorted before being added to the final result and forming the next frontier. This fixed ordering ensures the traversal is identical on every run.
- **Why it is faster:** It processes all nodes in the current frontier concurrently, exploring their neighbors in parallel. This significantly speeds up the discovery process on multi-core systems.
- **Worker count + chunk rule:** The implementation uses a `ForkJoinPool` with a parallelism level equal to the number of available processor cores. The work is automatically chunked by the parallel stream implementation.
- **Small-N fallback threshold:** For graphs with fewer than 1,000 vertices, the algorithm falls back to the original sequential implementation to avoid parallel overhead on small inputs.
- **Best rejected alternative + one key reason:** A task-based approach using `CompletableFuture` for each node was rejected because managing the dependencies and ensuring a deterministic result order would have introduced significant complexity and overhead, outweighing the benefits.

## 1) What Changed and Why

The original algorithm performs a Breadth-First Search (BFS) on a graph. Imagine exploring a maze by first checking all paths one step away, then all paths two steps away, and so on. The sequential code does this one step at a time, which can be slow if there are many paths to check at the same level. For a small example, if a starting node `A` is connected to `B`, `C`, and `D`, the original code would visit `B`, then `C`, then `D` in a fixed sequence.

## 2) How We Made It Parallel

We adopted a "level-synchronous" approach. Instead of processing one node at a time, we process all nodes at the current "level" or "frontier" simultaneously.

- **Split:** The set of nodes to visit at the current level (the frontier) is the input that gets split.
- **Work:** Each worker takes a subset of nodes from the frontier and finds all their unvisited neighbors.
- **Combine:** The neighbors found by all workers are collected into a single list. To ensure the final result is always the same, we sort this list of newly discovered nodes. This sorted list becomes the frontier for the next level.

Here is a sketch of the process:

```
Input (Current Frontier) ▶ [Node A][Node B][Node C]
                              │        │        │
                           Worker1  Worker2  Worker3
(Find unvisited neighbors)    │        │        │
                              ▼        ▼        ▼
Partial Results          ▶ [E, F]   [G]      [H, I]
                              │        │        │
                              └─► Collect & Sort ◄───┘
                                        │
                                        ▼
Output (Next Frontier)   ▶ [E, F, G, H, I]
```

## 3) Why the Answer Is Always the Same (Determinism)

Determinism is crucial. We guarantee it in two ways:

1.  **Thread-Safe Data Structures:** We use `ConcurrentHashMap.newKeySet()` for the `visited` set, which allows multiple workers to safely mark nodes as visited without interfering with each other.
2.  **Fixed Combine Order:** The most important step for determinism is that after all workers find the next set of neighbors in parallel, we collect them into a single list and sort it. This ensures that the traversal order is the same in every run, regardless of which worker finished first.

## 4) Proof It Works

The solution was rigorously tested to ensure it is correct, deterministic, and faster.

- **Correctness:** The parallel implementation's output was compared against the original sequential version on graphs of various sizes. The results were identical, as documented in `run_summary.txt`.
- **Determinism:** The parallel code was run three times on the same input graph. The SHA-256 hash of each output list was identical, proving that the output is the same every time. The hashes are recorded in `run_summary.txt`.
- **Performance:** On a test with a 50,000-vertex graph, the parallel version achieved a **1.95x speedup** over the sequential baseline, as detailed in `perf.txt`.

## 5) Limits & Safety Switches

- **Small Inputs:** For graphs with fewer than 1,000 vertices, the overhead of creating and managing threads can make the parallel version slower. A check is in place to route these small inputs to the original sequential algorithm.
- **Resource Bounds:** The number of worker threads is capped at the number of available CPU cores to prevent oversubscription and ensure efficient resource usage.
- **Corner Cases:** The code handles empty graphs and disconnected components correctly.

## 6) How to Reproduce

To compile and run the tests, use the following commands:

```bash
# Compile all Java files
javac Bfs.java BfsParallel.java Graph.java TestBfs.java

# Run correctness test (compares parallel vs. sequential)
java TestBfs correctness 20000

# Run determinism test (compares three parallel runs)
java TestBfs determinism 20000

# Run performance test
java TestBfs performance 50000
```

## 7) Glossary

- **Parallel:** Many helpers do different parts of the work at the same time.
- **Deterministic:** The same input gives the same output every time.
- **Worker:** A helper (in this case, a thread) that processes one chunk of the data.
- **Merge/Combine:** Join partial answers from workers into a final result.
- **Frontier:** The set of nodes at the current level of the search.

## 8) Alternatives We Considered

1.  **Parallelizing the Inner Neighbor Loop:**
    - _What it would do:_ For each node, process its list of neighbors in parallel.
    - _Why it loses here:_ This is too fine-grained. The overhead of creating parallel tasks for each node's small neighbor list would be much greater than the work being done, leading to poor performance.
    - _What would make it viable:_ If graphs were extremely dense, with individual nodes having millions of neighbors, this could be effective.

2.  **Task-Based Parallelism with `CompletableFuture`:**
    - _What it would do:_ Create an asynchronous task for exploring each node.
    - _Why it loses here:_ This approach makes it very difficult to maintain the level-by-level structure of BFS and to guarantee a deterministic output order without significant synchronization overhead (e.g., waiting for all tasks in a level to complete and then sorting).
    - _What would make it viable:_ If the problem did not require a strict level-by-level traversal and a non-deterministic but valid traversal was acceptable.

3.  **Graph Partitioning:**
    - _What it would do:_ Split the graph itself into subgraphs and assign each to a worker.
    - _Why it loses here:_ This is highly complex to implement correctly. It requires a sophisticated partitioning algorithm and careful management of communication between workers for nodes on the boundaries of partitions. The overhead and complexity are not justified for this problem.
    - _What would make it viable:_ For extremely large graphs that do not fit into the memory of a single machine (distributed systems), this is the standard approach.
