# Justification for Parallel Graph Edge Reduction

This document explains the parallelization of a C++ algorithm that minimizes the number of edges required to maintain the connectivity of a directed graph.

### 1. What Changed and Why

The original algorithm works in two main phases:
1.  **Find Components**: It first identifies all the "Strongly Connected Components" (SCCs) in the graph. An SCC is a group of nodes where you can get from any node in the group to any other node in that same group. The original code uses Tarjan's algorithm, which is inherently sequential, to find these.
2.  **Reduce Edges in Each Component**: For each SCC found, it calculates a minimal set of edges that preserves the connectivity within that component. This is done by building two spanning trees (a forward and a reverse one) and combining their edges.

The key insight is that the edge reduction for one SCC is completely independent of the reduction for any other SCC. This makes the second phase an ideal candidate for parallelization. We can process multiple SCCs at the same time.

For example, if a graph has three large SCCs (A, B, and C), the sequential version would process A, then B, then C. The parallel version can process A, B, and C all at once, each with a different helper.

### 2. How We Made It Parallel

The parallelization strategy focuses on the `ReduceEdges` function, which orchestrates the work.

1.  **Find SCCs (Sequential)**: We kept the first phase, finding all SCCs, sequential. Tarjan's algorithm is complex to parallelize correctly and is usually fast enough.
2.  **Distribute Work**: The list of all identified SCCs is then processed in parallel. We use OpenMP to create a team of worker threads. The list of SCCs is divided among these workers.
3.  **Process Chunks**: Each worker takes its assigned SCCs and performs the edge minimization calculation (`MinimizeEdgesInSCC`) independently. The results (the essential edges for each SCC) are stored in a private, per-worker list.
4.  **Combine Results**: After all workers have finished, their individual lists of essential edges are combined into one final list. This final merge is done in a thread-safe manner.

Here is a simple sketch of the process:

```
List of SCCs ▶ [SCC A][SCC B][SCC C][SCC D]
                    │        │        │        │
                 Worker1  Worker2  Worker3  Worker4
(MinimizeEdges)     │        │        │        │
                 [EdgesA] [EdgesB] [EdgesC] [EdgesD]
                    └────────► Thread-safe merge ◄────────┘
                                      │
                                Final Edge List
```

### 3. Why the Answer Is Always the Same (Determinism)

Determinism is guaranteed through several mechanisms:

*   **Independent Tasks**: The work for each SCC is self-contained. Workers do not share memory or communicate with each other during the computation phase, which prevents race conditions.
*   **Private Storage**: Each worker accumulates its results into a thread-local list. This avoids conflicts that would arise from multiple threads writing to a single shared list simultaneously.
*   **Controlled Merge**: The merging of these private lists into the final result list is done inside an OpenMP `critical` section, ensuring that only one thread can write to the final list at a time.
*   **Final Sort**: To ensure the final output is identical across runs regardless of the order in which threads finish, the final combined list of edges is sorted. This guarantees a consistent, deterministic output.

### 4. Proof It Works

The correctness and determinism of the parallel implementation were rigorously verified against the original sequential version.

*   **Correctness**: The test harness compared the output of the parallel version with the sequential one across various graph sizes, from empty graphs to large ones with 10,000 nodes and 150,000 edges. All tests passed, confirming the results are identical. See `evidence/run_summary.txt` for details.
*   **Determinism**: Each parallel run was executed twice, and the hash of the output was compared. The hashes were identical in all test cases, proving that the parallel algorithm produces the same result every time. The matching hashes are recorded in `evidence/run_summary.txt`.
*   **Performance**: On the "Large" test case, the parallel version showed a speedup, demonstrating its efficiency. The performance details are logged in `evidence/perf.txt`. For smaller graphs, the overhead of creating threads can make the parallel version slightly slower, which is expected.

### 5. Limits & Safety Switches

*   **Small Input Fallback**: A sequential fallback is implemented. If the number of SCCs found is less than 100, the algorithm will not use parallel processing. This avoids the overhead of thread management for small workloads where it would not be beneficial.
*   **Resource Bounds**: The number of worker threads is managed by OpenMP and is typically capped at the number of available CPU cores, preventing the program from creating an excessive number of threads and overloading the system.
*   **Edge Cases**: The implementation correctly handles edge cases such as empty graphs, graphs with a single node, and graphs with no edges, as verified by the test suite.

### 6. How to Reproduce

To compile and run the tests, use the following commands:

```bash
# Compile the test runner with OpenMP support
g++ -O3 -fopenmp test_runner.cpp -o test_runner

# Run the differential, determinism, and performance tests
./test_runner
```

The results will be printed to the console, and detailed evidence will be saved to the `evidence/` directory.

### 7. Glossary

*   **Parallel**: Performing multiple tasks at the same time.
*   **Deterministic**: Giving the same output for the same input, every single time.
*   **Worker**: A thread that processes a chunk of the data.
*   **Merge/Combine**: Joining partial results from different workers into a single final result.
*   **Strongly Connected Component (SCC)**: A part of a graph where every node can reach every other node within that part.
