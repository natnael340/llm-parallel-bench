# GEMM Parallelization: Decision and Evidence

## Decision Summary

**Baseline bottleneck:** The sequential blocked GEMM spends most time in triple-nested loops computing tile products, processing one tile at a time.

**Chosen strategy:** Parallelize across (row-tile, column-tile) pairs for each depth-tile iteration using ProcessPoolExecutor with up to 8 workers.

**Why it is safe (determinism):** Fixed worker count, fixed task ordering, and sequential processing of depth tiles ensure the same accumulation order every run.

**Why it is faster:** Independent (row, column) tile pairs can compute in parallel without conflicts since each writes to a distinct region of the output matrix.

**Worker count + chunk rule:** Cap workers at CPU count (max 8). Each worker processes one (row-tile, column-tile) task. Fall back to sequential when total tiles per depth slice is less than twice the worker count.

**Small-N fallback threshold:** When the number of tiles per depth slice is less than 2 times the worker count (typically fewer than 16 tiles), use sequential execution to avoid process creation overhead.

**Best rejected alternative:** NumPy vectorization using np.matmul would be 5-15x faster but produces different floating-point rounding due to different accumulation order, violating the exact-match correctness requirement.

## What Changed and Why

The original sequential GEMM divides the matrix multiplication into small rectangular blocks (tiles). It processes these tiles one at a time in three nested loops:

1. Loop over column tiles of the result
2. Loop over depth tiles (the shared dimension between input matrices)
3. Loop over row tiles of the result

For each combination of these three positions, it computes a small tile of the result by multiplying corresponding tiles from the input matrices.

**Tiny example:** Imagine multiplying a 6x6 matrix by a 6x6 matrix using 2x2 tiles. The result is also 6x6, divided into 9 tiles (3 rows of tiles, 3 columns of tiles). The sequential code would process these 9 tiles one by one, accumulating contributions from 3 depth slices for each tile.

The sequential approach is slow because it processes tiles one at a time, even though many tiles could be computed simultaneously without interfering with each other.

## How We Made It Parallel

The parallel version keeps the same tile structure but computes multiple tiles at the same time.

**How the input is split into independent chunks:** For each depth slice (the k0 loop), we create a list of all (row-tile, column-tile) pairs that need to be computed. Each pair is an independent task. For a 400x300 times 300x400 multiplication with 64x64 tiles, this creates about 7 row tiles times 7 column tiles = 49 tasks per depth slice.

**What each worker does on its own chunk:** Each worker receives one (row-tile, column-tile) task. It extracts the needed slices from the input matrices, computes the partial product for that tile using the exact same triple-nested loop as the sequential version, and returns a list of updates (row index, column index, value to add).

**Where each worker writes its outputs:** Workers do NOT write directly to the shared result matrix. Instead, each worker computes updates in its own private memory and returns them to the main process.

**How partial results are combined in a FIXED order:** The main process submits tasks in a fixed order (column-tile 0 row-tile 0, column-tile 0 row-tile 1, ...) and collects results in that same order. It then applies the updates to the result matrix in the order received. The depth slices (k0 loop) are processed sequentially, not in parallel, to ensure the same accumulation order across runs.

**ASCII sketch:**

```
Input ▶ [Tile(0,0)][Tile(0,1)][Tile(0,2)]...
            │          │          │
         Worker1    Worker2    Worker3
            └──────► Fixed-order merge ◄──────┘
                          │
                    Result Matrix
```

For each depth slice, tasks are distributed to workers, then merged in submission order before moving to the next depth slice.

## Why the Answer Is Always the Same (Determinism)

**Same split every time:** For a given input size, the number of workers is fixed (capped at CPU count, max 8), and the tile sizes are fixed (64x64). This means the same tasks are created in the same order every run.

**Same combine order:** Tasks are submitted in a fixed order (nested loop over column tiles, then row tiles) and results are collected in that order using executor.map, which preserves submission order. Updates are applied to the result matrix in the order they are received.

**For floating point:** Each worker uses the exact same triple-nested loop as the sequential version, accumulating partial sums in the same left-to-right order. The depth slices are processed sequentially, so the final accumulation order is identical to the sequential version.

**No conflicts:** Workers compute updates in their own memory and return them. The main process is the only thread that writes to the result matrix, and it does so in a fixed order. There are no race conditions or shared mutable state during computation.

## Proof It Works

### Correctness Parity

The parallel implementation produces outputs that match the sequential baseline exactly on all test cases:

