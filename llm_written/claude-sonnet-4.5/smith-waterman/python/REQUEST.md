# Parallelization Request: Smith-Waterman Algorithm

## Input
Sequential Smith-Waterman local sequence alignment algorithm in Python.

## Key Components
1. **constructMatrix**: Builds scoring matrix H[n×m] with dynamic programming
2. **findHighestScore**: Scans entire matrix for maximum score
3. **traceback**: Backtraces from max score to construct alignment
4. **findAlignment**: Main entry point combining all steps

## Constraints & Analysis
- **constructMatrix**: Strong loop-carried dependencies (anti-diagonal wavefront)
  - H[i][j] depends on H[i-1][j-1], H[i-1][j], H[i][j-1]
  - Each cell needs three predecessor cells computed first
  - Can parallelize by anti-diagonals (same anti-diagonal = independent cells)

- **findHighestScore**: Embarrassingly parallel reduction (max operation)
  - No dependencies between cells
  - Associative max reduction

- **traceback**: Sequential by nature (single path following backpointers)
  - Cannot parallelize (path-dependent)

## Parallelization Strategy
1. **constructMatrix**: Parallelize anti-diagonal wavefronts
   - Divide each anti-diagonal into chunks
   - Process chunks in parallel
   - Synchronize between diagonals
   
2. **findHighestScore**: Parallel reduction over matrix rows
   - Each worker finds max in subset of rows
   - Combine with deterministic order

3. **traceback**: Keep sequential (inherently serial)

## Language
Python with ProcessPoolExecutor (CPU-bound DP computation)

## Determinism Requirements
- Fixed anti-diagonal partitioning
- Fixed row assignment for max finding
- Deterministic worker assignment
