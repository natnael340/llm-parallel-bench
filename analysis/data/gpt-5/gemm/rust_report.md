# GPT-5 Parallel GEMM – Rust Technical Report

**Implementation files:** `algo_parallel.rs`, `algo_seq.rs`, `main.rs`
**Date analysed:** 2026-03-29

---

## 1. Parallelization Strategy

Parallelism is applied exclusively across the **M dimension** (rows of output matrix C). The full set of M rows is divided into `mb`-sized tiles, grouped into contiguous **bands** — one band per worker thread:

```rust
let m_chunks = (m + mb - 1) / mb;
let num_threads = max_threads.min(m_chunks.max(1));
let chunks_per_thread = (m_chunks + num_threads - 1) / num_threads;

for t in 0..num_threads {
    let start_chunk = t * chunks_per_thread;
    let end_chunk = ((t + 1) * chunks_per_thread).min(m_chunks);
    if start_chunk < end_chunk { bands.push((start_chunk, end_chunk)); }
}
```

Within each band a worker iterates the same three-level tiled loop as the sequential baseline: outer N-tiles, middle K-blocks, inner M-tiles. N and K are **not parallelized**. The transposed B matrix (`bt`) is shared read-only across all workers via a scoped borrow.

---

## 2. Concurrency Primitive

**`std::thread::scope`** from Rust's standard library (stable since 1.63). No third-party crate is used. `rayon` is in `Cargo.toml` but **explicitly not used**.

```rust
thread::scope(|scope| {
    let mut handles = Vec::with_capacity(bands.len());
    for (start_chunk, end_chunk) in bands.iter().copied() {
        let handle = scope.spawn(move || {
            // ... worker body ...
            (row_indices, c_rows)   // owned data returned on join
        });
        handles.push(handle);
    }
    for h in handles {
        let (idxs, rows) = h.join().unwrap();
        for (i, r) in idxs.into_iter().zip(rows.into_iter()) {
            collected.push((i, r));
        }
    }
});
```

`thread::scope` enforces all threads terminate before the scope exits, allowing workers to hold non-`'static` borrows without `Arc`.

---

## 3. Shared State Strategy — Clone-to-Local, Merge-on-Join

No `Arc`, no `Mutex`, no atomics in the hot path:

- **A and `bt`** — shared as immutable borrows (`&Matrix`) at zero cost
- **C** — each worker clones only its assigned rows into private `Vec<Vec<f64>>`; no concurrent write to C
- **Merge** — after all joins, collected `(row_index, row_data)` pairs are sorted then written back:

```rust
collected.sort_by_key(|(i, _)| *i);
for (i, row) in collected.into_iter() { c[i] = row; }
```

JUSTIFICATION.md explicitly rejects Rayon (timing-dependent float order breaks determinism), atomics (contention + non-deterministic accumulation), and locks (synchronization on overlapping tile writes).

---

## 4. Tiling / Blocking

Default MB = NB = KB = 64. Loop nest order per worker:

```
for N-tiles (n0..n, step nb):        [sequential]
  for K-blocks (k0..k, step kb):     [sequential]
    pack bpack from bt[k0..k1][n0..n1]
    for M-tiles (worker's band only): [parallel]
      pack apack from a[m0..m1][k0..k1]
      tile[mb][nb] = 0
      partial_matmul_add_into(apack, bpack, tile, alpha, kb)
      accumulate tile into c_rows[local_offset][n0..n1]
```

B is pre-transposed once before tile loops for cache-friendly row-stride access. Workers write into local scratch tiles (relative indices) rather than directly into global C — this avoids data races without any locking.

Inner kernel:
```rust
for (i_off, aik) in a.iter().enumerate() {
    for (j_off, bjk) in b.iter().enumerate() {
        let mut s = 0.0;
        for k in 0..kb { s += aik[k] * bjk[k]; }
        c_tile[i_off][j_off] += alpha * s;
    }
}
```

---

## 5. Determinism / Correctness

Three mechanisms guarantee bit-exact reproducibility:
1. **Fixed thread-to-data assignment** — band mapping is deterministic from `(m, mb, num_threads)`
2. **Fixed intra-worker accumulation order** — K-blocks ascending, scalar dot product sequential; no FP reductions span thread boundaries
3. **Fixed merge order** — `sort_by_key` imposes total row-index order independent of thread completion order

Verified by `check_equal` (element-wise `f64::to_bits()`) and FNV-1a hash across 3 parallel runs. All cases in `run_summary.txt` report `det=true`.

---

## 6. Small-Input Fallback

```rust
let total_ops = m * n * k;
if total_ops <= 64 * 64 * 32 {   // 131,072 operations
    // inline sequential tiled loops
    return Ok(c);
}
```

**Known bug:** at default tile size 64×64×64, `total_ops = 262,144 > 131,072`, so the degenerate single-M-tile case enters the parallel path and regresses 1.44× (19.98 ms parallel vs 13.85 ms sequential for 64³). The threshold should be at least `64³ = 262,144` or short-circuit when `bands.len() == 1`.

Also: B transpose runs unconditionally before the fallback check — wasted work for sub-threshold inputs.

---

## 7. Performance

| Matrix size | Sequential | Parallel | Speedup |
|-------------|-----------|----------|---------|
| 256×256×256 | 1104.84 ms | 311.88 ms | **3.54×** |
| 1024×1024×1024 | 1852.50 ms | 411.70 ms | **4.50×** |

1024³: 1.16 GFLOPs seq → 5.22 GFLOPs parallel. ~56% parallel efficiency on 8-core machine.

Cross-language comparison from `note`:

| Language | Mechanism | Speedup |
|----------|-----------|---------|
| Go | Goroutines | 7.4× |
| Rust | `thread::scope` | **4.5×** |
| Java | Executor | 1.05× |
| C++ | OpenMP | 0.87× |

Paper reports **4.5× speedup** — matches exactly.

---

## 8. Notable Design Choices and Limitations

**Strengths:**
- `thread::scope` eliminates `Arc` overhead — non-`'static` borrows at zero cost
- Clone-local-merge avoids all synchronization in the hot path
- Static band assignment is determinism-preserving and load-balanced for uniform work
- Four parallelism alternatives explicitly rejected with technical justification in JUSTIFICATION.md

**Limitations:**
- **Row cloning** — each worker allocates ~1 MB before compute begins (1024×1024, 8 threads); ~2% overhead at large scale but disproportionate for wide, compute-light workloads
- **Tile buffer re-allocated inside inner loop** — 256 allocations per worker at 1024³; could be pre-allocated and zeroed in-place
- **Fallback threshold mismatched** with default tile size — single-tile parallel path regresses
- **Sequential final merge** — O(m×n) write-back limits scalability at extreme thread counts
- **No SIMD** — scalar inner loop; vectorization is compiler-dependent
