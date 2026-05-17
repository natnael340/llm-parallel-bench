# GPT-5 Parallel GEMM – C++ Technical Report

**Implementation files:** `gemm_parallel_impl.cpp`, `gemm_seq.hpp`, `par_wrapper.cpp`
**Date analysed:** 2026-03-29

---

## 1. Parallelization Strategy

Parallelism is applied exclusively along the **M dimension** (rows of A / rows of C). The outer N and K loops remain sequential; the innermost M-block loop is parallelised with OpenMP:

```cpp
#pragma omp parallel for schedule(static) num_threads(threads)
for (int m0 = 0; m0 < m; m0 += MB) {
    int m1 = std::min(m0 + MB, m);
    Matrix Apack = packMatrix(A, k0, k1, m0, m1);
    int kb = k1 - k0;
    partialMatmul(Apack, Bpack, C, alpha, m0, n0, kb);
}
```

M-tiles produce writes to non-overlapping row ranges of C, eliminating any need for reduction or atomic updates. `Bpack` (the current NB×KB slice of B-transposed) is read-only and shared safely across all threads.

---

## 2. Concurrency Primitive

**OpenMP** exclusively.

- `#pragma omp parallel for schedule(static) num_threads(threads)`
- Thread count capped per tile:
  ```cpp
  int mBlocks = (m + MB - 1) / MB;
  int threads = std::min(omp_get_max_threads(), std::max(1, mBlocks));
  ```
- No `omp critical`, `omp atomic`, `omp reduction`, or tasks used.

---

## 3. Tiling / Blocking

Three-level blocking with default MB = NB = KB = 64:

```
for n0 in [0, n) step NB          [sequential]
  Bpack = packMatrix(Bt, k0, k1, n0, n1)   // NB×KB slice of B^T, shared
  for k0 in [0, k) step KB        [sequential]
    #pragma omp parallel for
    for m0 in [0, m) step MB      [OpenMP parallel]
      Apack = packMatrix(A, k0, k1, m0, m1) // MB×KB, thread-private
      partialMatmul(Apack, Bpack, C, alpha, m0, n0, kb)
```

- `Bpack` is hoisted outside the M-loop; all threads share one read-only pack per `(n0,k0)` tile
- `Apack` is thread-local; each iteration allocates its own MB×KB copy
- B is transposed once before tile loops for cache-friendly column access
- Inner kernel accumulates into a local `double s` before writing to C
- With 64×64 tiles: Apack + Bpack ≈ 64 KB working set per tile, targeting L2 residency

---

## 4. Determinism / Correctness

Preserved through **disjoint writes**: for any fixed `(n0, k0)` tile, each thread writes only to its exclusive row range `C[m0 : m0+MB]`. No two threads share a C row. The summation order over K within `partialMatmul` is identical to the sequential baseline. Output is **bit-identical** to sequential; the test harness verifies with zero tolerance (`tol = 0.0`).

---

## 5. Small-Input Fallback

```cpp
long long total_ops = (long long)m * (long long)n * (long long)k;
const long long SEQ_THRESHOLD = 200000; // ~2e5 MACs
if (total_ops <= SEQ_THRESHOLD) {
    gemm_seq_kernel(A, B, alpha, C, Cptr ? beta : 1.0, MB, NB, KB);
    return C;
}
```

Roughly a 58×58×58 cube or smaller routes to the sequential kernel, avoiding OpenMP thread-spawn overhead.

---

## 6. Performance

**Production binary (1024×1024×1024, `note`):**

| Metric | Value |
|--------|-------|
| Mean time | 265.3 ms ± 17.4 ms |
| Throughput | **8.09 GFLOPs** |

**Forced-parallel path (1000×1000×1000, `my_result.md`):**

| Implementation | Time | Throughput |
|----------------|------|-----------|
| Sequential | 17.91 s | 1.12 GFLOPs |
| Parallel | 5.99 s | 3.34 GFLOPs |
| **Speedup** | | **~3.0×** |

Paper reports **5.1× speedup** — the discrepancy from `my_result.md` (3×) may reflect the author's forced-parallel path measurement vs. the optimized benchmark run.

---

## 7. Notable Design Choices and Limitations

**Strengths:**
- Pragma placement is correct: inside the N-K body, parallelising only M
- Thread count bounded per tile prevents over-subscription on small problems
- B transposed once upfront for cache efficiency
- Clean namespace separation via `seq_wrapper.cpp` / `par_wrapper.cpp`

**Limitations:**
- **`std::vector<std::vector<double>>` layout** — heap-allocated rows prevent SIMD auto-vectorisation and add pointer indirection
- **Per-iteration `Apack` heap allocation inside the parallel region** — creates allocator pressure and potential malloc serialisation
- **256 fork-join cycles** for 1024-cube with NB=KB=64 (one `#pragma omp parallel for` per `(n0,k0)` tile)
- **No SIMD/intrinsics** — plain scalar inner loop
- **Sequential N and K loops** — for large K, M-only parallelism may leave cores underutilised
