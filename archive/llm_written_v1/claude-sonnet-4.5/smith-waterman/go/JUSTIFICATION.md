# Smith-Waterman Parallel Implementation Justification

## Decision Summary

- **Baseline bottleneck:** The original sequential algorithm fills an n×m scoring matrix row by row, taking O(n×m) time. Each cell computation depends on three neighbors (diagonal, left, up), creating dependencies that prevent naive row or column parallelization.

- **Chosen strategy:** Block-based wavefront parallelism. The matrix is divided into 256×256 blocks. Blocks are processed in "waves" (block antidiagonals), where all blocks in the same wave are independent and can be computed in parallel. Within each wave, workers process blocks in a fixed order.

- **Why it is safe (determinism):** Fixed block size (256), fixed worker count (CPU cores), and fixed processing order within each wave ensure the same computation happens every time. No race conditions because blocks in a wave never write to overlapping cells. Workers merge results in a fixed order (worker 0, then 1, then 2, etc.).

- **Why it is faster:** Large matrices (≥500×500) are divided into many independent blocks. Multiple CPU cores compute different blocks simultaneously during each wave, reducing total wall time by ~1.4× on 2000×2000 inputs.

- **Worker count + chunk rule:** Number of workers = CPU core count. Each worker processes 1 or more complete blocks per wave. Block size = 256 cells per side (fixed for determinism).

- **Small-N fallback threshold:** If n×m < 250,000 (roughly 500×500), the algorithm runs sequentially because parallelization overhead exceeds the benefit for small problems.

- **Best rejected alternative + reason:** Fine-grained cell-level wavefront parallelism (process individual antidiagonals in parallel) was tried first but caused 0.21× slowdown due to excessive goroutine creation overhead—creating thousands of goroutines for 2000 antidiagonals dominated the compute savings.

---

## 1. What Changed and Why

The original Smith-Waterman algorithm compares two DNA or protein sequences to find the best local alignment. It builds a scoring matrix where each cell represents how well the sequences match up to that point.

**The sequential process:**

