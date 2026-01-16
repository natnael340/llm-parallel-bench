# Request: Parallelize Smith-Waterman Local Sequence Alignment

## Input
Go implementation of Smith-Waterman algorithm with:
- ConstructMatrix: builds scoring matrix (n×m) with match/mismatch/gap scoring
- FindHighestScore: finds max score position in matrix
- Traceback: reconstructs alignment from max score position

## Constraints
- Language: Go
- Must maintain deterministic output (same alignment, score, identity%)
- Public API unchanged
- Bounded patch: ≤3 files or ≤250 LOC changes

## Performance Target
- Speedup ≥1.3× on sequences where n×m ≥ 10000
