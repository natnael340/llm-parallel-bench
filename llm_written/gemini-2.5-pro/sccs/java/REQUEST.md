
You are asked to parallelize a Java program that performs edge reduction in a graph.
The main entry point is `reduceEdges`, which first finds all Strongly Connected Components (SCCs) using Tarjan's algorithm, and then for each SCC, it finds a minimal set of edges to preserve the SCC structure.

The user has provided one Java file: `Graph.java`.

Your task is to create a parallel version of the `reduceEdges` method, ensuring correctness, determinism, and performance.
You must also provide a differential test suite to verify your implementation against the original, and a `JUSTIFICATION.md` explaining your approach.

Constraints:
- The solution must be in Java.
- The parallel implementation must be deterministic.
- The parallel implementation should be resource-bounded (e.g., using a fixed-size thread pool).
- The public API of the `Graph` class should be preserved as much as possible.
