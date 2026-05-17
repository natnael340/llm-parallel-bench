# GEMM Parallelization Justification

## Decision Summary

**Baseline bottleneck:** The sequential GEMM uses a blocked algorithm with three nested loops (n-blocks, k-blocks, m-blocks). The innermost computation (partialMatmul) is compute-intensive, performing matrix multiplication on small blocks. The triple loop structure processes blocks sequentially, leaving parallelism untapped.

**Chosen strategy:** Parallelize the combined (n-block, m-block) space while keeping the k-block loop sequential. For each k-block, all (n, m) block pairs are processed in parallel using OpenMP with static scheduling.

**Why it is safe (determinism):** The k-loop remains sequential, ensuring that accumulations into each C cell happen in the same order every time. Different (n, m) pairs write to completely separate regions of C (disjoint rows and columns), so no data races occur. Static scheduling assigns the same (n, m) pairs to the same threads for a given matrix size and block configuration.

**Why it is faster:** Large matrices have many (n, m) block pairs (e.g., 256×256 with 64×64 blocks yields 16 pairs). Processing these pairs in parallel distributes the compute-intensive partialMatmul work across multiple cores, reducing wall-clock time.

**Worker count + chunk rule:** OpenMP uses all available cores (16 in our tests). Static scheduling divides the (n, m) pairs evenly among threads, ensuring balanced load when the number of pairs is much larger than the thread count.

**Small-N fallback threshold:** Matrices with m < 128 use sequential execution. Below this threshold, the overhead of thread creation and synchronization exceeds the benefit of parallelism.

**Best rejected alternative + reason:** Parallelizing only the innermost m-loop (initial attempt) was rejected because it created too many parallel regions (one per k-block), causing excessive thread spawn overhead and memory allocation contention. The overhead dominated for all tested sizes, yielding 0.19x–0.60x speedup.

---

## What Changed and Why

The original sequential GEMM processes matrix multiplication in a blocked fashion to improve cache locality. Imagine multiplying two large matrices A (rows × shared) and B (shared × cols) to produce C (rows × cols). Instead of computing all of C at once, the algorithm divides the work into small rectangular blocks.

**Tiny example (8 rows, 8 cols, block size 4):**
- C is divided into 4 blocks: top-left, top-right, bottom-left, bottom-right.
- The algorithm processes these blocks one at a time in a fixed order: first all top-left contributions (from different k-blocks), then top-right, then bottom-left, then bottom-right.
- Each block computation multiplies a small piece of A with a small piece of B and adds the result to the corresponding piece of C.

The sequential version processes these blocks in a strict order, using three nested loops:
1. Loop over column-blocks of C (n-blocks)
2. Loop over shared-dimension blocks (k-blocks)
3. Loop over row-blocks of C (m-blocks)

This ensures that each C block receives contributions from all k-blocks in the same order every time.

---

## How We Made It Parallel

**Conceptual steps (no code):**

1. **Split the work into independent chunks:**  
   For a given k-block, all (n-block, m-block) pairs can be computed independently because they write to different parts of C. We create a list of all (n, m) pairs upfront. For example, with 4 n-blocks and 4 m-blocks, we have 16 pairs: (0,0), (0,1), ..., (3,3).

2. **Assign chunks to workers:**  
   OpenMP's static schedule divides the 16 pairs evenly among available threads. With 16 threads, each thread gets 1 pair. With 4 threads, each gets 4 pairs. The assignment is deterministic: pair index i always goes to thread (i mod num_threads).

3. **What each worker does:**  
   Each worker receives a (n, m) pair. It extracts the corresponding sub-blocks from A and B (called "packing"), multiplies them using partialMatmul, and writes the result directly to its assigned region of C. No worker touches another worker's region.

4. **Where workers write:**  
   Each worker writes to a private temporary buffer during partialMatmul, then accumulates into C. Since (n, m) pairs are disjoint, there are no conflicts. Worker 0 might write to C[0:64][0:64], worker 1 to C[0:64][64:128], etc.

5. **Fixed-order merge:**  
   The k-loop is sequential. For k-block 0, all (n, m) pairs are processed in parallel. Then we wait (implicit barrier). Then k-block 1 is processed, and so on. This ensures that contributions from k-block 0 are always added before k-block 1, maintaining deterministic accumulation order.

**ASCII sketch:**

