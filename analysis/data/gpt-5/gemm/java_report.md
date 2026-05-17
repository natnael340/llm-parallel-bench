# GPT-5 Parallel GEMM – Java Technical Report

**Implementation files:** `algo_parallel.java`, `GemmBaseline.java`, `RunGemm.java`
**Date analysed:** 2026-03-29

---

## 1. Parallelization Strategy

The implementation parallelizes over the **2D (M, N) output-tile grid** of C. Each task owns exactly one output tile `[m0:m1) × [n0:n1)` and accumulates all K-block contributions into that region. The **K dimension is not parallelized** — it is iterated sequentially inside each task.

```java
for (int nbIdx = 0; nbIdx < nBlocks; nbIdx++) {
    for (int mbIdx = 0; mbIdx < mBlocks; mbIdx++) {
        tasks.add(() -> {
            for (int kbIdx = 0; kbIdx < kBlocksFinal; kbIdx++) {
                // accumulate k-block into C[m0:m1, n0:n1]
            }
            return null;
        });
    }
}
```

Total tasks = `mBlocks × nBlocks` (one per output tile). Distinct output tiles cover disjoint regions of C — no write conflicts, no synchronization on C elements needed.

---

## 2. Concurrency Primitive

A **`java.util.concurrent.ExecutorService` with a fixed-size thread pool**:

```java
int cores = Runtime.getRuntime().availableProcessors();
int maxWorkers = Math.max(1, cores);
ExecutorService pool = Executors.newFixedThreadPool(maxWorkers);
```

All tasks submitted via `pool.invokeAll(tasks)`, which blocks until every task completes. The pool is **one-shot** — created, used, and destroyed per `run(...)` call. `ForkJoinPool` was explicitly rejected because work-stealing changes per-run task execution order, risking floating-point non-determinism.

---

## 3. Tiling / Blocking

Three-level blocking with configurable MB, NB, KB (default 64; performance tests use 128). Loop nest inside each task:

```
for kbIdx in 0..kBlocks:               // K: sequential, inside task
    Bpack = Bpacks[nbIdx][kbIdx]       // shared read-only
    Apack = packMatrix(A, k0, k1, m0, m1)  // local copy
    partialMatmul(Apack, Bpack, C, alpha, m0, n0, kbLen)
```

`partialMatmul` accumulates a scalar `s` per `(i, j)` pair before writing to `C[m0+i][n0+j]`.

---

## 4. B-Tile Pre-Packing

B tiles are **pre-packed before any tasks are submitted** and shared read-only across all tasks with the same `(nbIdx, kbIdx)`:

```java
final double[][][][] Bpacks = new double[nBlocks][][][];
for (int nbIdx = 0; nbIdx < nBlocks; nbIdx++) {
    Bpacks[nbIdx] = new double[kBlocks][][];
    for (int kbIdx = 0; kbIdx < kBlocks; kbIdx++) {
        Bpacks[nbIdx][kbIdx] = packMatrix(Bt, k0b, k1b, n0, n1);
    }
}
```

B is first transposed to `Bt` (shape n×k) for cache-friendly access. All `mBlocks` tasks for a given `nbIdx` share the same B-pack, so B-packing cost is paid only once per `(nbIdx, kbIdx)`. A-tiles are packed locally inside each task (each is unique to one `(mbIdx, kbIdx)` combination).

---

## 5. Determinism / Correctness

Bit-exact determinism preserved through three mechanisms:
1. **Disjoint writes** — tasks write exclusively to their own `[m0:m1) × [n0:n1)` C region
2. **Fixed K-accumulation order** — K-blocks always iterated in strictly increasing `kbIdx` order; scalar `s` sums sequentially
3. **Fixed task partition** — tile boundaries fully determined by `(m, n, k, MB, NB, KB)`

`RunGemm.java` verifies determinism with SHA-256 hashes across 3 parallel runs. Bitwise equality between baseline and parallel checked with `Double.doubleToLongBits`. Beta pre-scaling applied once on the single-threaded path before tasks are launched.

---

## 6. Small-Input Fallback

```java
long work = (long) m * (long) n * (long) k;
final long SEQ_THRESHOLD = 500_000L;
if (work <= SEQ_THRESHOLD) {
    return GemmBaseline.run(A, B, alpha, C, 1.0, MB, NB, KB);
}
```

Roughly 79×79 square or smaller routes to sequential. At 128×128×128 (above threshold), parallel takes 63 ms vs. baseline 11 ms — a 5.7× regression due to `invokeAll` overhead.

---

## 7. Performance

**Correctness / small-scale timing (`run_summary.txt`):**

| Size | Baseline (ms) | Parallel (ms) | Speedup |
|------|--------------|---------------|---------|
| 128×128×128 | 11 | 63 | 0.17× (regression) |
| 256×256×256 | 33 | 18 | 1.83× |

**Headline speedup (`perf.txt`, MB=NB=KB=128):**

```
perf M=512 K=512 N=512 seq_ms=174 par_ms=31 speedup=5.613
```

**5.61× speedup** at 512×512×512 (16 output tasks on 4×4 tile grid).

**Sustained throughput (`note`, 1024×1024×1024):**

```
150.67 ms/run ± 22.03 ms → 14.253 GFLOPs
```

Paper reports **7.9× speedup** — consistent with the 5.6× at 512³ scaling upward at 1024³ with better tile utilization.

---

## 8. Notable Design Choices and Limitations

**Strengths:**
- B pre-packing amortized across all M-tasks — saves `mBlocks` redundant packs per `(nbIdx, kbIdx)`
- B transposed upfront for cache-friendly kernel access
- Explicit ForkJoinPool rejection for determinism guarantee
- SHA-256 hash determinism verification across runs

**Limitations:**
- **One-shot thread pool per call** — `newFixedThreadPool` + `shutdown` overhead on every invocation
- **All B-packing runs serially** before first task starts — no pipelining
- **Hardcoded fallback threshold** — does not adapt to core count or JVM startup cost
- **Heap allocation pressure** — per-task A-packs + full upfront B-pack table → GC jitter (explains 22 ms σ)
- **No SIMD / Vector API** — scalar dot product relies on JIT auto-vectorization
