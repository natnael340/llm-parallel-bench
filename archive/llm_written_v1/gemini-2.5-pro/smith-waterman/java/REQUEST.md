**User Request**

The user wants to parallelize a Java implementation of the Smith-Waterman algorithm.

**Core Algorithm**

The `constructMatrix` method is the computationally intensive part of the algorithm. It fills a 2D matrix `H` where each cell `H[i][j]` depends on its neighbors: `H[i-1][j-1]`, `H[i-1][j]`, and `H[i][j-1]`. This creates a wavefront dependency, where cells on a diagonal can be computed in parallel.

**Constraints**

- The solution must be deterministic.
- The public API should remain unchanged.
- The solution should be resource-bounded.
- The solution must be implemented in Java.
