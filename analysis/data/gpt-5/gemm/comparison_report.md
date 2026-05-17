# GPT-5 Parallel GEMM — Paper vs. Implementation Comparison

**Date:** 2026-03-29
**Source:** `llm_written/gpt-5/gemm/` (6 languages)

---

## Summary Table

| Claim in paper | Verified? | Notes |
|----------------|-----------|-------|
| All 6 languages achieved meaningful speedup | **YES** | All > 1× at large scale |
| All preserve numerical determinism | **YES** | Disjoint writes + fixed K order in all |
| All have small-input fallback | **PARTIAL** | Python fallback is broken (wrong import path) |
| Five languages parallelize M dimension | **YES** | Go, C++, Rust, C#, Python all parallelize M |
| Java is sole exception: distributes (M,N) tile pairs | **YES** | Java uses `mBlocks × nBlocks` task grid |
| Go: 7.4× via channel-based worker pool | **YES** | Measured 7.40× at 1024³ |
| Java: 7.9× with ExecutorService + B pre-packing | **PARTIAL** | 5.6× at 512³, 14.25 GFLOPs at 1024³ — paper's 7.9× not directly reproducible from perf.txt |
| C++: 5.1× with OpenMP `parallel for` on M-loop | **PARTIAL** | 3.0× in `my_result.md`; 8.09 GFLOPs from `note` — speedup ratio depends on benchmark run |
| Rust: 4.5× via scoped threads + clone-local-merge | **YES** | Measured 4.50× at 1024³ |
| C#: 3.3× via TPL work-stealing | **PARTIAL** | 2.69× at 384³, 3.26× at 1024³ — consistent with 3.3× |
| Python: 3.0× with hard cap of 4 workers | **YES** | Measured ~3.0× at 1024³ |
| Python: 8/16 workers yield 40%/60% higher throughput | **YES** | Explicitly noted in `my_results.md` |

---

## Language-by-Language Analysis

### Go — 7.4× ✓

**Paper:** "Go achieves 7.4× using a channel-based worker pool, as goroutine dispatch overhead is low enough to allow fine-grained tile parallelism without excessive synchronization."

**Implementation confirms:**
- Uses unbuffered `mJobs` channel + `done` counting barrier — textbook channel-based worker pool
- Pool sized to `runtime.GOMAXPROCS(0)` workers, re-created per `(n0, k0)` tile
- Measured 7.40× at 1024³ — exact match

**Discrepancy:** The paper describes "fine-grained tile parallelism." In practice the pool is re-created 256 times (one per N×K tile pair at 64-wide tiles), which is coarser than it sounds. The 7.4× result holds because goroutine creation overhead is genuinely negligible compared to per-tile compute.

---

### Java — 7.9× (PARTIAL)

**Paper:** "Java achieved 7.9× using a fixed thread pool with ExecutorService. B tiles are pre-packed and shared read-only across tasks, while each task packs its own A tile locally."

**Implementation confirms:**
- Fixed `ExecutorService` thread pool (`newFixedThreadPool(availableProcessors)`)
- B tiles pre-packed into `Bpacks[nbIdx][kbIdx]` before task submission — shared read-only ✓
- A tiles packed locally per task ✓
- `pool.invokeAll(tasks)` for barrier synchronization ✓

**Discrepancy:** The paper says Java is the "sole exception" distributing over `(M,N)` tile pairs. This is **confirmed** — task count = `mBlocks × nBlocks`, with K iterated sequentially inside each task. However, the paper's "7.9×" figure comes from the 512×512 benchmark (`5.6×`) extrapolated or measured at a larger size. The `perf.txt` headline is `5.613×` at 512³; the `note` shows 14.25 GFLOPs at 1024³ without a sequential comparison point, so the 7.9× cannot be directly verified from available artifacts.

---

### C++ — 5.1× (PARTIAL)

**Paper:** "C++ achieved 5.1× with OpenMP `parallel for` directives on the innermost M-loop, parallelizing across M-blocks within each (N, K) tile iteration."

**Implementation confirms:**
- `#pragma omp parallel for schedule(static) num_threads(threads)` on the M-block loop ✓
- N and K loops remain sequential ✓
- Thread count bounded to `min(omp_get_max_threads(), mBlocks)` ✓

**Discrepancy:** `my_result.md` reports only ~3.0× speedup at 1000³ (forced parallel). The `note` shows 8.09 GFLOPs throughput but provides no sequential baseline, making the speedup ratio implicit. The paper's 5.1× is plausible on the production benchmark runner but not directly confirmed by the committed artifacts. The implementation is structurally correct for the described approach.

---

### Rust — 4.5× ✓

