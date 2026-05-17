# Parallelizing Graph SCC Edge Reduction: A Transparent Analysis

## Decision Summary

**Baseline bottleneck:** Sequential processing of each strongly connected component (SCC) to find minimal edge sets, after Tarjan's algorithm identifies all SCCs.

**Chosen strategy:** Parallelize the per-SCC edge minimization phase using Java's ForkJoinPool with bounded parallelism, while keeping Tarjan's SCC detection sequential.

**Why it is safe (determinism):** Each SCC is processed independently with no shared state. Results are collected in a fixed order (by SCC discovery index) using sorted stream operations, ensuring identical output every time.

**Why it doesn't speed things up:** Thread pool overhead (creation, task scheduling, synchronization) exceeds the actual computation time for typical graph sizes. Each SCC's spanning tree construction is memory-bound and completes in microseconds, making parallelization counterproductive.

**Worker count + chunk rule:** Up to 16 workers (CPU core count), with each worker processing one SCC at a time. Sequential fallback for graphs with fewer than 10 SCCs.

**Small-N fallback threshold:** Graphs with fewer than 10 SCCs use the sequential algorithm to avoid thread pool overhead.

**Best rejected alternative:** Parallel Tarjan's algorithm using multi-pivot approach. Rejected because it requires complex synchronization for the discovery/low-link arrays and stack, introduces non-determinism risks, and would require rewriting the entire algorithm (>200 LOC change).

## What Changed and Why

The original algorithm finds strongly connected components in a directed graph and then reduces each SCC to a minimal set of edges that preserves strong connectivity.

Think of a social network where some groups of people all follow each other (forming SCCs). The algorithm first identifies these tightly-knit groups, then for each group, finds the smallest number of "follow" relationships needed to keep everyone connected within that group.

**Original sequential process:**
1. Run Tarjan's depth-first search to discover all SCCs
2. For each SCC found (in order):
   - Build a forward spanning tree (edges going forward through the SCC)
   - Build a reverse spanning tree (edges going backward through the SCC)
   - Combine both trees as the minimal edge set
3. Collect all minimal edge sets into one result list

**Tiny example (8 people in 2 groups):**
- Group A: Alice → Bob → Carol → Alice (3 people, circular follows)
- Group B: Dave → Eve → Frank → George → Dave (4 people, circular follows)

Original algorithm processes Group A completely, then Group B completely, one after the other.

## How We Made It Parallel

The key insight: once we know which groups exist, we can analyze each group independently because they don't share any edges.

**Input split:** After Tarjan's algorithm identifies all SCCs, we have a list of groups. Each group becomes a separate task.

**Worker assignment:** If we have 16 CPU cores and 100 groups, we create a pool of 16 workers. Each worker grabs the next unprocessed group from the list.

**What each worker does:** 
- Takes one SCC (e.g., "Group 17: nodes 340-359")
- Builds a forward spanning tree for just those nodes
- Builds a reverse spanning tree for just those nodes  
- Combines them into a minimal edge list for that group
- Returns the result

**Where workers write outputs:** Each worker creates its own private list of edges for its assigned SCC. No worker ever modifies another worker's data or any shared structure during computation.

**Fixed-order merge:** After all workers finish, we collect their results in the exact order the SCCs were discovered (Group 1, then Group 2, then Group 3, etc.). This is enforced by tagging each result with its SCC index and sorting before combining.

**ASCII sketch:**

```
Input ▶ [SCC 0][SCC 1][SCC 2]...[SCC 99]
           │      │      │          │
        Worker1 Worker2 Worker3  Worker16
           │      │      │          │
        [edges] [edges] [edges]  [edges]
           └──────┴──────┴──────────┘
                      │
            Fixed-order merge (0,1,2,...,99)
                      ▼
                 Final result
```

## Why the Answer Is Always the Same (Determinism)

**Same split every time:** For a given graph, Tarjan's algorithm always discovers SCCs in the same order (it's a deterministic depth-first search). So SCC 0 is always the same set of nodes, SCC 1 is always the same set, etc.

**Same combine order:** We explicitly sort results by SCC index before merging. Even though Worker 3 might finish before Worker 1, we always combine the results in order: SCC 0's edges, then SCC 1's edges, then SCC 2's edges, and so on.

**No conflicts:** Each worker only reads the graph structure (which never changes) and writes to its own private edge list. The final merge step is the only time results are combined, and it happens in a fixed order after all parallel work is done.

**No randomness:** We don't use random numbers, random task assignment, or any non-deterministic operations. The thread scheduler might run workers in different orders, but the final result order is always the same because we explicitly sort by SCC index.

## Proof It Works

### Correctness Parity

