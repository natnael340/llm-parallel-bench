This repository adds a deterministic, parallel breadth‑first search (BFS) alongside the original sequential variant.

Files created
- llm_written/bfs.go: Public API and both implementations (BfsSequential, BfsParallel) with the Graph type.
- llm_written/bfs_test.go: Rigorous tests that verify parity with the sequential implementation and determinism across runs, plus edge cases.

API preservation
- The public type Graph and method AddEdge are unchanged.
- The sequential behavior is available as BfsSequential, mirroring the provided logic.
- A new function BfsParallel provides parallel execution while preserving the output order of BfsSequential.

Parallelization strategy
- The BFS is executed in level‑synchronous rounds. In each round, the current frontier ( slice of nodes at the same BFS depth) is expanded in parallel.
- To keep determinism and match the sequential order, we do not enqueue neighbors concurrently. Instead, each worker computes candidates it would discover, keyed by a deterministic tie‑break key edgeKey{parentIdx, neighborIdx} where parentIdx is the index of the parent node within the current frontier and neighborIdx is the index within the parent’s adjacency slice.
- Workers operate read‑only on the graph and a per‑level snapshot of the visited set (snapshotVisited) to avoid races. Each worker builds a local map neighbor→minimal key. These local maps are merged serially into a global map using the same minimal‑key rule. The next frontier is obtained by stably sorting the global candidates by (parentIdx, neighborIdx), which exactly reproduces the enqueue order of the sequential BFS.

Resource bounds and small‑input fast path
- Worker count is bounded by runtime.GOMAXPROCS(0) and the frontier size. Work is distributed via a bounded channel of parent indices.
- For small graphs (≤ 2048 total adjacency entries), BfsParallel falls back to BfsSequential to avoid goroutine overhead.

Determinism and correctness
- All non‑determinism is isolated behind local maps and a single‑goroutine merge and sort with a fixed comparator, guaranteeing the same result for identical inputs across runs and matching BfsSequential.
- No shared writes occur across goroutines: only read‑only access to g.Vertices and snapshotVisited, and writes are per‑goroutine local.

Complexity
- Time per level: O(sum of degrees over the frontier) + O(F log F) to sort unique new nodes (F ≤ number of candidates). Space is O(V) for visited and O(F) for next frontier.

Testing summary
- Tests cover: empty graph, missing start, a simple path, and randomized graphs (fixed seeds). Parallel vs sequential parity and two parallel runs are compared for determinism.
