User provided a Rust implementation of Smith-Waterman local alignment with sequential dynamic programming matrix fill and traceback. Goal: create a correct, deterministic, resource-bounded parallel implementation, tests, and justification.

Language: Rust.
Constraints:
- Minimal patch; preserve public API if possible; output files per spec.
- Deterministic splitting and fixed reduction order.
- Provide algo_parallel.rs, test_smith_waterman.rs and/or run_smith_waterman.rs, JUSTIFICATION.md, and evidence files.

We will parallelize the construct_matrix phase using Rayon with bounded thread pool, fixed chunking, and row-wise wavefront (anti-diagonal) parallelism or striped rows. Determinism must be preserved by fixed partition and merge order. Include sequential fallback for small inputs.