```
Matrix C split into (n,m) blocks:
  [Block(0,0)][Block(0,1)][Block(0,2)]
  [Block(1,0)][Block(1,1)][Block(1,2)]
  [Block(2,0)][Block(2,1)][Block(2,2)]

For each k-block (sequential):
  k=0: Process all 9 blocks in parallel
         │         │         │
      Worker1  Worker2  Worker3  ...
         └─► Write to disjoint C regions
  
  [Barrier - all workers finish k=0]
  
  k=1: Process all 9 blocks in parallel
         │         │         │
      Worker1  Worker2  Worker3  ...
         └─► Accumulate to same C regions (no conflict, sequential k-order)
  
  [Barrier - all workers finish k=1]
  
  ... and so on
```

---

## Why the Answer Is Always the Same (Determinism)

**Same split every time:**  
For a given matrix size (m, n, k) and block configuration (MB=64, NB=64, KB=64), the number of (n, m) pairs is fixed. A 512×512 matrix always yields 64 pairs (8 n-blocks × 8 m-blocks). The list of pairs is built in the same order every run: (0,0), (0,64), (0,128), ..., (448,448).

**Same combine order:**  
The k-loop is sequential. Contributions from k-block 0 are always added before k-block 1, before k-block 2, etc. Within each k-block, the (n, m) pairs are processed in parallel, but they write to disjoint C regions, so the order doesn't matter for those writes. The only shared accumulation is across k-blocks, which is serialized.

**Floating-point determinism:**  
Each partialMatmul computes a dot product in a fixed loop order (same k-index order every time). The accumulation into C happens in the same k-block order every run. Since the same operations happen in the same sequence, floating-point results are bitwise identical.

**No conflicts:**  
Workers never write to overlapping C regions within a k-block. Each (n, m) pair maps to a unique rectangle in C. Worker 1 might update C[0:64][0:64], worker 2 updates C[0:64][64:128], etc. These regions don't overlap. The only synchronization is the implicit barrier between k-blocks, which ensures all workers finish k-block i before any starts k-block i+1.

---

## Proof It Works

**Correctness parity:**  
The parallel implementation produces outputs that match the sequential baseline exactly on all test cases: edge cases (1×1, single row, single column), small cases (4×4, 5×3×7), medium cases (64×64, 100×80×120, 128×128), and large cases (256×256, 512×256×128). All 11 test cases passed. See run_summary.txt for full results.

**Determinism:**  
Three consecutive parallel runs on the same input produce identical outputs, verified by bitwise hashing. For example:
- Large 256×256 test: all three runs produced hash `74ff99319e132bf1`
- Large 512×256×128 test: all three runs produced hash `408da51f704e7cc4`

These hashes confirm that every floating-point value in the output matrix is bitwise identical across runs. See run_summary.txt for all hash values.

**Performance:**  
Tested on matrices of size 256×256, 512×512, and 1024×512×512 with 16 cores:

| Matrix Size       | t_seq (s) | t_par (s) | Speedup | Efficiency |
|-------------------|-----------|-----------|---------|------------|
| 256×256×256       | 0.0247    | 0.0359    | 0.69x   | 4.3%       |
| 512×512×512       | 0.1654    | 0.0850    | 1.95x   | 12.2%      |
| 1024×512×512      | 0.3457    | 0.1042    | 3.32x   | 20.7%      |

The 256×256 case shows slowdown due to overhead dominating small workloads. The larger cases (512×512 and 1024×512×512) show meaningful speedups of 1.95x and 3.32x. See perf.txt for detailed timing data.

---

## Limits & Safety Switches

**Small inputs:**  
Matrices with m < 128 use sequential execution. Below this threshold, the number of (n, m) block pairs is too small to amortize thread creation overhead. For example, a 64×64 matrix with 64×64 blocks yields only 1 pair, making parallelism pointless.

**Resource bounds:**  
OpenMP automatically caps worker threads to the number of available cores (16 in our tests). We use static scheduling to avoid dynamic scheduling overhead. No manual thread pool management is needed; OpenMP handles this safely.

**Corner cases handled:**
- Empty inputs: validation rejects them before any computation.
- 1×1 matrices: processed sequentially (below threshold).
- Non-square matrices: handled correctly by the blocking logic (e.g., 512×256×128 test passed).
- Alpha=0 or beta≠1: special cases are handled before the main loop.

---

## How to Reproduce

**Rerun correctness and determinism tests:**
```bash
g++ -O3 -fopenmp gemm_common.cpp gemm_seq.cpp gemm_parallel.cpp test_gemm.cpp -o test_gemm
./test_gemm
```
This runs 11 test cases (edge, small, medium, large) and verifies that parallel outputs match sequential outputs exactly. It also runs each parallel case 3 times and checks that all 3 runs produce identical hashes.

**Rerun performance tests:**
The same `./test_gemm` command also runs performance benchmarks on 256×256, 512×512, and 1024×512×512 matrices. Results are written to perf.txt.

