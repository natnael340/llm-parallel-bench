# Parallelization Request

## Algorithm
GEMM (General Matrix Multiply): C := alpha * A * B + beta * C

## Language
Java

## Baseline Implementation
- Tiled matrix multiplication with configurable tile sizes (MB, NB, KB)
- Uses transpose + packing for cache efficiency
- Three nested loops over tiles: n0, k0, m0
- Inner kernel: partialMatmul computes tile-level products

## Key Characteristics
- Input: A (m×k), B (k×n), scalars alpha/beta, optional C (m×n)
- Output: m×n result matrix
- Tiling strategy: iterates over n-tiles, then k-tiles, then m-tiles
- B is transposed once upfront for better cache locality
- Each tile pair is packed before multiplication

## Constraints
- Must maintain exact numerical determinism (floating-point order matters)
- Must respect resource bounds (bounded parallelism)
- Must preserve public API
- Must handle edge cases (null C, beta scaling, alpha=0 short-circuit)