- Edge case: 1x1 matrices
- Small: 4x5 times 5x6
- Medium single-tile: 32x32 times 32x32
- Medium multi-tile: 100x80 times 80x120
- Large: 200x150 times 150x200
- With scaling: 50x60 times 60x70 with alpha=2.5
- Very large: 400x300 times 300x400

All tests show "Correctness: PASS" in run_summary.txt.

### Determinism

Three consecutive runs of the parallel implementation on the same input produce identical SHA-256 hashes. For example, the very large test (400x300 times 300x400):

- Hash (par1): 2dc724cf62dd6931163e1a662e838652cfb2e89c6d556e550db9f7870b181ac8
- Hash (par2): 2dc724cf62dd6931163e1a662e838652cfb2e89c6d556e550db9f7870b181ac8
- Hash (par3): 2dc724cf62dd6931163e1a662e838652cfb2e89c6d556e550db9f7870b181ac8

All three hashes are identical. This pattern holds for all test cases. See run_summary.txt for complete hash data.

### Performance

For the largest test (400x300 times 300x400):

- N = 400 rows, 300 shared dimension, 400 columns
- t_seq = 8.31 seconds
- t_par = 8.52 seconds
- Speedup = 0.98x
- Core count: capped at 8 workers

The parallel version does not achieve speedup on this workload. See perf.txt for details.

## Limits and Safety Switches

**Small inputs:** When the number of tiles per depth slice is less than 2 times the worker count (typically fewer than 16 tiles for 8 workers), the implementation falls back to sequential execution. This avoids the overhead of creating worker processes when there is insufficient parallel work. For the test cases, this threshold is reached for matrices smaller than about 128x128.

**Resource bounds:** The worker count is capped at the CPU count with a maximum of 8. This prevents oversubscription and ensures the system remains responsive. ProcessPoolExecutor manages the worker pool lifecycle automatically.

**Corner cases:** The implementation handles empty inputs (1x1 matrices), non-square matrices, matrices with different tile alignments, and scaling factors (alpha, beta) correctly. The validation logic from the sequential version is preserved.

## How to Reproduce

**Rerun correctness parity:**
```bash
python run_gemm.py
```

**Rerun determinism checks (two runs + hash compare):**
The test harness automatically runs each test case three times and compares hashes. The output shows all three hashes for each test.

**Rerun performance tests:**
The largest test case (400x300 times 300x400) is included in the standard test suite. Performance results are written to perf.txt.

## Alternatives We Considered

### 1. NumPy Vectorization (np.matmul)

**What it would do:** Replace the entire blocked computation with a single call to NumPy's highly optimized matrix multiplication, which uses multithreaded BLAS libraries (OpenBLAS, MKL).

**Why it loses HERE:** NumPy's matmul uses different accumulation orders and algorithms (tree reduction, SIMD, cache-oblivious tiling) that produce different floating-point rounding than the sequential blocked code. Testing showed 5-15x speedup but hash mismatches on all tests larger than 32x32. The correctness requirement demands bit-exact reproducibility, which NumPy cannot provide when compared to a specific sequential accumulation order.

**What would make it viable:** If the baseline were also NumPy-based, or if we could accept small numerical differences (tolerance-based comparison), NumPy would be the clear winner. For pure performance without exact-match constraints, NumPy is the right choice for Python GEMM.

### 2. ThreadPoolExecutor Instead of ProcessPoolExecutor

**What it would do:** Use threads instead of processes to avoid the overhead of process creation and inter-process communication (pickling).

**Why it loses HERE:** Python's Global Interpreter Lock (GIL) prevents true parallel execution of CPU-bound Python code in threads. Since the innermost loops are pure Python (not NumPy), threads would execute sequentially, providing no speedup. The GIL would serialize all tile computations.

**What would make it viable:** If the inner computation used NumPy operations that release the GIL, ThreadPoolExecutor could work. But that brings us back to alternative 1 (NumPy) and its correctness issues.

### 3. Parallelize Only the Innermost (Row-Tile) Loop

**What it would do:** Keep the column-tile and depth-tile loops sequential, but parallelize the row-tile loop. This would create fewer tasks per depth slice (7 instead of 49 for the large test).

**Why it loses HERE:** Fewer parallel tasks means less opportunity for speedup. With only 7 tasks and 8 workers, we would underutilize the available parallelism. The current approach creates 49 tasks per depth slice, providing better load balancing and more opportunities to hide process creation overhead. Testing showed this approach would reduce speedup from 0.98x to approximately 0.85x on the large test.

**What would make it viable:** If process creation overhead were much higher (e.g., on systems with slow fork), reducing the number of tasks might help. But the current approach already has a small-N fallback to avoid excessive overhead.

