# Parallel GEMM Implementation

This project contains a parallelized implementation of GEMM (General Matrix Multiply) in Go.

## Files

### Core Implementation
- **gemm_common.go** - Shared utilities (matrix types, validation, packing, transpose)
- **gemm_sequential.go** - Sequential baseline implementation
- **gemm_parallel.go** - Parallel implementation using bounded goroutines

### Testing & Benchmarking
- **run_gemm.go** - Main test runner (correctness + determinism tests)
- **run_perf.go** - Performance benchmark runner

### Documentation
- **JUSTIFICATION.md** - Detailed explanation of parallelization strategy (600-1100 words)
- **REQUEST.md** - Original parallelization request and constraints
- **run_summary.txt** - Test results (correctness + determinism)
- **perf.txt** - Performance benchmark results

## Quick Start

### Run All Tests (Correctness + Determinism)
```bash
go run gemm_common.go gemm_sequential.go gemm_parallel.go run_gemm.go
```

### Run Performance Benchmarks
```bash
go run gemm_common.go gemm_sequential.go gemm_parallel.go run_perf.go
```

## Results Summary

### Correctness
✅ All 10 test cases pass (edge cases, small, medium, large matrices)

### Determinism
✅ Three runs produce identical outputs (verified via SHA256 hash)
- medium_128x128: Hash a6ffd63385e99556
- large_256x256: Hash 0178626f03617e87

### Performance (16 cores)
- **256×256:** 2.28× speedup (72.44ms → 31.71ms)
- **512×512:** 2.98× speedup (460.06ms → 154.13ms)

## Implementation Strategy

**Approach:** Parallelize the innermost m-loop (row blocks) while keeping n-loop and k-loop sequential.

**Key Features:**
- Bounded concurrency (capped at runtime.NumCPU())
- Deterministic accumulation order (WaitGroup barriers between iterations)
- No data races (each goroutine writes to disjoint rows)
- Sequential fallback for small matrices (m*n < 10000)

**Why This Works:**
- For each (n-block, k-block) pair, all m-blocks are independent
- Different m-blocks write to different rows of C
- Fixed iteration order ensures deterministic results
- Goroutines complete in parallel but synchronize before next iteration

See **JUSTIFICATION.md** for detailed explanation and alternatives considered.

## Algorithm Overview

GEMM computes: **C := alpha * A * B + beta * C**

The implementation uses blocked matrix multiplication:
1. Transpose B for better cache locality
2. Partition matrices into blocks (default 64×64)
3. Triple-nested loop: n-blocks (outer), k-blocks (middle), m-blocks (inner)
4. **Parallel execution:** m-blocks within each (n, k) iteration
5. Each m-block computes a partial result and accumulates into C

## Requirements

- Go 1.16 or later
- No external dependencies (pure Go)

## License

This is a demonstration project for parallelization techniques.
