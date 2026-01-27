# Parallelization Request: Smith-Waterman Algorithm

## Input
Sequential Java implementation of Smith-Waterman local sequence alignment algorithm.

## Key Components
1. **constructMatrix**: Builds scoring matrix H[n×m] where each cell depends on three neighbors (diagonal, up, left)
2. **findHighestScore**: Linear scan to find maximum score position
3. **traceback**: Sequential path following from max score to zero

## Constraints
- Must maintain deterministic output (same alignment and score every time)
- Preserve public API
- Language: Java (use ForkJoinPool or parallel streams with bounded parallelism)

## Analysis
### Dependencies
- **constructMatrix**: Anti-diagonal wavefront dependency pattern
  - Cell H[i][j] depends on H[i-1][j-1], H[i-1][j], H[i][j-1]
  - Cells on same anti-diagonal are independent
  - Row-by-row requires sequential processing within rows
  
- **findHighestScore**: Embarrassingly parallel (read-only scan)
- **traceback**: Inherently sequential (follows dependency chain backwards)

## Target
Parallelize constructMatrix using anti-diagonal wavefront approach with bounded workers.
