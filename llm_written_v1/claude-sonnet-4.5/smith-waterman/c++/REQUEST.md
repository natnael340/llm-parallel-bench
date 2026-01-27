# Parallelization Request: Smith-Waterman Algorithm

## Input
Sequential C++ implementation of Smith-Waterman local sequence alignment algorithm.

## Files Provided
- smith_waterman.h (header, assumed standard interface)
- smith_waterman.cpp (implementation with constructMatrix, findHighestScore, traceback, findAlignment)

## Key Components
1. **constructMatrix**: Fills (n+1) × (m+1) scoring matrix H with dynamic programming
2. **findHighestScore**: Scans entire matrix for maximum score position
3. **traceback**: Walks backward from max score to build alignment strings
4. **findAlignment**: Orchestrates the full pipeline

## Constraints
- Deterministic output required (same input → same alignment)
- Preserve public API
- Language: C++ with OpenMP
- Resource-bounded (≤3 files, ≤250 LOC change, workers ≤ core count)

## Expected Deliverables
- Parallel implementation with OpenMP
- Differential test harness (edge/small/medium/large cases, determinism check)
- JUSTIFICATION.md (600–1100 words, non-coder audience)
- run_summary.txt (correctness + determinism results)
- perf.txt (if large N tested)
