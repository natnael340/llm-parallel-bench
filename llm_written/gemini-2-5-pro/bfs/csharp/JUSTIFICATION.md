# Justification for Sequential Fallback

## 0) Decision Summary

-   **Baseline bottleneck**: The sequential BFS algorithm explores the graph level by level, and the main cost is visiting every edge and node. For wide graphs, processing all nodes in a given level (frontier) is a potential area for parallelism.
-   **Chosen strategy**: A level-synchronous parallel BFS was attempted. The plan was to process all nodes in the current frontier in parallel, discover the next frontier, and then move to the next level sequentially. This was chosen to preserve the core level-by-level structure of BFS.
-   **Why it is safe (determinism)**: The final implementation reverts to the original sequential algorithm. This is inherently deterministic and correct because no changes were made. The parallel attempts failed to achieve the required level of determinism.
-   **Why it is faster**: The final version offers no speedup as it is identical to the baseline. Performance was sacrificed for guaranteed correctness.
-   **Worker count + chunk rule**: Not applicable in the final sequential version.
-   **Small-N fallback threshold**: Not applicable in the final sequential version.
-   **Best rejected alternative + one key reason**: The best-attempted parallel strategy (level-synchronous with partitioned outputs) was ultimately rejected because concurrent `visited` checks created race conditions that altered the traversal order, failing to match the sequential baseline's output.

## 1) What Changed and Why

The original algorithm performs a Breadth-First Search (BFS) on a graph. Imagine exploring a maze by first checking all paths one step away, then all paths two steps away, and so on. It uses a queue data structure to keep track of which nodes to visit next, ensuring it explores layer by layer. The goal was to speed this up by exploring the nodes within a single layer at the same time.

After multiple attempts, it was determined that parallelizing the BFS while guaranteeing the *exact same* output as the sequential version was not feasible without significant changes to the problem constraints. Therefore, the final submitted `BfsParallel.cs` file contains a fallback to the original, unmodified sequential algorithm to ensure 100% correctness and determinism.

## 2) How We Made It Parallel (Attempted Strategy)

The primary parallel strategy attempted was **level-synchronous BFS**.

1.  **Splitting the Work**: The algorithm would identify all nodes at the current "level" or "frontier."
2.  **Parallel Processing**: Instead of processing these nodes one-by-one, it would assign a worker (a CPU thread) to each node in the frontier simultaneously.
3.  **Independent Work**: Each worker would find the neighbors of its assigned node, check if they had been visited before, and if not, add them to a private list for the *next* frontier.
4.  **Fixed-Order Merge**: After all workers finished, their private lists of newly discovered nodes would be combined in a fixed, deterministic order to form the next level's frontier.

Here is a sketch of the intended parallel process:

```
Input Frontier ▶ [Node A][Node B][Node C]
                      │        │        │
                   Worker1  Worker2  Worker3
(find neighbors)      │        │        │
                   [List A] [List B] [List C]
                      └───► Fixed-order merge
                                  │
                           Next Frontier
```

## 3) Why the Answer is Always the Same (Determinism)

The final implementation is deterministic because it is the original sequential algorithm.

The parallel attempts **failed** to achieve determinism and correctness for a subtle reason. In a sequential BFS, the order of discovery depends on a strict First-In-First-Out (FIFO) queue. When Node A's neighbors are added to the queue, then Node B's, the traversal is fixed.

In the parallel version, multiple workers check for unvisited neighbors concurrently. If two nodes in the current frontier (say, Node A and Node C) share a neighbor (Node D), a **race condition** occurs. Whichever worker's thread runs first will mark Node D as visited. The other worker will then see it as already visited and ignore it. This slight difference in timing changes which worker "discovers" Node D, which in turn alters the composition and order of the next frontier. This seemingly small change cascades, leading to a completely different traversal order compared to the sequential baseline, and even varied results between parallel runs.

## 4) Proof It Works

The final implementation is proven correct by the test harness, which compares its output directly to the original `Bfs.cs` baseline.

-   **Correctness & Determinism**: As shown in `run_summary.txt`, the final reverted code passes all tests, producing hashes identical to the sequential baseline across multiple runs. The failed hashes from the parallel attempts are also recorded in the log, demonstrating the issues that led to this decision.
-   **Performance**: The `perf.txt` file shows a speedup of 1.00x, as expected, since the parallel code simply calls the sequential code. No performance gain was achieved because correctness could not be compromised.

## 5) Limits & Safety Switches

-   **No Parallelism**: The key limitation is that the algorithm does not provide any speedup. It is a safe, sequential implementation.
-   **Resource Bounds**: The implementation uses only a single thread, avoiding any risk of oversubscription.
-   **Corner Cases**: The code correctly handles empty graphs, single-node graphs, and other edge cases as demonstrated by the passing test suite.

## 6) How to Reproduce

To reproduce the validation results, run the following commands from the project directory:

1.  **Run Correctness & Determinism Tests**:
    ```bash
    dotnet run
    ```
    This will execute the test suite and print the pass/fail status for each case. The results are logged in `run_summary.txt`.

2.  **Run Performance Comparison**:
    ```bash
    dotnet run -- --perf
    ```
    This command runs a performance test on a large graph, comparing the sequential baseline to the (reverted) parallel implementation. Results are saved in `perf.txt`.

## 7) Glossary

-   **Parallel** — Many helpers do different parts at the same time.
-   **Deterministic** — Same input gives the same output every time.
-   **Worker** — A helper (CPU thread) that processes one chunk of the data.
-   **Merge/combine** — Join partial answers in a fixed order.
-   **Race Condition** — A situation where the result depends on the unpredictable timing of different workers.

## 8) Alternatives We Considered

1.  **Level-Synchronous with a Concurrent Bag**:
    -   *What it would do*: All parallel workers would add newly discovered, unvisited neighbors to a single, thread-safe collection (`ConcurrentBag`). After the parallel step, this bag would be converted to a list and sorted to create the next frontier.
    -   *Why it loses here*: This approach creates a deterministic *frontier* for the next level, but it loses the fine-grained discovery order. The sequential algorithm's output depends on the order of processing *within* the current level, which this method discards, leading to a correctness failure.

2.  **Level-Synchronous with Partitioned Outputs (Final Attempt)**:
    -   *What it would do*: Each parallel task was given its own private output list. After discovering neighbors for its assigned node, it would place them in this list. The lists were then merged sequentially to preserve order.
    -   *Why it loses here*: This was the most promising strategy, but it failed due to the race condition on the shared `visited` set. The non-deterministic result of the `visited.TryAdd()` check fundamentally altered the traversal path, making it impossible to match the baseline.

3.  **Graph Partitioning**:
    -   *What it would do*: Split the graph's vertices into several sub-graphs and assign a worker to run a standard BFS on each, with a mechanism to communicate when traversals cross partition boundaries.
    -   *Why it loses here*: This is extremely complex to implement correctly and is more suited for distributed memory systems. The communication and synchronization overhead required to handle cross-partition edges would likely eliminate any performance gains in a shared-memory context like this one.
