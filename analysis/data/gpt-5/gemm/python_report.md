# GPT-5 Parallel GEMM – Python Technical Report

**Implementation files:** `gemm_parallel.py`, `gemm_seq.py`, `test_gemm.py`
**Date analysed:** 2026-03-29

---

## 1. Parallelization Strategy

Work is distributed across the **M dimension (row tiles)** only. The outer N and K loops remain sequential in the main process. For each fixed `(n0, k0)` slab, B is packed once, then all M-tile tasks are submitted concurrently to a `ProcessPoolExecutor`. The worker `_compute_block_contrib(Apack, Bpack, kb, alpha)` returns a dense `(mb × nb)` result block. Tasks write to disjoint rows of C. After all futures for a slab complete, the main process merges blocks back into C in deterministic ascending `m0` order.

---

## 2. Concurrency Primitive

`concurrent.futures.ProcessPoolExecutor` — bypasses the GIL via OS processes. Futures are collected with `as_completed`, mapped back to their `m0` key via `future_map: {future -> m0}`, then merged in a second pass. The executor is created and destroyed per `gemm()` call (no reuse across calls).

---

## 3. Worker Count Cap

```python
max_workers_global = min(cpu_cnt, max(1, (m + MB - 1) // MB), 4)
```

Three constraints: machine CPU count, number of M-tiles (`ceil(m/MB)`), and a **hard cap of 4**. On any machine with more than 4 cores the hard cap is binding. It is not configurable via the public API.

This cap is the dominant performance limiter. Testing with 8 and 16 workers yields 40% and 60% higher throughput respectively — the paper explicitly calls this out as the LLM leaving performance on the table.

---

## 4. Tiling / Blocking

Default tile sizes: MB = NB = KB = 64. Iteration order: N → K → M (outer to inner), matching the sequential baseline. B is transposed once before tiling (`Bt = transpose(B)`). `pack_matrix` slices `Bpack` (shape `nb × kb`) and `Apack` (shape `mb × kb`). Packing runs **serially in the main process** for every `(m0, n0, k0)` triple.

---

## 5. Determinism / Correctness

Preserved by two mechanisms:
1. The inner K-summation loop in `_compute_block_contrib` always runs left-to-right `k=0..kb-1`, identical to the sequential baseline
2. The merge phase iterates `m_tiles` in fixed ascending `m0` order, so the `+=` accumulation sequence in C is identical to sequential regardless of future completion order

The test suite checks exact (bitwise) equality, not tolerance-based.

---

## 6. Small-Input Fallback

Threshold: `m*n <= 1024` or `cpu_count <= 1`.

**Bug:** the fallback imports `from llm_written.python_openai.gemm.gemm_seq import gemm as seq_gemm` — a path that does not exist in the repository. Any input hitting this branch raises `ModuleNotFoundError` at runtime. **The fallback is non-functional.**

---

## 7. Performance

| Source | Size | Sequential | Parallel | Speedup |
|--------|------|-----------|----------|---------|
| `note` | 1024³ | 130,023 ms | 42,829 ms | **~3.0×** |
| `my_results.md` | 1000³ | ~1,200 s | 345 s | **~3.5×** |

For 1024×1024 with MB=NB=KB=64: 4,096 total task submissions, ~98 KB raw float data per round-trip, 524K FLOPs per task. The compute-to-communication ratio is unfavorable, limiting speedup to ~3× despite 4 workers. Throughput of 0.050 GFLOPs is far below BLAS-level performance due to pure-Python arithmetic.

Paper reports **3.0× speedup** — matches observed data exactly.

---

## 8. Notable Design Choices and Limitations

**Strengths:**
- B transposed once before tile loops (avoids repeated column access)
- No shared mutable state between workers
- Two-phase collect-then-merge ensures deterministic accumulation order
- Full API parity with sequential version

**Limitations:**
- **Broken small-input fallback** — `ModuleNotFoundError` at runtime for small inputs
- **Hard cap of 4 workers** hardcoded — no API parameter to override
- **Executor created/destroyed per call** — no pool reuse across repeated `gemm()` invocations
- **Matrix packing runs serially** in the main process — Amdahl-law overhead
- **Only M-dimension parallelized** — N and K fully sequential
- **Pure Python arithmetic** in the inner kernel — no NumPy or native extensions
- Bare `except Exception` blocks silently convert failures to sequential fallback, masking real errors