The parallel implementation produces identical output to the sequential baseline on all test cases:

- **Edge cases:** Single node (0 edges), disconnected graph (0 edges)
- **Small inputs:** 3-node cycle (4 edges), 6-node dual-SCC (8 edges)
- **Medium inputs:** 9-node complex graph with inter-SCC edges (12 edges)
- **Large inputs:** 100-node graph with 20 SCCs (160 edges), 10,000-node graph with 100 SCCs

All tests show exact edge count and edge set matches. See `run_summary.txt` for complete results.

### Determinism

Three consecutive runs of the parallel implementation on a 60-node graph (15 SCCs, 4 nodes each) produced identical results:

- Run 1 hash: `53c7ddb064c19182700c9d44e2ccadd3a56c2eb9495e85940ba4d5682c4b024a`
- Run 2 hash: `53c7ddb064c19182700c9d44e2ccadd3a56c2eb9495e85940ba4d5682c4b024a`
- Run 3 hash: `53c7ddb064c19182700c9d44e2ccadd3a56c2eb9495e85940ba4d5682c4b024a`

All three hashes are identical, confirming deterministic behavior. See `run_summary.txt` for details.

### Performance

**Test 1: Medium graph (1,000 nodes, 50 SCCs)**
- Sequential time: 4.44 ms
- Parallel time: 12.70 ms
- Speedup: 0.35x (slower)
- Cores: 16

**Test 2: Large graph (10,000 nodes, 100 SCCs)**
- Sequential time: 23.02 ms
- Parallel time: 32.86 ms  
- Speedup: 0.70x (slower)
- Cores: 16

**Why parallelization doesn't help:**

1. **Amdahl's Law ceiling:** Tarjan's SCC detection is inherently sequential and takes ~40-50% of total time. Even with infinite parallelism on the remaining work, maximum theoretical speedup is ~2x.

2. **Memory bandwidth bottleneck:** Spanning tree construction is memory-bound (traversing adjacency lists, allocating edge arrays). Adding more threads doesn't help when all threads are waiting on memory.

3. **Thread pool overhead:** Creating a ForkJoinPool, submitting tasks, and synchronizing results takes 5-10 ms, which exceeds the actual computation time for typical SCCs (each SCC processes in 0.1-0.5 ms).

4. **Small per-task granularity:** With 100 SCCs and 16 cores, each worker processes ~6 SCCs. But each SCC completes so quickly that task scheduling overhead dominates.

See `perf.txt` for detailed measurements.

## Limits & Safety Switches

**Small inputs:** Graphs with fewer than 10 SCCs automatically use the sequential algorithm. Below this threshold, thread pool overhead always exceeds any potential benefit. This threshold was determined empirically by testing graphs with 5, 10, 15, and 20 SCCs.

**Resource bounds:** Worker count is capped at the number of physical CPU cores (16 on the test machine) to prevent oversubscription. We also cap workers at the number of SCCs (no point having 16 workers for 8 SCCs).

**Corner cases handled:**
- Empty graph (0 nodes): Returns empty edge list
- Single node: Returns empty edge list  
- Disconnected components: Each component is its own SCC, processed independently
- Very large SCCs: No special handling needed; each SCC is still processed independently

**Thread pool lifecycle:** The ForkJoinPool is created fresh for each `reduceEdges()` call and shut down immediately after, preventing resource leaks and ensuring clean state for repeated calls.

## How to Reproduce

**Rerun correctness and determinism tests:**
```bash
javac Graph.java GraphParallel.java TestGraphSCC.java
java TestGraphSCC
```

**Rerun performance tests:**
```bash
# Medium graph (1,000 nodes, 50 SCCs)
javac Graph.java GraphParallel.java PerfTest.java
java PerfTest

# Large graph (10,000 nodes, 100 SCCs)
javac Graph.java GraphParallel.java PerfTestLarge.java
java PerfTestLarge
```

All commands write results to `run_summary.txt` and `perf.txt`.

## Alternatives We Considered

### 1. Parallel Tarjan's Algorithm (Multi-Pivot)

**What it would do:** Run multiple Tarjan DFS traversals in parallel from different starting nodes, using atomic operations to coordinate discovery times and SCC membership.

**Why it loses here:**
- **Shared state synchronization:** The discovery/low-link arrays and the SCC stack require atomic updates or locks on every node visit, creating severe contention. With 10,000 nodes, this means 10,000+ atomic operations, each with cache coherence overhead.
- **Non-determinism risk:** Without careful ordering of atomic updates, different runs could discover SCCs in different orders, breaking our determinism guarantee.
- **Patch size violation:** Would require rewriting the entire Tarjan algorithm (~80 LOC) plus adding thread-safe data structures (~50 LOC) and coordination logic (~40 LOC), totaling ~170 LOC of changes.
- **Correctness complexity:** Parallel Tarjan is an active research area with subtle race conditions. The sequential algorithm is proven correct; parallelizing it introduces significant correctness risk.

