# Request: Parallelize Smith-Waterman Algorithm (Rust)

## Input
Sequential Rust implementation of Smith-Waterman local sequence alignment algorithm.

## Key Components
1. `construct_matrix` - Fills DP matrix (main bottleneck)
2. `find_highest_score` - Finds max score position
3. `traceback` - Reconstructs alignment path

## Constraints
- Language: Rust
- Must be deterministic (same input → same output)
- Resource-bounded (cap parallelism)
- Maintain public API
- Correctness: exact match with sequential version

## Target
- Parallelize the matrix construction phase (double nested loop)
- Apply anti-diagonal (wavefront) parallelization strategy
- Use Rayon for thread pool management
