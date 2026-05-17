# GEMM Parallel Implementation

This directory contains a parallel implementation of GEMM (General Matrix Multiply) in Java.

## Files

### Core Implementation
- **Gemm.java** - Sequential baseline implementation
- **GemmParallel.java** - Parallel implementation using ForkJoinPool

### Testing
- **TestGemm.java** - Comprehensive test harness with correctness and determinism tests
- **RunGemm.java** - Simple test runner that executes all tests

### Documentation
- **JUSTIFICATION.md** - Detailed explanation of parallelization strategy (600-1100 words)
- **run_summary.txt** - Test results summary (correctness + determinism)
- **perf.txt** - Performance benchmark results

## Quick Start

### Compile
```bash
javac Gemm.java GemmParallel.java TestGemm.java RunGemm.java
```

### Run All Tests
```bash
java RunGemm
```

### Run Specific Test Suites
```bash
# Correctness tests only
java TestGemm correctness

# Determinism tests only
java TestGemm determinism

# Performance tests only
java TestGemm performance

# All tests
java TestGemm all
```

## Results Summary

### Correctness
- ✅ 10/10 tests passed
- Covers edge cases (1×1, 1×n, m×1), small (8×8), medium (128×128), large (512×512)
- Tests alpha/beta parameters and accumulation modes

### Determinism
- ✅ 2/2 tests passed
- Multiple runs produce identical results (bitwise equality)
- Hash verification confirms deterministic behavior

### Performance
- Matrix size: 512×512
- Sequential time: ~0.24 seconds
- Parallel time: ~0.03 seconds
- **Speedup: ~7.7×**
- Cores: 16
- **Parallel efficiency: ~48%**

## Implementation Strategy

The parallel version restructures the computation to parallelize over output tiles:

1. **Split**: Divide output matrix C into tiles (default 64×64)
2. **Assign**: Each worker computes one output tile independently
3. **Accumulate**: Within each tile, k-contributions are accumulated in fixed order
4. **Merge**: No explicit merge needed; workers write to non-overlapping regions

This approach ensures:
- **Correctness**: Exact match with sequential version
- **Determinism**: Same input always produces same output
- **Performance**: Good speedup on multi-core systems

## Key Features

- Bounded parallelism (respects available CPU cores)
- Sequential fallback for small matrices (< 256×256)
- Deterministic floating-point accumulation
- Preserves original API (drop-in replacement)
- Handles all edge cases (null C, alpha=0, beta≠1)

## See Also

- **JUSTIFICATION.md** - Full technical explanation for non-technical readers
- **run_summary.txt** - Detailed test results
- **perf.txt** - Performance measurements
