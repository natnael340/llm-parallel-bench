# Parallelization Request

## Input
C# GEMM (General Matrix Multiply) implementation with tiled/blocked algorithm.

## Algorithm
Computes: C := alpha * A * B + beta * C
- A is m×k matrix
- B is k×n matrix  
- C is m×n matrix
- Uses cache-friendly tiling with configurable block sizes (MB, NB, KB)
- Transposes B for better cache locality
- Packs sub-matrices for efficient access

## Key Characteristics
- Triple nested loop over tiles (n0, k0, m0)
- Inner PartialMatmul performs blocked matrix multiplication
- Accumulates results into shared C matrix
- No loop-carried dependencies between tiles at same k-level
- Sequential reduction across k-dimension tiles

## Constraints
- Language: C#
- Must maintain correctness (exact floating-point match with sequential)
- Must be deterministic (same input → same output every run)
- Respect resource bounds (bounded parallelism)
- Target performance improvement on large matrices

## Deliverables
1. Parallel implementation (gemm_parallel.cs)
2. Differential test harness (test_gemm.cs)
3. Test runner (run_gemm.cs)
4. JUSTIFICATION.md (600-1100 words, non-technical)
5. run_summary.txt (correctness + determinism results)
6. perf.txt (performance measurements)