**Check determinism manually (two runs + hash compare):**
```bash
./test_gemm > run1.log
./test_gemm > run2.log
diff run1.log run2.log
```
If the outputs are identical, diff will produce no output, confirming determinism.

---

## Alternatives We Considered

### 1. Parallelize only the innermost m-loop (initial implementation)

**What it would do:**  
For each (n-block, k-block) pair, parallelize the loop over m-blocks. Each thread processes a different row-block of C.

**Why it loses here:**  
This creates a new parallel region for every (n, k) pair. With 4 n-blocks and 8 k-blocks, that's 32 parallel regions. Each region spawn incurs overhead (thread wake-up, work distribution). Additionally, each thread allocates a new Apack matrix inside the parallel loop, causing memory allocation contention. In our tests, this approach yielded 0.19x–0.60x speedup (slower than sequential) because overhead dominated. The memory allocator became a bottleneck with 16 threads all calling packMatrix simultaneously.

**What would make it viable:**  
If we pre-allocated all Apack buffers outside the parallel region and reused them, overhead would drop. However, this would require significant refactoring (thread-local buffer pools) and would still suffer from many small parallel regions. It might become viable for very large m (e.g., m > 4096) where each m-block is large enough to amortize overhead.

---

### 2. Parallelize the k-loop with reduction on C

**What it would do:**  
Process all k-blocks in parallel. Each thread computes a partial result for C, then combine them with a reduction (sum). This exposes more parallelism since k-blocks are independent.

**Why it loses here:**  
OpenMP reductions on large matrices (e.g., 512×512 doubles = 2MB) are expensive. The reduction must combine 16 copies of C (32MB total) at the end. More critically, floating-point reduction order is non-deterministic in OpenMP unless we manually implement a fixed-tree reduction. The manual reduction would add 100+ lines of code and complex indexing logic. The determinism risk is high: even with a fixed tree, we'd need to ensure the same thread-to-k-block mapping every run, which requires careful schedule control.

**What would make it viable:**  
If determinism were not required, or if we accepted small numeric differences (e.g., relative error < 1e-12), OpenMP's built-in reduction would work. For very large k (e.g., k > 2048), the parallelism gain might outweigh the reduction cost. We could also use a library like Eigen or Intel MKL that handles deterministic reductions internally.

---

### 3. Task-based parallelism with dependency graph

**What it would do:**  
Model each (n, k, m) block computation as a task. Use OpenMP tasks with dependencies to express that C[n,m] from k-block i+1 depends on C[n,m] from k-block i. The runtime schedules tasks dynamically while respecting dependencies.

**Why it loses here:**  
With 4 n-blocks, 8 k-blocks, and 4 m-blocks, we'd create 128 tasks. Each task has dependencies on the previous k-block's tasks for the same (n, m) pair. This creates a complex dependency graph. OpenMP's task scheduler overhead is non-trivial: each task spawn, dependency check, and scheduling decision costs cycles. For our block sizes (64×64), each task does only ~250K FLOPs, making the overhead-to-work ratio poor. Additionally, ensuring deterministic task scheduling requires careful use of `taskwait` and `depend` clauses, which adds code complexity (estimated 150+ lines).

**What would make it viable:**  
If block sizes were much larger (e.g., MB=NB=KB=256), each task would do ~16M FLOPs, making overhead negligible. Task-based approaches shine when work is highly irregular (e.g., sparse matrices, adaptive refinement). For our regular dense GEMM, the complexity cost outweighs the benefit. This would be viable if we needed to integrate with other task-based code (e.g., a larger task graph for a multi-stage computation).

---

### 4. Parallelize the outer n-loop only

**What it would do:**  
Process each n-block in parallel. Within each n-block, the k-loop and m-loop remain sequential. This creates fewer parallel regions (one per n-block) and avoids reduction issues.

**Why it loses here:**  
For a 512×512 matrix with NB=64, we have only 8 n-blocks. With 16 threads, half the cores sit idle. Load imbalance is severe if n is not a multiple of the thread count. For non-square matrices (e.g., 1024×512×512), we have 8 n-blocks but 16 m-blocks, leaving parallelism on the table. The efficiency would be capped at 50% even in the best case.

**What would make it viable:**  
If n >> m (e.g., 2048×256×256), parallelizing the n-loop would provide enough work. We could also combine this with parallelizing the m-loop (collapse(2) on n and m), but that brings us back to the chosen strategy. This approach is simpler (fewer lines of code) but sacrifices performance for simplicity, which violates the priority order (performance > maintainability when correctness and determinism are met).

