# Parallelization Request

## Original Algorithm
GEMM (General Matrix Multiply): C := alpha * A * B + beta * C

## Language
Go

## Baseline Implementation
- Blocked matrix multiplication with configurable block sizes (MB, NB, KB)
- Uses transpose optimization for B matrix
- Packs sub-matrices as views (no copy)
- Triple-nested loop over blocks: n-blocks, k-blocks, m-blocks
- Inner kernel: partialMatmul computes C[m0:m1, n0:n1] += alpha * A[m0:m1, k0:k1] * B[k0:k1, n0:n1]

## Constraints
- Correctness: outputs must match sequential baseline exactly
- Determinism: same input must produce same output on every run
- Performance: maximize speedup on large matrices while respecting resource bounds
- Maintainability: code must remain readable and reproducible

## Resource Bounds
- Cap workers to available CPU core count
- Avoid oversubscription
- Use bounded worker pools
