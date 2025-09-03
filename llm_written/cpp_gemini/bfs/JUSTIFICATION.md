### BFS Parallelization Justification

The parallelization of the Breadth-First Search (BFS) algorithm was implemented in `bfs_parallel.cpp` using a level-synchronous approach with OpenMP. The public API is preserved, with the parallel function `bfs_parallel(Graph&, int)` matching the signature of the original sequential one.

**Partitioning and Worker Logic**
The core of the algorithm iterates through the graph level by level. The set of nodes at the current level is stored in a vector called `frontier`. The main `while (!frontier.empty())` loop is sequential, ensuring that one level is completely processed before the next begins. Within this loop, the task of exploring the neighbors of each node in the `frontier` is parallelized. An OpenMP `#pragma omp parallel for schedule(dynamic)` directive distributes the nodes in the `frontier` among multiple threads. Each thread executes a portion of the loop, finds the neighbors for its assigned nodes, and adds newly discovered nodes to a private, thread-local vector (`local_next_frontiers`). This partitioning scheme is effective because the work of visiting neighbors for different nodes at the same level is independent.

**Merge Rule and Determinism**
After all threads complete the parallel for-loop, their local discovery lists (`local_next_frontiers`) are merged into a single `next_frontier` vector. To guarantee deterministic output, which is crucial for reproducibility and correctness, two sorting steps are enforced:
1.  Inside the parallel region, each thread sorts the neighbors of a node before processing them.
2.  After the parallel region, the merged `next_frontier` is sorted before it becomes the `frontier` for the next level.
These sorting operations ensure that the traversal order is identical across different runs, regardless of thread scheduling. The sequential baseline in `bfs_seq.cpp` was also modified to follow the same level-synchronous, sorted logic to provide a valid comparison target.

**Race Condition Avoidance and Performance**
The `visited` map is a shared resource that presents a potential race condition. This is managed using two separate `#pragma omp critical` sections. A node's visited status is first checked in a critical section. If it has not been visited, the thread enters a second, separate critical section to update the map and claim the node. Separating the check from the update minimizes lock contention, as the expensive update lock is only acquired when a new node is discovered.

For performance, a small-input fast path is included. If the graph has fewer than `PARALLEL_THRESHOLD` (1000) vertices, the code defaults to the sequential `bfs` implementation in `bfs_seq.cpp` to avoid the overhead of thread management on small workloads.

**Verification**
The implementation was rigorously tested by `test_bfs.cpp`, which compares the parallel output against the deterministic sequential baseline across 8 test cases. These include an empty graph, a single-node graph, a small linear graph (testing the sequential fallback), a large random graph, a star graph, and a disconnected graph. Tests confirmed correctness and determinism, with two consecutive runs yielding identical, correct results.
