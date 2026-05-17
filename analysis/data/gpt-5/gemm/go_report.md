# GPT-5 Parallel GEMM – Go Technical Report

**Implementation files:** `gemm_parallel.go`, `gemm_parallel_test.go`
**Date analysed:** 2026-03-29

---

## 1. Parallelization Strategy

Parallelism is introduced exclusively along the **M-dimension tile loop**. The outer N and K loops remain strictly sequential. For each fixed `(n0, k0)` tile pair, the range `[0, m)` is subdivided into MB-height chunks. Each chunk `[m0, m1)` constitutes one independent job. Workers write exclusively to the row stripe `C[m0:m1][n0:n1]`. Accumulation across K-tiles into the same output cell always occurs in ascending `k0` order, matching the sequential version.

---

## 2. Concurrency Primitive

A **bounded goroutine worker pool** coordinated with two Go channels:

```go
mJobs := make(chan [2]int)          // unbuffered job channel
workers := runtime.GOMAXPROCS(0)
if workers > mChunks { workers = mChunks }

done := make(chan struct{})

for w := 0; w < workers; w++ {
    go func() {
        for mm := range mJobs {
            Apack := packMatrix(A, k0, k1, mm[0], mm[1])
            partialMatmul(Apack, Bpack, C, alpha, mm[0], n0, kb)
        }
        done <- struct{}{}
    }()
}
for m0 := 0; m0 < m; m0 += MB { mJobs <- [2]int{m0, m1} }
close(mJobs)
for w := 0; w < workers; w++ { <-done }
```

- `mJobs` is **unbuffered** — producer blocks on each send (natural back-pressure)
- `done` acts as a **counting barrier** — each worker sends one token after draining; caller collects `workers` tokens before advancing to the next `(n0, k0)` tile
- No `sync.WaitGroup`, no mutexes, no atomics — pure channel synchronization
- Pool is **re-created per `(n0, k0)` tile**, not persisted across the full `Gemm` call

---

## 3. Tiling / Blocking

Default MB = NB = KB = 64. Loop order:

```
for n0 in [0, n) step NB    // N-tile (sequential)
  for k0 in [0, k) step KB  // K-tile (sequential)
    for m0 in [0, m) step MB  // M-tile (parallel via worker pool)
```

B is fully transposed once before tile loops (`Bt := transpose(B)`) for cache-friendly row-stride access in `partialMatmul`. `packMatrix` constructs zero-copy sub-slice views (only `O(rows)` slice headers allocated per tile — no data copied).

---

## 4. Determinism / Correctness

- **Disjoint writes** — concurrent workers have non-overlapping `m0` values (separated by MB); no two goroutines write to the same element
- **Fixed K summation order** — K-tile loop is sequential; for any C[i][j], contributions arrive in strictly increasing `k0` order, identical to sequential baseline → **bit-reproducible results**
- **Beta pre-scaling** — C scaled by beta in a single-threaded step before any worker is launched

`TestDeterminism` runs `Gemm` twice and checks exact equality (`tol == 0`). `TestGemmMatchesSequential` compares parallel vs. sequential with `tol = 1e-12` across 7 configurations (1×1 to 128×96).

---

## 5. Small-Input Fallback

```go
const smallThreshold = 10
if m*n <= smallThreshold || m == 1 || n == 1 || k == 1 {
    return gemmSequential(A, B, alpha, C, 1.0, MB, NB, KB)
}
```

Threshold `m*n <= 10` is extremely aggressive — practically no realistic input reaches sequential. A commented-out alternative of `1_000` is present, indicating this was tuned downward. Inputs in the range `11 ≤ m*n ≤ ~500` would likely run faster sequentially but are routed to the parallel path.

---

## 6. Performance

**1024×1024×1024 (20 iters, 5 repeats, `note`/`perf`):**

| | Sequential | Parallel | Speedup |
|-|-----------|----------|---------|
| Wall time | 2978.79 ms | 402.48 ms ± 11.73 ms | **7.40×** |
| Throughput | 0.721 GFLOPs | 5.336 GFLOPs | **7.40×** |

**1000×1000×1000 (`my_result.md`):**

| Sequential | Parallel | Speedup |
|-----------|----------|---------|
| 29.480 s (0.678 GFLOPs) | 8.712 s (2.296 GFLOPs) | **~3.38×** |

The reduced speedup at 1000³ vs 1024³ is consistent with non-power-of-two tiling: last tiles are smaller, worsening load balance.

Paper reports **7.4× speedup** — matches exactly.

---

## 7. Notable Design Choices and Limitations

**Strengths:**
- M-only parallelism avoids all synchronization (no reduction needed)
- Channel-based worker pool is idiomatic Go — no external dependencies
- Full B transpose upfront for cache-friendly access
- Zero-copy `packMatrix` via slice headers

**Limitations:**
- **Pool re-created per `(n0, k0)` tile** — 256 goroutine spawns/teardowns at 1024³ with 64-wide tiles; acceptable but suboptimal
- **Near-zero fallback threshold** (`m*n ≤ 10`) — essentially bypassed for all practical inputs
- **Unbuffered `mJobs` channel** — serializes dispatch; a buffered channel sized to `workers` would allow overlap
- **Slice-of-slices layout** — scattered heap rows add TLB pressure vs. flat `[]float64`
- **No SIMD guarantee** — inner loop is plain Go; vectorization is compiler-dependent