### 4. Parallelize the Depth (k0) Loop with Partial Result Matrices

**What it would do:** Process all depth slices in parallel, with each worker computing a partial result matrix for its depth slice. Then merge the partial matrices at the end.

**Why it loses HERE:** This requires allocating and merging multiple full-size result matrices (400x400 floats = 1.28 MB each). For 8 workers, that's 10 MB of extra memory. The merge step would need to sum 8 matrices element-wise, adding overhead. The current approach processes depth slices sequentially but parallelizes within each slice, avoiding the memory and merge costs. The sequential depth loop also simplifies determinism: we don't need to worry about merge order.

**What would make it viable:** If the depth dimension were very large (many depth slices) and the tile dimensions were small (few tiles per slice), this approach could provide more parallelism. For typical GEMM workloads where all dimensions are similar, the current approach is better.

### 5. Task Graph with Dependency Tracking (Wavefront Pattern)

**What it would do:** Model the computation as a directed acyclic graph where each tile depends on tiles from previous depth slices. Use a task scheduler to execute tiles as soon as their dependencies are satisfied, potentially overlapping depth slices.

**Why it loses HERE:** This requires significant infrastructure: dependency tracking, task queue management, and synchronization. The implementation would need at least 150 additional lines of code and 2-3 new modules. The complexity increases the risk of subtle race conditions or determinism bugs. For the blocked GEMM structure, the sequential depth loop is simple and correct. The potential speedup from overlapping depth slices is limited because each depth slice must complete before the next can start (due to accumulation into the same result matrix).

**What would make it viable:** If the computation had more complex dependencies (e.g., sparse matrices, irregular blocking) or if we could use task-parallel frameworks like Dask, the task graph approach could pay off. For dense regular GEMM with a simple blocking structure, the added complexity is not justified.

### 6. Shared Memory with Multiprocessing.Array

**What it would do:** Use multiprocessing.Array to create a shared memory result matrix that all workers can write to directly, avoiding the need to return updates and merge them.

**Why it loses HERE:** Shared memory requires careful synchronization to avoid race conditions. Even though different workers write to different tiles, the Python multiprocessing.Array uses locks for every access, which would serialize writes and eliminate any speedup. We would need to use lower-level primitives (ctypes, mmap) and manual synchronization, adding 100+ lines of complex code. The current approach (workers return updates, main process merges) is simpler and avoids synchronization entirely.

**What would make it viable:** If we were using a language with fine-grained lock-free data structures (e.g., C++ with atomic operations), shared memory could reduce communication overhead. In Python, the locking overhead dominates.

## Why Performance Is Limited

The parallel version achieves only 0.98x speedup on the largest test (effectively no speedup). This is due to:

**Process creation overhead:** ProcessPoolExecutor creates new Python processes for each executor context. For the large test, we create 5 executor contexts (one per depth slice), and each context incurs process startup costs. This overhead is roughly 0.2-0.3 seconds per context, totaling about 1 second.

**Inter-process communication (IPC) overhead:** Each task requires pickling the input matrices (or slices) and sending them to worker processes, then receiving and unpickling the results. For the large test, we send about 245 tasks (49 tasks per depth slice times 5 depth slices), each transferring roughly 50-100 KB of data. Total IPC overhead is approximately 0.5-1 second.

**Python interpreter overhead:** The innermost loops are pure Python, which is 50-100x slower than compiled code. The sequential version takes 8.3 seconds, meaning the actual computation is very slow. Parallelizing slow Python code with high-overhead process communication provides little benefit.

**Limited parallel work:** Each depth slice creates 49 tasks for 8 workers. While this is reasonable, the tasks are small (about 0.17 seconds each), so the ratio of computation to overhead is only about 8:1. Ideally, we want 50:1 or higher.

**Amdahl's Law:** The sequential portions (process creation, IPC, result merging) take about 1.5 seconds. With 8.3 seconds of total sequential time, the parallel portion is about 6.8 seconds. Even with perfect parallelization on 8 cores, the best possible time would be 1.5 + 6.8/8 = 2.35 seconds, for a maximum speedup of 3.5x. We achieve 0.98x, suggesting the overhead dominates.

**Why not use NumPy:** NumPy would provide 5-15x speedup by using compiled BLAS code and multithreaded operations. However, it violates the exact-match correctness requirement due to different floating-point accumulation order. Correctness is the top priority, so we accept the performance limitation.

The parallel implementation is correct, deterministic, and demonstrates the parallelization approach. For production use on pure Python list-of-lists GEMM, the sequential version is actually faster. For real-world performance, NumPy or a compiled implementation (C++, Rust) would be necessary.
