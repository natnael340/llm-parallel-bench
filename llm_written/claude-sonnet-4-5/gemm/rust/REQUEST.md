# Request: Parallelize GEMM Implementation

## Input Code
Rust implementation of GEMM (General Matrix Multiply) with tiled/blocked algorithm.

## Key Algorithm Characteristics
- Computes C := alpha * A * B + beta * C
- Uses blocking/tiling strategy with mb, nb, kb tile sizes
- Three nested loops over tiles: n0 (columns), k0 (inner dimension), m0 (rows)
- Transposes B matrix for cache efficiency
- Packs sub-matrices for better memory access patterns
- partial_matmul performs the actual multiplication on tiles

## Constraints
- Language: Rust
- Must maintain correctness (exact floating-point match)
- Must be deterministic (same input → same output every run)
- Respect resource bounds (CPU core count)
- Preserve public API (gemm function signature)

## Parallelization Considerations
- Loop-carried dependencies: C accumulation across k0 iterations
- Shared state: C matrix is mutated
- Ordering requirements: k0 loop has dependencies, but n0 and m0 loops are independent
- Data layout: Row-major Vec<Vec<f64>>
