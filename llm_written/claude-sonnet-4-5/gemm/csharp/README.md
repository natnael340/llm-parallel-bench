# GEMM Parallel Implementation

This project contains a parallel implementation of General Matrix Multiply (GEMM) in C# using the Task Parallel Library (TPL).

## Files

- **gemm_sequential.cs** - Original sequential baseline implementation
- **gemm_parallel.cs** - Parallel implementation with bounded concurrency
- **test_gemm.cs** - Differential test harness
- **run_gemm.cs** - Test runner with CLI
- **JUSTIFICATION.md** - Detailed explanation for non-technical readers
- **run_summary.txt** - Test results (correctness + determinism)
- **perf.txt** - Performance measurements

## Quick Start

Run all tests:
```bash
dotnet run --project run_gemm.cs
```

Run specific test suites:
```bash
dotnet run --project run_gemm.cs -- --test correctness
dotnet run --project run_gemm.cs -- --test determinism
dotnet run --project run_gemm.cs -- --test performance
```

## Results Summary

### Correctness
✅ All 9 test cases pass with bitwise-identical outputs
- Edge cases: 1×1, 2×2
- Small: 10×10, 15×20×25
- Medium: 100×100, 128×256×128
- Large: 512×512
- Special: alpha/beta scaling, identity matrix

### Determinism
✅ All 3 test cases produce identical hashes across 3 runs
- 128×128×128
- 256×256×256
- 512×512×512

### Performance (16-core machine)
- **256×256:** 2.59× speedup (16.2% efficiency)
- **512×512:** 3.99× speedup (24.9% efficiency)
- **1024×1024:** 5.91× speedup (36.9% efficiency)

## Implementation Strategy

The parallel implementation uses TPL's `Parallel.ForEach` to parallelize the innermost loop (m0) that processes row-tiles. Key features:

1. **Bounded concurrency:** Worker count capped at `Environment.ProcessorCount`
2. **Deterministic execution:** Fixed iteration order, no race conditions
3. **Sequential fallback:** Matrices smaller than 128×128 use sequential path
4. **Memory safety:** Each worker writes to disjoint row ranges

## Why Efficiency is Below 50%

Matrix multiplication is memory-bandwidth intensive. As more cores work simultaneously, they compete for the same memory bus, creating a bottleneck. The 5.91× speedup on 1024×1024 matrices is still excellent and demonstrates effective parallelization within hardware constraints.

See **JUSTIFICATION.md** for detailed explanation.
