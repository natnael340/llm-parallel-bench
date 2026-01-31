
# Justification for Sequential BFS Implementation

## 0) Decision Summary
- **Baseline bottleneck:** The original sequential BFS is CPU-bound, with work centered on iterating through node neighbors and managing a queue.
- **Chosen strategy:** A parallel, level-synchronous approach was attempted using Rayon.
- **Why it is safe (determinism):** The parallel strategy sorted the neighbors at each level to ensure a consistent traversal order.
- **Why it is faster:** The hypothesis was that processing all nodes at a given level in parallel would be faster. **This hypothesis was proven incorrect.**
- **Rejected alternative:** A fully asynchronous approach was rejected due to the high complexity of ensuring deterministic output.

**Final Decision:** After multiple refinement attempts, the parallel implementation showed a significant performance *regression*. The overhead of parallelization outweighed the benefits. Therefore, the final recommendation is to **use the original sequential implementation**, as it is correct, deterministic, and faster in practice.

## 1) What Changed and Why
The goal was to parallelize a Breadth-First Search (BFS) algorithm. In simple terms, a sequential BFS explores a graph (like a social network) level by level. It starts at one node, finds all its direct friends (level 1), then finds all of their friends (level 2), and so on, without visiting the same node twice. The process uses a queue to keep track of who to visit next.

For example, starting from node A:
1.  Visit A.
2.  Find A's neighbors: B and C. Add them to the queue.
3.  Visit B, find its neighbors (D, E). Add them to the queue.
4.  Visit C, find its neighbors (F). Add it to the queue.
...and so on, until every reachable node has been visited.

## 2) How We Made It Parallel (and Why It Failed)
The chosen strategy was a **level-synchronous BFS**. The idea was to process all nodes at the same "level" (e.g., all of A's direct friends) at the same time, using multiple workers.

The process looked like this:
```
Input ▶ [Current Level: A]
                │
             Worker1 (finds B, C)
                │
           Merge & Sort Results ▶ [Next Level: B, C]
                │
      ┌─────────┴─────────┐
   Worker1 (finds D, E)  Worker2 (finds F)
      │                     │
      └──────► Merge & Sort ◄┘
```

Each worker would find the neighbors of its assigned nodes. These lists of neighbors would then be combined, sorted (to ensure the same answer every time), and filtered to create the next level.

**The Problem:** The work required to merge, sort, and filter the results from multiple workers created a new bottleneck. The cost of this coordination and data management was much higher than the time saved by exploring neighbors in parallel. After two attempts to optimize this process, the parallel version remained significantly slower than the simple, single-worker sequential version.

## 3) Why the Answer is Always the Same (Determinism)
Both the sequential and the attempted parallel versions are deterministic.
-   **Sequential:** The use of a `VecDeque` (a standard queue) ensures that nodes are always processed in the same first-in, first-out order.
-   **Parallel (Attempted):** To ensure determinism, the list of newly discovered nodes at each level was explicitly sorted. This guaranteed that the final traversal order would be identical across runs, even though the neighbors were found in parallel. This sorting step, while necessary for determinism, contributed to the performance overhead.

## 4) Proof It Works
The correctness and determinism of the attempted parallel implementation were verified by a test harness. However, the performance results showed a clear regression.

-   **Correctness & Determinism:** The `run_summary.txt` file shows that the parallel version produced the exact same output as the sequential version on all test cases (from empty graphs to large ones) and that repeated parallel runs yielded identical results.
-   **Performance:** The same summary file shows that the parallel version was consistently slower, with a speedup of less than 1.0x (e.g., 0.24x on the large test case), indicating a slowdown.

Because the parallel version was not faster, the sequential implementation is the superior choice.

## 5) Limits & Safety Switches
-   **Small Inputs:** The performance regression was present even on large inputs, so there is no threshold where the parallel version becomes beneficial.
-   **Resource Bounds:** The parallel implementation used Rayon, which manages a thread pool typically sized to the number of CPU cores, thus avoiding oversubscription.

## 6) How to Reproduce
The following commands can be used to rerun the tests and validate the findings:
1.  **Build and run the test harness:**
    ```bash
    cargo run
    ```
2.  **Verify correctness and determinism from the output:**
    Check the `run_summary.txt` file and the console output to confirm that "Correctness" and "Determinism" are marked as "PASS" for all scenarios.

## 7) Glossary
-   **Parallel:** Multiple tasks running at the same time.
-   **Deterministic:** The same input always produces the same output.
-   **Worker:** A thread of execution that performs a piece of the work.
-   **Overhead:** Extra work required to manage parallel tasks, which can sometimes slow down the program.

## 8) Alternatives We Considered
1.  **Mutex-Based `visited` Set:**
    -   **What it would do:** Use a single, shared `HashSet` protected by a lock (`Mutex`) to track visited nodes.
    -   **Why it loses here:** This was the first implementation attempt. It failed because all workers had to wait in line to acquire the lock before checking or inserting a node, creating a severe bottleneck and serializing the execution.
    -   **What would make it viable:** This approach is generally not viable for high-performance parallel algorithms due to lock contention.

2.  **Fully Asynchronous BFS:**
    -   **What it would do:** Use concurrent queues and data structures to allow workers to operate independently without waiting for levels to synchronize.
    -   **Why it loses here:** Ensuring deterministic output with this approach is extremely difficult. The order in which nodes are visited would depend on thread scheduling, leading to different results on different runs. It would also require more complex and potentially slower concurrent data structures.
    -   **What would make it viable:** If the exact traversal order was not important and only node discovery mattered, this could be a powerful (though complex) strategy.
