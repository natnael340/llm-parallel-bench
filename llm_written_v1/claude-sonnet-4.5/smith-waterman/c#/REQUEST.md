# Parallelization Request

## Input
- **Language**: C#
- **Algorithm**: Smith-Waterman local sequence alignment
- **Baseline**: Sequential implementation with three main phases:
  1. ConstructMatrix: Fill scoring matrix H[n×m] with dynamic programming
  2. FindHighestScore: Scan matrix for maximum score location
  3. Traceback: Follow optimal path from max score to reconstruct alignment

## Key Methods
- `ConstructMatrix(query, reference)`: Nested loops i=1..n, j=1..m, each cell depends on H[i-1][j-1], H[i-1][j], H[i][j-1]
- `FindHighestScore(H)`: Independent scan over all cells
- `Traceback(H, query, reference)`: Sequential path-following from max score

## Constraints
- **Deterministic**: Same inputs must produce identical outputs (alignment strings, score, identity %)
- **Correctness**: Must match sequential results exactly
- **Bounded patch**: ≤3 files, ≤250 LOC changes
- **Resource-bounded**: Cap parallelism to CPU count
- **Public API**: Keep SmithWaterman constructor and FindAlignment() signature unchanged

## Goals
1. Parallelize matrix construction (main bottleneck for large sequences)
2. Optionally parallelize FindHighestScore scan
3. Keep Traceback sequential (path-dependent)
4. Maintain deterministic output
5. Add small-N sequential fallback