**Paper:** "Rust attained 4.5× via scoped threads and a clone-to-local-merge strategy that avoids shared mutable state entirely."

**Implementation confirms:**
- `std::thread::scope` (not Rayon, despite Rayon in `Cargo.toml`) ✓
- Clone-to-local-merge: each worker clones its row band, merges via `sort_by_key` + sequential write-back ✓
- No `Arc`, no `Mutex`, no atomics in hot path ✓
- Measured 4.50× at 1024³ — exact match ✓

**Additional detail not in paper:** JUSTIFICATION.md provides explicit reasoning for rejecting Rayon (timing-dependent float order), atomics, locks, and K-block wavefronts. The determinism-first design constraint directly explains the choice of static band assignment over work-stealing.

---

### C# — 3.3× ✓ (within range)

**Paper:** "C# benefits from the Task Parallel Library's work-stealing scheduler, yielding 3.3×."

**Implementation confirms:**
- `Parallel.For` with `ParallelOptions { MaxDegreeOfParallelism = ProcessorCount }` ✓
- M dimension only parallelized; N and K loops serial ✓
- Measured 2.69× at 384³ and 3.26× at 1024³ — consistent with 3.3× at scale ✓

**Additional detail:** The paper attributes performance to the "work-stealing scheduler." This is accurate — `Parallel.For` internally uses the .NET thread pool's work-stealing queue. However, the implementation creates 256 separate `Parallel.For` calls (one per N×K tile), each with an implicit join barrier, slightly reducing the scheduler's ability to steal across tile boundaries.

---

### Python — 3.0× ✓

**Paper:** "Python achieved 3.0×, though performance was limited by a hard cap of four worker processes. Testing with 8 and 16 workers yielded 40% and 60% higher throughput respectively."

**Implementation confirms:**
- `ProcessPoolExecutor` with `max_workers = min(cpu_cnt, m_tiles, 4)` — hard cap of 4 ✓
- Measured ~3.0× at 1024³ ✓
- `my_results.md` explicitly notes higher throughput at 8 and 16 workers ✓

**Bug not mentioned in paper:** The small-input fallback imports `from llm_written.python_openai.gemm.gemm_seq import gemm` — a non-existent module path. Any input with `m*n ≤ 1024` raises `ModuleNotFoundError` at runtime. The paper's benchmarks only tested large inputs, so this bug was not caught.

---

## Overall Assessment

### What the paper gets right

1. **Parallelization dimension** — Correctly identifies M-only for Go, C++, Rust, C#, Python and `(M,N)` tile pairs for Java
2. **Concurrency primitives** — Correctly identifies channel-based pool (Go), ExecutorService (Java), OpenMP (C++), scoped threads (Rust), TPL (C#), ProcessPoolExecutor (Python)
3. **B pre-packing in Java** — Correctly described as shared read-only across tasks
4. **Clone-to-local-merge in Rust** — Accurately describes the strategy; correctly notes no shared mutable state
5. **Python worker cap** — Correctly identifies 4-worker limit and its performance consequence
6. **Speedup figures** — Go (7.4×), Rust (4.5×), Python (3.0×) match the benchmarks exactly

### What the paper understates or omits

1. **Java's 7.9× is at a specific scale** — The perf artifacts show 5.6× at 512³; the paper's 7.9× is plausible at a larger benchmark size but isn't directly confirmed by `perf.txt`
2. **C++'s `my_result.md` shows only 3×** — The paper's 5.1× likely reflects the production benchmark environment, not the committed artifacts
3. **Python's fallback is broken** — The non-existent import path is a correctness bug that the paper does not mention
4. **Rust's fallback threshold bug** — The threshold (131,072) is below the default single-tile workload (262,144), causing a regression for 64×64×64 inputs; not mentioned
5. **Go's pool re-creation** — 256 goroutine pool creations per large GEMM call is a subtle overhead the paper glosses over as "low dispatch overhead"

### Recurring limitation identified by paper

The paper's conclusion — "GPT-5 does not reliably reason about *where within a loop nest* parallelism should be introduced to minimize synchronization frequency" — is **well-supported** by the evidence:

- C# creates 256 `Parallel.For` barriers (one per N×K tile) rather than one outer `Parallel.For` over M
- Go re-creates its worker pool 256 times rather than maintaining a persistent pool
- Python re-creates the executor per call
- Rust's static band assignment is correct but performs 256 tile allocations per worker inside the parallel region

In all cases the *strategy* (M-dimension, disjoint writes, K-sequential) is correct and consistent. The *placement* of the concurrency primitive within the loop nest is suboptimal in every language except Java, where the `(M,N)` task grid provides broader coverage.
