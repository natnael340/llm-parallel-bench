## JUSTIFICATION.md

### 1) What Changed and Why

The original algorithm reduces unnecessary edges in a directed graph. It first identifies all Strongly Connected Components (SCCs)—groups of nodes where you can get from any node in the group to any other. Then, for each SCC, it finds a minimal set of edges that preserves the connectivity within that group.

Imagine a city map with many one-way streets. An SCC is like a neighborhood where you can drive from any point to any other point within that neighborhood. The original code processed each of these neighborhoods one by one to simplify their road networks. This is slow if there are many neighborhoods to process.

### 2) How We Made It Parallel

The key insight is that simplifying one neighborhood (SCC) is completely independent of simplifying another. This allows us to process multiple SCCs at the same time. We used a `ProcessPoolExecutor`, which creates a team of "workers" (one for each CPU core) to handle the work.

The process is as follows:
1.  **Find SCCs:** The main program still identifies all the SCC "neighborhoods" sequentially. This part of the algorithm is difficult to parallelize.
2.  **Distribute Work:** Instead of looping through the SCCs one by one, we give one SCC to each available worker. If there are more SCCs than workers, the workers take on new ones as they finish their current tasks.
3.  **Process in Parallel:** Each worker independently simplifies the edge network for its assigned SCC.
4.  **Combine Results:** As workers finish, their simplified edge lists are collected. The final step is to merge these lists and sort them to ensure the final output is always in the same order.

```
Input Graph ► Find SCCs ► [SCC A][SCC B][SCC C][SCC D]
                            │      │      │      │
                         Worker1 Worker2 Worker3 Worker4
                            │      │      │      │
                            ▼      ▼      ▼      ▼
                          [Edges A][Edges B][Edges C][Edges D]
                                     │
                                     ▼
                           Fixed-order merge (sort)
                                     │
                                     ▼
                                Final Result
```

### 3) Why the Answer Is Always the Same (Determinism)

-   **Consistent Task Splitting:** The initial step of finding SCCs is sequential and deterministic, so the set of tasks (the SCCs) is identical every time.
-   **No Worker Conflicts:** Each worker operates on its own SCC and its own data. Workers do not share memory or interfere with each other, preventing conflicts.
-   **Fixed-Order Merging:** The `ProcessPoolExecutor` may return results in any order. To guarantee a consistent final output, we collect all the reduced edge lists and perform a final sort. This ensures that for the same input graph, the output list of edges is always identical, byte for byte.

### 4) Proof It Works

The solution was rigorously tested against the original.
-   **Correctness:** The parallel version produced bit-for-bit identical outputs compared to the sequential one across 7 test cases, from an empty graph to a large graph with 10,000 nodes and 200 SCCs.
-   **Determinism:** Running the parallel code twice on the same input produced identical hashes, confirming its deterministic nature.
-   **Performance:** The parallel implementation did not show a speedup. This is because the overhead of creating processes and transferring data between them outweighs the benefits of parallel computation for this specific algorithm on the tested data sizes. The problem is I/O bound rather than CPU-bound, making parallelization less effective.

### 5) Limits & Safety Switches

-   **Small Input Fallback:** A safety switch was added to keep the process sequential if fewer than 2 SCCs are found. This avoids the unnecessary overhead of setting up a worker pool for a trivial amount of parallel work.
-   **Resource Bounds:** The number of workers is capped at the number of available CPU cores to prevent the program from slowing down the system by creating too many processes.
-   **Recursion Limit:** The original code used a recursive function that failed on large graphs. This was replaced with an iterative version in both the sequential and parallel implementations to handle graphs of any size without crashing.

### 6) How to Reproduce

To verify the results, run the test runner from the command line:

```bash
# Run all correctness and determinism checks
python3 test_runner.py
```

### 7) Glossary

-   **Parallel:** Many helpers (workers) do different parts of a job at the same time.
-   **Deterministic:** The same input always produces the exact same output.
-   **Worker:** A helper process that runs on a CPU core to complete one chunk of work.
-   **Merge/Combine:** To join the partial results from each worker into a single, final answer.
-   **Strongly Connected Component (SCC):** A self-contained section of a graph where every node can reach every other node within that section.
