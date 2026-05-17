# Parallelization Request

## Input
Sequential GEMM (General Matrix Multiply) implementation in C++.

## Algorithm
Computes C := alpha * A * B + beta * C
- A is (m x k)
- B is (k x n)  
- C is (m x n)
- Uses blocked/tiled algorithm with configurable block sizes (MB, NB, KB)
- Transposes B for cache-friendly access
- Packs submatrices for each block computation

## Constraints
- Language: C++
- Must use OpenMP
- Correctness: outputs must match sequential baseline exactly
- Determinism: same input must produce same output on every run
- Performance: target ≥50% parallel efficiency on large inputs
- Resource bounds: cap threads at physical core count

## Key Characteristics
- Triple nested loop over n-blocks, k-blocks, m-blocks
- Inner partialMatmul is compute-intensive and parallelizable
- No loop-carried dependencies across m-blocks for a given (n0, k0) pair
- Reduction accumulation into C requires careful ordering for determinism
