User has provided a Rust implementation of the Smith-Waterman algorithm for sequence alignment.

The goal is to parallelize this algorithm, focusing on the `construct_matrix` and `find_highest_score` methods.

Constraints:
- The parallel version must be deterministic.
- The solution should be resource-bounded (e.g., using a fixed-size thread pool).
- A rigorous differential test suite must be provided to verify correctness and determinism.
- A `JUSTIFICATION.md` file explaining the changes is required.
