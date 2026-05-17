# GPT-5 Parallel GEMM – C# Technical Report

**Implementation files:** `algo_parallel.cs`, `run_gemm.cs`
**Date analysed:** 2026-03-29

---

## 1. Parallelization Strategy

The implementation uses a three-level tiled blocking scheme. The outer two loops over N and K tiles remain strictly serial; only the **M dimension** is parallelized via `Parallel.For`:

```
for n0 in [0, n, step NB]           // serial
  for k0 in [0, k, step KB]         // serial
    Bpack = PackMatrix(Bt, k0, k1, n0, n1)   // shared, read-only
    Parallel.For(0, tileCount, po, t =>      // parallel over M-tiles
        Apack = PackMatrix(A, k0, k1, m0, m1) // private per worker
        PartialMatmul(Apack, Bpack, C, alpha, m0, n0, kb)
    )
```

For a fixed `(n0, k0)` tile pair, `tileCount = ceil(m / MB)` M-tiles are fully independent: each writes to a distinct non-overlapping horizontal stripe of C (rows `[m0, m1)`), and all tasks share the pre-packed, read-only `Bpack`. Tile start indices are pre-computed into `mStarts[]` to avoid repeated arithmetic in the lambda.

---

## 2. Concurrency Primitive

Exclusively `Parallel.For` from the .NET Task Parallel Library. A `ParallelOptions` instance with `MaxDegreeOfParallelism = min(ProcessorCount, maxDegree)` is constructed once and reused. No `Task`, PLINQ, or concurrent collections are used.

---

## 3. Work-Stealing Scheduler

`Parallel.For` feeds work items to the .NET thread pool's work-stealing scheduler. Degree is capped at `Environment.ProcessorCount`. Each `Parallel.For` call produces an implicit join barrier; with NB=KB=64 on a 1024³ matrix there are 256 such barriers, adding ~256 µs total overhead against ~200 ms of compute.

---

## 4. Tiling / Blocking

- **Check runs:** MB = NB = KB = 64
- **Perf runs:** MB = NB = KB = 128
- Loop order: N → K → parallel(M)
- `PackMatrix` copies sub-regions into compact jagged arrays via `Array.Copy` for cache-friendly access
- `PartialMatmul` accumulates into a local scalar `s` before writing once to `C[i][j]`

---

## 5. Determinism / Correctness

Guaranteed by two mechanisms:
- **Disjoint write ownership** — no two workers share a row of C
- **Serial K-reduction** — the K loop is unchanged, so summation order over K-tiles is identical to the sequential baseline, giving bit-for-bit identical results

Verified by exact-equality checks and FNV-1a hashing across 3 repeated parallel runs for all test sizes (1×1×1 through 256×256×256).

---

## 6. Small-Input Fallback

```csharp
long approxFlops = (long)m * n * k;
if (approxFlops <= smallNFlops)  // default 1,000,000
    return RunSequential(...);
```

The beta scaling is applied before this check; `RunSequential` is called with `beta=1.0` to prevent double-scaling.

---

## 7. Performance

| Matrix size | Sequential | Parallel | Speedup |
|-------------|-----------|----------|---------|
| 384×384×384 | 334.6 ms | 124.5 ms | **2.69×** |
| 1024×1024×1024 | 1967.97 ms | 603.38 ms | **3.26×** (3.56 GFLOPs/s parallel) |

Parallel efficiency ~41% relative to 8 effective cores; substantially lower against 64 physical cores, suggesting memory-bandwidth saturation dominates.

Paper reports **3.3× speedup** — consistent with these observations.

---

## 8. Notable Design Choices and Limitations

**Strengths:**
- M-only parallelism avoids any synchronization inside the parallel region
- Pre-packed shared `Bpack` eliminates redundant packing
- Explicit `MaxDegreeOfParallelism` bound prevents over-subscription
- Nullable reference annotations for safety

**Limitations:**
- Jagged `double[][]` layout (pointer chasing, inhibits vectorization/SIMD)
- Per-tile heap allocation causing GC pressure
- No SIMD intrinsics
- 256 serial barriers (one per `Parallel.For` call) prevent K-tile pipelining
- Single-run benchmark timing (high variance)
