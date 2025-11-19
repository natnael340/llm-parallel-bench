# Parallelization Justification: Tarjan's SCC Edge Reduction

## 1. What Changed and Why

The original algorithm finds **strongly connected components** (SCCs) in a directed graph, then computes a minimal set of edges for each SCC. Think of a graph as a network of cities (nodes) with one-way roads (edges). An SCC is a group of cities where you can drive from any city to any other city in that group, following the one-way roads.

**Sequential Process (Original)**:
1. Find all SCCs using Tarjan's depth-first search algorithm.
2. For each SCC found, compute a minimal edge set by building two spanning trees (forward and reverse).
3. Combine all minimal edge sets into a final result.

**Example with 6 cities forming 2 SCCs**:
- SCC #1: Cities {0,1,2} form a loop: 0→1→2→0
- SCC #2: Cities {3,4,5} form a loop: 3→4→5→3
- Plus a road from SCC #1 to SCC #2: 2→3

The sequential code processes each SCC one after another. If SCC #1 takes 50ms and SCC #2 takes 50ms, total time is 100ms.

**The Change**: We parallelized step 2—the per-SCC edge minimization. Step 1 (Tarjan's DFS) stays sequential because it has dependencies that prevent safe parallelization. Step 2, however, is embarrassingly parallel: each SCC's minimization is independent.

## 2. How We Made It Parallel

**Split the Work (Fixed Chunks)**:
- After finding N SCCs, we distribute them to W worker goroutines (W = number of CPU cores, capped at N).
- Each worker gets a job containing one SCC index and the node list.

**What Each Worker Does**:
- Receives a job (e.g., "process SCC #3").
- Calls `MinimizeEdgesInSCC(scc)` which:
  - Builds a forward spanning tree (visits nodes following forward edges).
  - Builds a reverse spanning tree (visits nodes following backward edges).
  - Merges both edge sets.
- Sends the result (index + edges) to a result channel.

**Fixed-Order Combine**:
- A collector goroutine gathers all results into a map keyed by SCC index.
- After all workers finish, we reconstruct the final edge list by appending results in index order: 0, 1, 2, ..., N-1.
- This ensures the same input always produces the same output order.

**ASCII Visualization**:
```
Input: Graph ▶ Tarjan's DFS (sequential) ▶ [SCC₀][SCC₁][SCC₂][SCC₃]
                                              │     │     │     │
                                           Worker Worker Worker Worker
                                              1     2     3     4
                                              └──────┬──────┘──────┘
                                                     │
                                         Fixed-order merge (0→1→2→3)
                                                     ▼
                                                 Result
```

**Small-Input Fast Path**:
- If fewer than 4 SCCs are found, we skip parallelization and run sequentially to avoid goroutine overhead.

## 3. Why the Answer Is Always the Same (Determinism)

**Same Split Every Time**:
- For a given graph, Tarjan's DFS produces the same SCC list in the same order (it's deterministic).
- We assign SCC index 0 to worker slot 0, SCC index 1 to worker slot 1, etc., in a round-robin fashion via a buffered channel.

**Same Combine Order**:
- Workers return results with their original index attached.
- The final merge reconstructs edges by iterating indices 0 to N-1, regardless of which worker finished first.
- This is like assembling puzzle pieces: even if pieces arrive out of order, we place them by their number (1, 2, 3, ...).

**No Conflicts**:
- Each worker operates on a disjoint SCC; no two workers touch the same nodes or shared state.
- Workers write results to a channel, which is thread-safe in Go.
- The final merge happens after all workers finish, so no race conditions.

**No Floating-Point Randomness**:
- The algorithm uses only integers (node IDs, edge counts). No floating-point arithmetic, so no rounding issues.

## 4. Proof It Works

**Correctness Parity**:
- All 8 test cases passed correctness checks: sequential and parallel outputs are identical (same edge count, same edge sets after normalization).
- Edge cases tested: empty graph (0 nodes), single node, linear chain, cycle, multiple SCCs, and a complete graph.
- See `evidence/run_summary.txt` for per-case results.

**Determinism**:
- For each test, we ran the parallel version twice and computed SHA-256 hashes of the normalized edge sets.
- All hash pairs matched:
  - `Edge_Empty`: `e3b0c44298fc1c14` (both runs)
  - `Small_Cycle_5`: `67abdc6bc545a9b5` (both runs)
  - `Large_50SCCs_20each`: `7d1adc6f77b947f8` (both runs)
  - ... (see `evidence/run_summary.txt` for all cases)

**Performance**:
- **Large_50SCCs_20each** (50 SCCs, 20 nodes each, 1000 total nodes):
  - Sequential: 2.90 ms
  - Parallel: 1.64 ms
  - Speedup: **1.77×**
- **Small cases** (< 4 SCCs): Used sequential fast path; parallel overhead would hurt.
- Note: Speedup is moderate because per-SCC work is small (spanning tree on ~20 nodes is fast). Larger SCCs would show higher speedup.

## 5. Limits & Safety Switches

**Small-Input Threshold**:
- If fewer than 4 SCCs, we run sequentially. Goroutine creation/coordination overhead (~500ns–1µs each) would exceed the benefit for tiny workloads.
- Rationale: SCC minimization for N=3 takes ~50µs; spinning up 3 workers + channel ops takes ~2µs, leaving no net gain.

**Resource Bounds**:
- Workers capped at `runtime.NumCPU()` (e.g., 8 on an 8-core machine).
- Job queue is buffered (size = SCC count), so we don't create unbounded goroutines.
- Workers are launched once, process all jobs, then exit—no goroutine leaks.

**Corner Cases Handled**:
- **Empty graph (0 nodes)**: Returns 0 edges; no workers launched.
- **Single node**: Returns 0 edges (no SCC edges to reduce); sequential fast path.
- **Disconnected components**: Each component becomes an SCC; all processed independently.

## 6. How to Reproduce

**Run All Tests (Correctness + Determinism + Performance)**:
```bash
go run test_runner.go
```
This executes 8 test cases, compares sequential vs. parallel, runs parallel twice, and writes results to `evidence/run_summary.txt`.

**Check Determinism Manually**:
```bash
go run test_runner.go | grep "hash:"
```
Verify that `Run1 hash` and `Run2 hash` match for all tests.

**Quick Performance Check (Large Case Only)**:
```bash
go run test_runner.go 2>/dev/null | grep "Large_50SCCs"
```
Expect `speedup=1.7x` or similar (depends on CPU).

## 7. Glossary

- **Parallel**: Multiple CPU cores work on different parts of the problem at the same time (not "one after another").
- **Deterministic**: Same input → same output, every time. No randomness, no race conditions.
- **Worker**: A helper goroutine that processes one chunk (one SCC) of the data.
- **Merge/Combine**: Taking partial results from workers and joining them in a fixed order (0, 1, 2, ...).
- **SCC (Strongly Connected Component)**: A group of graph nodes where every node can reach every other node via directed edges.
- **Spanning Tree**: A subset of edges that connects all nodes in a group without cycles (like a tree structure).
- **Goroutine**: Go's lightweight thread; cheaper than OS threads, safe for thousands of concurrent tasks.
- **Channel**: Go's message-passing primitive; safe for sending data between goroutines without locks.
- **Fast Path**: A special code branch for simple cases (e.g., tiny inputs) that skips expensive setup.