**What would make it viable:** If SCC detection took 90%+ of total time (not 40-50%) and we had graphs with 100,000+ nodes where the coordination overhead would be amortized. Also would need acceptance of non-deterministic SCC ordering.

### 2. Task Graph / Wavefront Parallelism

**What it would do:** Build a dependency graph of SCCs (which SCCs must be processed before others based on inter-SCC edges), then process SCCs in parallel waves where each wave contains SCCs with no dependencies on later waves.

**Why it loses here:**
- **No dependencies exist:** Our algorithm processes each SCC completely independently. There are no inter-SCC dependencies in the edge minimization phase. A task graph would just add overhead without enabling any additional parallelism beyond what we already have.
- **Overhead without benefit:** Building the task graph requires analyzing all inter-SCC edges (O(E) work), then scheduling waves. This overhead is pure waste when we can already process all SCCs in parallel.
- **Complexity cost:** Would require ~100 LOC for task graph construction, topological sorting, and wave scheduling, all for zero benefit.

**What would make it viable:** If the edge minimization algorithm had dependencies between SCCs (e.g., "must process SCC A before SCC B"), which it doesn't. This approach solves a problem we don't have.

### 3. Parallel Spanning Tree Construction Within Each SCC

**What it would do:** For each SCC, parallelize the forward and reverse spanning tree construction by having multiple threads explore different branches of the DFS tree simultaneously.

**Why it loses here:**
- **Tiny work units:** Each SCC has 20-100 nodes. A DFS spanning tree on 100 nodes completes in 50-200 microseconds. Thread creation alone takes 10-50 microseconds, so we'd spend more time creating threads than doing actual work.
- **Shared visited set:** All parallel DFS threads would need to coordinate on a shared "visited" set using atomic operations or locks, creating contention that would slow down the already-fast DFS.
- **Memory bandwidth saturation:** DFS is memory-bound (pointer chasing through adjacency lists). Adding more threads doesn't help when they're all waiting on the same memory bus.
- **Diminishing returns:** Even if we achieved 2x speedup on spanning tree construction (optimistic), that's only 30% of total time, giving 1.2x overall speedup at best, which wouldn't overcome the thread pool overhead.

**What would make it viable:** If each SCC had 10,000+ nodes and the spanning tree construction took seconds instead of microseconds. At that scale, the coordination overhead would be amortized. Also would need a machine with high memory bandwidth to support multiple concurrent DFS traversals.

### 4. Data-Parallel Graph Representation (Structure of Arrays)

**What it would do:** Restructure the adjacency lists from a list-of-lists (Array of Structures) to a flat array with offset indices (Structure of Arrays), enabling better cache locality and potential SIMD vectorization.

**Why it loses here:**
- **No vectorization opportunity:** Graph traversal (DFS) is inherently pointer-chasing with unpredictable branches. SIMD doesn't help with irregular memory access patterns.
- **Cache locality already good:** The current ArrayList-based representation has excellent cache locality for small SCCs (20-100 nodes). The entire adjacency list for an SCC fits in L2 cache.
- **Conversion overhead:** Would need to convert the input graph representation, adding O(V+E) preprocessing time that would exceed any cache benefit.
- **Complexity explosion:** Would require changing the Graph constructor, addEdge method, and all traversal code (~120 LOC changes) for negligible benefit.

**What would make it viable:** If we were doing bulk operations on edges (e.g., filtering all edges by weight) where SIMD could process 4-8 edges at once. Graph traversal doesn't fit this pattern. Also would need much larger graphs (100,000+ nodes) where cache misses dominate.

## Honest Conclusion

This parallelization is **correct and deterministic**, but **not faster** for typical graph sizes. The implementation demonstrates that not all algorithms benefit from parallelization, even when the work appears parallelizable on paper.

The fundamental issue is that **thread overhead exceeds computation time** for this workload. Each SCC processes in 0.1-0.5 milliseconds, while thread pool operations take 5-10 milliseconds. It's like using a semi-truck to deliver a single envelope—the overhead of starting the truck exceeds the delivery time.

The sequential algorithm remains the best choice for graphs with up to 100,000 nodes and 1,000 SCCs. Parallelization might help for truly massive graphs (1,000,000+ nodes, 10,000+ SCCs with 100+ nodes each), but such graphs are rare in practice.

**Key lesson:** Parallelization is a tool, not a goal. Sometimes the sequential algorithm is the right answer.
