# Smith-Waterman Parallel Implementation

## Overview
This is a parallel implementation of the Smith-Waterman local sequence alignment algorithm in C#, transformed from a sequential baseline while maintaining correctness, determinism, and resource bounds.

## Files

### Implementation
- **algo_parallel.cs** - Final parallel implementation using wavefront/anti-diagonal approach
- **SmithWatermanSequential.cs** - Sequential baseline for comparison
- **SmithWaterman.cs** - Same as algo_parallel.cs (working version)

### Testing
- **test_smithwaterman.cs** - Differential test harness with correctness and determinism checks
- **TestSmithWaterman.cs** - Same as test_smithwaterman.cs (working version)

### Documentation
- **JUSTIFICATION.md** - Complete technical justification (1600+ words) explaining:
  - What changed and why
  - How parallelization works (step-by-step)
  - Why it's deterministic
  - Proof of correctness with evidence
  - Performance analysis
  - Alternatives considered with concrete reasons
- **run_summary.txt** - Test results showing correctness and determinism verification
- **perf.txt** - Performance measurements and overhead analysis
- **REQUEST.md** - Original parallelization request and constraints

## Quick Start

### Run All Tests
```bash
dotnet run --project .setup SmithWaterman.cs SmithWatermanSequential.cs TestSmithWaterman.cs
```

### View Results
```bash
cat run_summary.txt  # Correctness and determinism summary
cat perf.txt         # Performance analysis
cat JUSTIFICATION.md # Full technical explanation
```

## Key Results

### ✓ Correctness
All 13 test cases (edge, small, medium, large) pass. Parallel output matches sequential baseline exactly.

### ✓ Determinism
Running parallel version twice on same input produces identical results. All hash comparisons match:
- Empty strings: `4D353861B9CC65ED` (both runs)
- 200×200 random: `29DEC21BBA7ED6AB` (both runs)
- 1200×1200 random: `8CE96E2E20EDC607` (both runs)

### ⚠️ Performance
The parallel version shows slowdown rather than speedup due to C# TPL overhead:
- 600×600: 0.04× speedup (12.92ms → 336.86ms)
- 1200×1200: 0.23× speedup (102.56ms → 455.02ms)

**Mitigation:** Sequences < 500 characters automatically use sequential fallback.

## Approach

### Strategy: Wavefront/Anti-Diagonal Parallelization
Smith-Waterman has strict dependencies: each cell H[i][j] depends on H[i-1][j-1], H[i-1][j], and H[i][j-1]. This makes row-parallel and column-parallel approaches unsafe due to race conditions.

The **only safe parallelization** is processing anti-diagonals (cells where i+j=constant) because these cells only depend on *previous* diagonals:
```
Diagonal 2: (1,1)
Diagonal 3: (1,2), (2,1)              ← Can parallelize
Diagonal 4: (1,3), (2,2), (3,1)       ← Can parallelize
...
```

### Determinism
1. Fixed diagonal order: 2, 3, 4, ..., N+M-1
2. Fixed worker assignments per diagonal
3. No race conditions (each worker writes to distinct cells)
4. Fixed-order reduction in FindHighestScore
5. Integer-only operations (no floating-point non-determinism)

### Resource Bounds
- Workers capped at CPU core count (16)
- Sequential fallback for sequences < 500 chars
- No nested parallelism
- Bounded memory (matrix size O(N×M))

## Alternatives Considered

See JUSTIFICATION.md section 8 for detailed analysis of 6 alternatives, including:
1. **Row-striping with locks** - Rejected: race conditions at boundaries, non-deterministic
2. **Column-based parallelism** - Rejected: violates left-to-right dependencies
3. **Blocked 2D tiling** - Rejected: exceeds bounded patch (>250 LOC), complex scheduling
4. **Parallel scan only** - Rejected: misses main bottleneck (matrix construction is 95% of runtime)
5. **Sequential fallback only** - Rejected: goal was to demonstrate parallel implementation
6. **OpenMP in C++** - Rejected: language constraint (would perform better)

Each alternative includes concrete code-specific reasons for rejection.

## Tradeoffs

The implementation demonstrates that:
- **Correctness and determinism are achievable** for wavefront parallelization in C#
- **Performance benefits depend on overhead/work ratio** - TPL overhead is too high for per-cell granularity
- **Larger inputs might benefit** - crossover point likely around 5000×5000 or larger
- **Different runtimes could help** - OpenMP (C++), GPU kernels, or SIMD would reduce overhead

This is a **correctness-focused parallel implementation** suitable for applications requiring reproducibility, with the understanding that speedup requires either much larger inputs or lower-overhead parallel mechanisms.