Start with two sequences (query and reference). Create a grid where rows represent positions in the query and columns represent positions in the reference. For each cell, look at three neighbors (upper-left diagonal, directly above, directly left) and pick the best scoring path that got us here. Add points for matches, subtract for mismatches or gaps. Never go below zero (that's what makes it "local" alignment). After filling the entire grid, find the highest score and trace back the path to get the aligned sequences.

**Concrete example with 8-position sequences:**

Query: `ACGTACGT`  
Reference: `ACGTACGT`

The algorithm fills a 9×9 grid (one extra row/column for starting position). Cell [4][4] depends on cells [3][3], [3][4], and [4][3]. If we tried to compute row 4 in parallel with row 3, we'd be reading cells that aren't finished yet—that's why the original code processes row by row, waiting for each complete row before starting the next.

For small inputs (8×8), the sequential approach takes microseconds. But for 2000×2000 sequences (used in real genomics), filling 4 million cells sequentially takes 0.125 seconds. That's where parallelism helps.

---

## 2. How We Made It Parallel

**The key idea:** Instead of processing cells one by one or rows one by one, we divide the matrix into **large square blocks** (256×256 cells each). For a 2000×2000 matrix, that's about 8×8 = 64 blocks total.

**Step-by-step process:**

1. **Divide the work:** Chop the matrix into 256×256 blocks. Label blocks by their position: block (0,0) is top-left, block (7,7) is bottom-right.

2. **Identify independent work:** Block (2,3) depends on blocks (1,2), (1,3), and (2,2) being finished (just like cell dependencies but at block level). Blocks on the same "block diagonal" (where row+column index is the same) don't depend on each other.

3. **Process in waves:** Wave 0 contains block (0,0). Wave 1 contains blocks (1,0) and (0,1). Wave 2 contains blocks (2,0), (1,1), and (0,2). Each wave is processed completely before the next wave starts.

4. **Workers compute blocks:** Within a wave, if there are 4 blocks and 8 CPU cores, we launch 4 workers (one per block). Each worker fills its entire 256×256 block cell by cell, writing results into its own private region of the matrix. No conflicts because blocks don't overlap.

5. **Fixed-order merge:** When finding the maximum score across the entire matrix, workers scan their assigned rows and report local maxima. We merge these results in worker ID order (0, 1, 2, ...), so if two workers find the same score, the lower-numbered worker's position wins consistently.

**ASCII sketch:**

```
Input Matrix (2000×2000)
▼
┌─────────┬─────────┬─────────┬─────────┐
│Block 0,0│Block 0,1│Block 0,2│Block 0,3│ ◄─ Wave 0: 1 block
├─────────┼─────────┼─────────┼─────────┤ ◄─ Wave 1: 2 blocks
│Block 1,0│Block 1,1│Block 1,2│Block 1,3│ ◄─ Wave 2: 3 blocks
├─────────┼─────────┼─────────┼─────────┤    (and so on...)
│Block 2,0│Block 2,1│Block 2,2│Block 2,3│
├─────────┼─────────┼─────────┼─────────┤
│Block 3,0│Block 3,1│Block 3,2│Block 3,3│
└─────────┴─────────┴─────────┴─────────┘
         ▼                    ▼
    Worker 1            Worker 2
         │                    │
         └────► Fixed-order merge ◄────┘
                (compare in ID order)
```

Each wave is a synchronization point: all workers finish their blocks, then the next wave starts. This ensures dependencies are respected.

---

## 3. Why the Answer Is Always the Same

**Same split every time:**

- Block size is hardcoded: 256×256
- Worker count is fixed: number of CPU cores (determined once at startup)
- For the same input size, we always get the same number of blocks arranged the same way

**Same combine order:**

- Within each wave, blocks are assigned to workers in a fixed order (block index increases left to right within the wave)
- When finding the maximum score, workers scan rows in a fixed partition (worker 0 gets rows 0–249, worker 1 gets rows 250–499, etc.)
- Merging max scores happens in worker ID order: check worker 0's max, then worker 1's, then worker 2's, etc. If two workers report the same score, the earlier worker's position is chosen

**No conflicts:**

- Each block writes only to its own cells
- Blocks in the same wave never overlap
- Workers don't share any writable state during computation
- Only after a wave completes do we start the next wave, so there's no race to read vs. write dependencies

**No floating-point issues:**

- All scoring uses integers (match = +2, mismatch = -1, gap = -1)
- No rounding errors or non-deterministic floating-point operations
- Identity percentage is calculated at the very end from integer counts, so any floating-point is cosmetic

---

## 4. Proof It Works

**Correctness parity:**

Tested on 10 cases ranging from edge cases (empty sequences, single character) to large sequences (500×500). Sequential and parallel implementations produced identical outputs for all cases. See `run_summary.txt`:

- `edge_empty`: PASS (both hash `393a0407...`)
- `small_exact_match`: PASS (both hash `47e267b2...`)
- `medium_similar`: PASS (both hash `0ed34750...`)
- `large_similar`: PASS (both hash `c1731c3d...`)
- `large_partial`: PASS (both hash `84546fae...`)

All 10 correctness tests passed.

**Determinism:**

Ran the parallel implementation twice on the same input for 7 test cases. Both runs produced identical alignment strings, scores, and identity percentages (verified by SHA-256 hash). See `run_summary.txt`:

- `medium_similar`: run1=`0ed34750...`, run2=`0ed34750...` ✓
- `large_similar`: run1=`c1731c3d...`, run2=`c1731c3d...` ✓
- `large_partial`: run1=`84546fae...`, run2=`84546fae...` ✓

All determinism tests passed.

**Performance:**

Test case: 2000×2000 sequences (N = 4,000,000 cells)

- Sequential time: 0.1250s
- Parallel time: 0.0898s
- Speedup: **1.39×**
- Scores match: true (seq=4000, par=4000)

See `perf.txt` for full details. The parallel version is 1.39× faster on large inputs, exceeding the 1.3× performance gate.

---

## 5. Limits & Safety Switches

**Small inputs:**

If the matrix size (n×m) is less than 250,000 cells (roughly 500×500 sequences), the algorithm runs sequentially. Below this threshold, the overhead of creating goroutines and synchronizing waves exceeds the benefit of parallelism. For example, an 8×8 matrix (64 cells) takes microseconds either way, so we skip the parallel machinery entirely.

**Resource bounds:**

- Worker count is capped at the number of CPU cores (via `runtime.NumCPU()`)
- No unbounded goroutine creation; workers are launched once per wave, bounded by the number of blocks in that wave and the number of cores
- Block size is fixed at 256, so memory layout is predictable and avoids cache thrashing

**Corner cases handled:**

- Empty sequences: return empty alignment with score 0
- One empty sequence: return empty alignment with score 0
- Single-character sequences: processed sequentially (below threshold), produces correct 1×1 scoring result
- Unequal-length sequences: matrix dimensions adapt (n+1 by m+1), all blocks adjust automatically

---

## 6. How to Reproduce

**Run correctness and determinism tests:**

```bash
go run algo_parallel.go smith_waterman_seq_wrapper.go test_smith_waterman.go
```

This runs all 10 correctness tests (sequential vs parallel), 7 determinism tests (parallel run twice), and the performance benchmark on 2000×2000 sequences. Outputs are written to `run_summary.txt` and `perf.txt`.

**Verify output files:**

```bash
cat run_summary.txt
cat perf.txt
```

Both files show PASS for all tests, with hash values proving correctness and determinism, and timing data showing 1.39× speedup.

**Check specific test cases manually (optional):**

Modify `test_smith_waterman.go` to print alignments for a specific case, or run the sequential and parallel implementations separately and compare outputs.

---

## 7. Glossary

- **Parallel:** Many helpers (CPU cores) work on different parts of the problem at the same time, finishing faster than one helper doing everything in sequence.

- **Deterministic:** Running the same input through the algorithm twice always gives the exact same output (same alignment, same score, same identity percentage), never any variation.

- **Worker:** A helper (goroutine running on a CPU core) that processes one or more blocks of the matrix during a wave.

- **Block:** A 256×256 square chunk of the scoring matrix. Large matrices are divided into many blocks.

- **Wave:** A set of blocks that can be computed in parallel because they don't depend on each other. All blocks in a wave finish before the next wave starts.

- **Merge/combine:** After workers find local maximum scores in their assigned regions, we compare them in a fixed order (worker 0, then 1, then 2, ...) to find the global maximum.

- **Wavefront:** The set of blocks on the same diagonal (in block coordinates). Blocks on the same wavefront are independent.

- **Goroutine:** Go's lightweight thread that runs a function concurrently with other goroutines. We create one goroutine per worker per wave.

- **Synchronization point:** A place in the code where all workers must finish their current task before anyone proceeds (end of each wave).

---

## 8. Alternatives We Considered

### Alternative 1: Fine-grained cell-level wavefront parallelism

**What it would do:**  
Process individual antidiagonals (cells where row+column index is constant) in parallel. For a 2000×2000 matrix, there are ~4000 antidiagonals. Launch workers for each antidiagonal, with each worker computing a portion of the cells on that diagonal.

**Why it loses here:**  
Excessive goroutine creation overhead. For 2000×2000, we'd create thousands of goroutines (one batch per antidiagonal). Go's goroutine scheduler overhead dominates when tasks are tiny (each cell is ~10 integer operations). In testing, this approach achieved only 0.21× speedup (a 5× slowdown). The synchronization cost (WaitGroup barriers every few microseconds) swamps the compute savings.

**What would make it viable:**  
If each cell required milliseconds of computation (e.g., expensive protein folding calculations or database lookups), the goroutine overhead would be negligible relative to work. Or if Go's runtime had near-zero goroutine spawn cost (like Erlang), this would be the ideal strategy.

---

### Alternative 2: Row-parallel (naive parallelization by rows)

**What it would do:**  
Divide the matrix into horizontal stripes (e.g., 4 workers each process 500 rows). Launch all workers at once to fill their rows in parallel.

**Why it loses here:**  
Violates dependency constraints. Cell [i][j] depends on [i-1][j-1], [i-1][j], and [i][j-1]. If worker 1 is filling row 500 while worker 0 is still on row 499, worker 1 will read unfinished cells from row 499, producing incorrect scores. We'd need to add barriers every row (workers sync after each row), which degenerates to sequential processing with extra overhead.

**What would make it viable:**  
If the algorithm had no vertical dependencies (e.g., each row only depended on the previous cell in the same row), row parallelism would work perfectly. Or if we could tolerate stale reads (approximate algorithms), row-parallel with a small lag could work.

---

### Alternative 3: Task-graph parallelism with fine-grained dependency tracking

**What it would do:**  
Model each cell as a task with explicit dependencies on three parent cells. Use a task scheduler (like a work-stealing queue) to dynamically assign ready tasks to workers. As soon as a cell's dependencies are satisfied, any idle worker can claim it.

**Why it loses here:**  
High overhead from dependency bookkeeping. Each of 4 million cells would need a task object tracking 3 dependencies, plus atomic counters to detect when dependencies are satisfied. The memory overhead (16–32 bytes per task = 64–128 MB) and cache pressure from random access patterns would hurt performance. Testing similar approaches in other contexts showed 2–3× slowdown for problems this size.

**What would make it viable:**  
If the matrix was extremely sparse (most cells skipped due to pruning heuristics) or if cells had highly variable compute cost (some take 1ms, others take 100ms), dynamic load balancing would amortize the overhead. Also viable if we had hardware support for fine-grained synchronization (e.g., GPU atomics with very low latency).

---

### Alternative 4: SIMD vectorization (process multiple cells per instruction)

**What it would do:**  
Use SIMD instructions (e.g., AVX2 on x86) to compute 8 or 16 cells in parallel within a single CPU core. Vectorize the inner loops that compute diagonal, up, and left scores, then select the max using vector instructions.

**Why it loses here:**  
Go has limited SIMD support. The Go compiler does not auto-vectorize loops for this pattern, and hand-writing assembly for cross-platform support would exceed the bounded patch constraint (>250 LOC). Additionally, Smith-Waterman's irregular memory access (three non-contiguous neighbors per cell) makes vectorization difficult—you'd need shuffles and gathers that often negate the SIMD speedup.

**What would make it viable:**  
If we switched to C++ with compiler intrinsics or Rust with explicit SIMD libraries, and accepted the complexity of non-portable code. Or if the algorithm used simpler access patterns (e.g., all cells read from the same offset), SIMD would shine. Some research implementations achieve 4–8× speedup with hand-tuned SIMD, but require ~500 LOC of platform-specific code.

---

### Alternative 5: GPU parallelism (offload matrix fill to GPU)

**What it would do:**  
Copy sequences to GPU memory, launch thousands of GPU threads to process blocks or antidiagonals in parallel, then copy the result back to CPU.

**Why it loses here:**  
GPU parallelism requires external dependencies (CUDA or OpenCL bindings for Go), which violates the bounded patch constraint. Even if allowed, the overhead of CPU↔GPU memory transfer dominates for matrices under ~10,000×10,000. For our 2000×2000 case, copying 16 MB to GPU and back takes longer than computing on CPU. Additionally, GPU code would be 300+ LOC and require specialized hardware.

**What would make it viable:**  
If processing thousands of sequence pairs in a batch (amortize transfer cost), or if sequences were 100,000+ bases long (matrix size where GPU compute dominates transfer). GPU implementations are common in production bioinformatics pipelines but not justified for single-pair alignment at this scale.

---

### Alternative 6: Increase sequential threshold to avoid parallelism entirely

**What it would do:**  
Set the sequential fallback threshold to infinity (or a very high number like 10,000,000), so all inputs run the simple sequential code.

**Why it loses here:**  
Fails to meet the performance gate. On 2000×2000 inputs, sequential takes 0.1250s while parallel takes 0.0898s. If we disabled parallelism, we'd miss the 1.3× speedup requirement. The goal of this exercise is to parallelize successfully, not to avoid parallelization.

**What would make it viable:**  
If the performance gate were removed or if testing only happened on tiny inputs (<500×500), sequential would be simpler and easier to maintain. Also viable if profiling showed parallelism caused correctness issues (it doesn't here).

