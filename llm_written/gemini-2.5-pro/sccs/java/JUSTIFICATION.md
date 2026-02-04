# Justification for Parallelizing the Graph Edge Reduction Algorithm

## 1. Decision Summary

- **Baseline Bottleneck:** The original code processed each Strongly Connected Component (SCC) one by one. For graphs with many SCCs, this was a missed opportunity for parallel work.
- **Chosen Strategy:** We used a fixed-size thread pool (`ExecutorService`) to process multiple SCCs at the same time. Each SCC gets its own task.
- **Why it is Safe (Determinism):** The work on each SCC is completely independent. We sort the list of SCCs before starting to guarantee that the final list of edges is assembled in the same order every time.
- **Why it is Faster:** While one thread is working on a complex SCC, other threads can work on different SCCs. This keeps all CPU cores busy.
- **Worker Count + Chunk Rule:** We use a thread pool with a size equal to the number of available CPU cores. Each task consists of processing one entire SCC.
- **Small-N Fallback Threshold:** No specific threshold was set. The overhead of creating tasks is small, so even small graphs can benefit. For graphs with very few SCCs, the performance will be similar to the sequential version.
- **Best Rejected Alternative:** Using `parallelStream()` was considered and initially implemented. However, it did not guarantee the order of the final combined list of edges, which made it non-deterministic. The `ExecutorService` approach gives us full control over the order.

## 2. What Changed and Why

The original program finds groups of connected nodes in a graph called Strongly Connected Components (SCCs). Imagine a city map with one-way streets. An SCC is a neighborhood where you can get from any point to any other point by following the streets.

After finding these neighborhoods, the program simplifies the map by removing redundant streets while keeping the neighborhood connected. The original code did this one neighborhood at a time.

For example, if the map had three neighborhoods (A, B, C), the process was:
1. Simplify neighborhood A.
2. Then, simplify neighborhood B.
3. Finally, simplify neighborhood C.

This is slow if neighborhood A is very large and complex, as the computer has to wait for it to finish before starting on B.

## 3. How We Made It Parallel

We changed the process to work on all neighborhoods at once. Instead of a single worker, we now have a team of workers (one for each CPU core).

1.  **Splitting the Work:** The list of all neighborhoods (SCCs) is the work pile. We give one neighborhood to each available worker.
2.  **Independent Work:** Each worker simplifies its assigned neighborhood. They don't need to talk to each other or share any information.
3.  **Writing Outputs:** Each worker produces a simplified list of streets for its neighborhood.
4.  **Combining Results:** After all workers are done, we collect their lists of streets and combine them. To make sure the final map is the same every time, we always combine the lists in a fixed order (e.g., always A, then B, then C).

Here is a sketch of the process:

     Input (List of SCCs) ▶ [SCC A][SCC B][SCC C]
                                │        │        │
                             Worker1  Worker2  Worker3
                                └───► Fixed-order merge ◄───┘

## 4. Why the Answer is Always the Same (Determinism)

Determinism is crucial. We guarantee the same output for the same input in two ways:

1.  **Fixed Task Order:** Before we start, we sort the list of SCCs. This ensures that we always process them in the same sequence. For example, SCCs are sorted based on their smallest node ID.
2.  **Fixed Combine Order:** We collect the results from the workers in the same order we assigned them. This means the final list of edges is always assembled identically.

Because the work on each SCC is independent and the final assembly is ordered, there are no race conditions or opportunities for the output to change between runs.

## 5. Proof It Works

We built a test program (`TestGraph.java`) to prove that the new parallel version is correct and deterministic.

-   **Correctness Parity:** The test program compares the output of the new parallel version with the original sequential version for several graphs (empty, small, medium, and large). The results are identical, which is confirmed by comparing a SHA-256 hash of the final edge lists. You can see the results in `run_summary.txt`.
-   **Determinism:** The test runs the parallel version three times on the same input and checks that the output hash is identical each time. This proves that the output is stable.
-   **Performance:** For a large graph with 1,000 nodes and 5,000 edges, the parallel version shows a speedup. The exact numbers are in `perf.txt`.

## 6. Limits & Safety Switches

-   **Small Inputs:** For graphs with only one or a few SCCs, the parallel version will not be much faster than the sequential one, but the overhead is minimal. We don't need a special check to run sequentially.
-   **Resource Bounds:** The number of threads is capped at the number of available CPU cores. This prevents the program from creating too many threads, which would slow down the computer.
-   **Corner Cases:** The code handles empty graphs, graphs with no edges, and graphs with a single node correctly.

## 7. How to Reproduce

To run the tests yourself, you can use the following commands:

1.  **Compile the code:**
    ```bash
    javac Graph.java Graph_parallel.java TestGraph.java
    ```

2.  **Run the correctness and determinism tests:**
    ```bash
    java TestGraph
    ```

3.  **Check the output:**
    The program will print the results to the console and create `run_summary.txt` and `perf.txt`.

## 8. Alternatives We Considered

-   **`parallelStream()`:** This was our first choice. It is a simple way to parallelize collections in Java.
    -   **Why it lost here:** `parallelStream().flatMap().collect()` does not guarantee the order of elements in the final collection. This made the output non-deterministic, which was a critical requirement. While there are ways to enforce order, they are more complex and less explicit than the `ExecutorService` approach.

-   **Custom ForkJoinPool:** We could have used a `ForkJoinPool` directly to have more control over the tasks.
    -   **Why it lost here:** For this problem, the work is already naturally split into independent chunks (the SCCs). A simple `ExecutorService` with a fixed thread pool is easier to understand and implement, and it provides the same performance benefits for this specific workload.

-   **Parallelizing Tarjan's Algorithm:** We considered parallelizing the SCC-finding algorithm itself.
    -   **Why it lost here:** Tarjan's algorithm is inherently sequential due to its reliance on a depth-first search traversal. Parallelizing it is a major research topic and would require a much more complex and invasive code change, likely beyond the scope of this task. The current approach of parallelizing the work *after* finding the SCCs is a much more practical and safer strategy.
