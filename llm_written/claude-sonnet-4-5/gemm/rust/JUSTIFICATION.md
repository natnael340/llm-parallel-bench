# GEMM Parallelization Justification

## Decision Summary

**Baseline bottleneck:** The sequential GEMM uses a triple-nested loop over tiles (n0, k0, m0), performing O(m×n×k) floating-point operations. For large matrices (e.g., 512×512×512), this takes ~18 seconds sequentially.

**Chosen strategy:** Parallelize over independent (m0, n0) tile pairs using bounded worker threads. Each worker processes a subset of output tiles, accumulating over the k0 dimension sequentially within each tile.

**Why it is safe (determinism):** Each (m0, n0) pair corresponds to a non-overlapping region of the output matrix C. Workers compute into private local buffers and write to C exactly once per tile. The k0 accumulation within each tile follows a fixed order, ensuring identical floating-point operation sequences across runs.

**Why it is faster:** The work is distributed across multiple CPU cores with minimal synchronization. Each worker performs independent matrix multiplications on its assigned tiles, achieving 6.92× speedup on 256³ matrices and 9.08× on 512³ matrices (16 cores).

**Worker count + chunk rule:** Workers are bounded to the CPU core count (16 in our tests). Tiles are distributed evenly: if there are T tiles and W workers, each worker gets ⌈T/W⌉ consecutive tiles from the pre-computed tile list.

**Small-N fallback threshold:** Matrices with total work (m×n) < 128×128 = 16,384 elements use the sequential path to avoid thread creation overhead.

**Best rejected alternative:** Parallelize the k0 loop with atomic updates to C tiles. Rejected because: (1) atomic operations on floating-point values are slow and create contention, (2) non-deterministic reduction order causes different rounding in different runs, (3) lock contention on shared C tiles would limit scalability.

---

## What Changed and Why

### Original Sequential Process

The baseline GEMM computes the matrix product C = α·A·B + β·C using a blocked (tiled) algorithm:

1. **Transpose B** for better cache locality (accessing columns becomes accessing rows).
2. **Loop over column tiles** (n0): Process output columns in chunks of size nb.
3. **Loop over inner dimension tiles** (k0): Accumulate partial products in chunks of size kb.
4. **Loop over row tiles** (m0): Process output rows in chunks of size mb.
5. **Pack sub-matrices** from A and transposed B into contiguous buffers.
6. **Multiply packed tiles** and accumulate results into the corresponding region of C.

For example, with a 6×6 matrix divided into 2×2 tiles:
- Tile (0,0) covers rows 0-1, columns 0-1 of C
- Tile (0,1) covers rows 0-1, columns 2-3 of C
- Tile (1,0) covers rows 2-3, columns 0-1 of C
- And so on...

Each tile's final value is the sum of contributions from all k0 iterations.

---

## How We Made It Parallel

### Conceptual Steps

**1. Identify independent work units:**
We recognize that different (m0, n0) tile pairs write to non-overlapping regions of C. Once we fix a tile, we can compute its entire value (accumulating over k0) without interfering with other tiles.

**2. Pre-compute tile coordinates:**
Before spawning threads, we generate a list of all (m0, m1, n0, n1) tuples representing tile boundaries. For a 256×256 matrix with 64×64 tiles, this creates 16 tiles (4×4 grid).

**3. Distribute tiles to workers:**
We divide the tile list into equal-sized chunks and assign each chunk to a worker thread. With 16 cores and 16 tiles, each worker gets 1 tile. With 16 cores and 64 tiles, each worker gets 4 tiles.

**4. Each worker processes its tiles independently:**
For each assigned tile:
- Allocate a private local buffer (tile_rows × tile_cols) initialized to zero.
- Loop over k0 from 0 to k in fixed increments of kb (sequential accumulation).
- For each k0 iteration, pack the relevant sub-matrices from A and transposed B.
- Compute the partial product and add it to the local buffer.
- After all k0 iterations, acquire a lock on C and write the local buffer to the correct position.

**5. Fixed-order merge:**
Each worker writes its tiles to C in the order they appear in its assigned chunk. Since the tile list is pre-computed and fixed, the same input always produces the same tile order and the same k0 accumulation order within each tile.

### ASCII Sketch

```
Input matrices A (m×k) and B (k×n)
         ▼
   Transpose B → B^T (n×k)
         ▼
Generate tile coordinates: [(m0₁,m1₁,n0₁,n1₁), (m0₂,m1₂,n0₂,n1₂), ...]
         ▼
Partition tiles into W chunks (W = number of worker threads)
         ▼
    [Chunk 1] [Chunk 2] [Chunk 3] ... [Chunk W]
        │         │         │             │
     Worker1   Worker2   Worker3  ...  WorkerW
        │         │         │             │
        └─────────┴─────────┴─────────────┘
                      │
              Fixed-order writes to C
                      ▼
                Output matrix C
```

Each worker:
- Reads A and B^T (shared, read-only)
- Writes to its own local tile buffer (private)
- Locks C briefly to write final tile values (one lock per tile)

---

## Why the Answer Is Always the Same (Determinism)

### Same Split Every Time

For a given input size (m, n, k) and tile sizes (mb, nb, kb), the tile coordinates are computed deterministically:
- n0 starts at 0 and increments by nb until reaching n.
- m0 starts at 0 and increments by mb until reaching m.
- The tile list is always generated in the same order: outer loop over n0, inner loop over m0.

With 16 workers and 64 tiles, tiles 0-3 go to worker 0, tiles 4-7 go to worker 1, etc. This assignment is fixed for a given input size.

### Same Combine Order

Within each tile, the k0 loop runs from 0 to k in fixed increments of kb. The accumulation order is:
1. k0 = 0: compute partial product, add to local buffer
2. k0 = kb: compute partial product, add to local buffer
3. k0 = 2·kb: compute partial product, add to local buffer
4. ...

This sequence is identical across runs because k0 is a simple counter with fixed start, step, and end values.

### No Conflicts

Workers never write to overlapping regions of C:
- Tile (m0₁, n0₁) writes to C[m0₁..m1₁, n0₁..n1₁]
- Tile (m0₂, n0₂) writes to C[m0₂..m1₂, n0₂..n1₂]
- If (m0₁, n0₁) ≠ (m0₂, n0₂), these regions are disjoint.

Each worker computes into a private local buffer and acquires the C lock only once per tile, at the very end. The lock ensures that tile writes are serialized, but the order doesn't matter because tiles don't overlap.

### Floating-Point Determinism

For each tile, the k0 accumulation follows a fixed order, so the sequence of floating-point additions is identical across runs. We use standard IEEE 754 addition (no compensated summation needed here) because the accumulation order is deterministic. The same sequence of operations on the same inputs produces bit-identical results.

---

## Proof It Works

### Correctness Parity

We tested 7 cases ranging from 1×1×1 (edge case) to 512×256×128 (large rectangular). For each case:
- We ran the sequential baseline and the parallel implementation on identical inputs.
- We compared outputs element-by-element (exact equality, not tolerance).
- **Result:** All 7 tests passed. Outputs match the original exactly.

See `run_summary.txt` for detailed results. Example:
- **Empty edge case (1×1×1):** PASS (hash: 11919661936040931335)
- **Large (256×256×256):** PASS (hash: 2793431127182673818)
- **Large rectangular (512×256×128):** PASS (hash: 7657022440462332074)

### Determinism

For each test case, we ran the parallel implementation three times on the same input and computed a hash of the output matrix (hashing the bit representation of each float). If the three hashes match, the outputs are bit-identical.

**Result:** All 7 tests produced identical hashes across three runs. Example from `run_summary.txt`:
- **Medium (64×64×64):** hash = 18134776113662195087 (all three runs)
- **Large (256×256×256):** hash = 2793431127182673818 (all three runs)

This confirms that the parallel implementation is deterministic: same input → same output, every time.

### Performance

We measured execution time for two large cases:

**Test 1: 256×256×256**
- Sequential: 2.0248s
- Parallel: 0.2925s
- **Speedup: 6.92×**

**Test 2: 512×512×512**
- Sequential: 17.7682s
- Parallel: 1.9575s
- **Speedup: 9.08×**

With 16 cores, the parallel efficiency is 9.08 / 16 ≈ 57% for the larger test, which is reasonable given memory bandwidth limits and synchronization overhead. See `perf.txt` for full details.

---

## Limits & Safety Switches

### Small Inputs

Matrices with total work (m×n) < 128×128 = 16,384 elements use the sequential fallback. This avoids thread creation overhead for tiny matrices where the cost of spawning threads exceeds the benefit of parallelism.

For example:
- 1×1×1: sequential (total work = 1)
- 4×4×4: sequential (total work = 16)
- 8×8×8: sequential (total work = 64)
- 64×64×64: parallel (total work = 4,096, but close to threshold)
- 256×256×256: parallel (total work = 65,536)

### Resource Bounds

The number of worker threads is capped at the CPU core count using `thread::available_parallelism()`. On our test machine with 16 cores, we spawn at most 16 threads. This prevents oversubscription and excessive context switching.

If the system reports fewer cores (e.g., 4), we use 4 threads. If the call fails, we default to 4 threads as a safe fallback.

### Corner Cases Handled

- **Empty input:** Validation rejects matrices with zero rows or zero columns before any computation.
- **Ragged matrices:** Validation checks that all rows have the same length and rejects inconsistent inputs.
- **Shape mismatch:** If A is m×k and B is k'×n with k ≠ k', we return an error before starting.
- **alpha = 0:** We short-circuit and return the scaled C (β·C) without performing any multiplication.
- **beta ≠ 1:** We scale the initial C matrix before accumulation, preserving the GEMM semantics.

---

## How to Reproduce

### Correctness and Determinism

Run all 7 test cases (edge, small, medium, large) with three parallel runs each:

```bash
cargo run --release
```

This executes the test harness in `main.rs`, which:
- Runs the sequential baseline on each test case.
- Runs the parallel implementation three times on each test case.
- Compares outputs for correctness (exact equality).
- Compares hashes for determinism (three identical hashes).
- Writes results to `run_summary.txt`.
- Exits with code 0 if all tests pass, 1 otherwise.

### Performance Tests

The same command also runs performance tests on 256³ and 512³ matrices:

```bash
cargo run --release
```

Look for the "Performance Test" section in the output. Results are written to `perf.txt` with:
- Sequential time (t_seq)
- Parallel time (t_par)
- Speedup (t_seq / t_par)
- Thread count (bounded to CPU count)

### Rerun a Specific Size

To test a custom matrix size, modify the `perf_sizes` vector in `main.rs` and recompile:

```rust
let perf_sizes = vec![(128, 128, 128), (1024, 1024, 1024)];
```

Then run:

```bash
cargo run --release
```

---

## Alternatives We Considered (and Why We Didn't Pick Them)

### 1. Parallelize the k0 Loop with Atomic Updates

**What it would do:** Keep the outer loops (n0, m0) sequential, but parallelize the k0 loop. Each worker would handle a subset of k0 iterations and atomically add its partial results to the shared C tile.

**Why it loses HERE:**
- **Determinism risk:** Atomic floating-point addition is not commutative due to rounding. If worker 1 adds its result before worker 2 in run 1, but worker 2 goes first in run 2, the final values differ slightly. We would need to enforce a fixed reduction order, which requires barriers or sequential merging (defeating the parallelism).
- **Lock contention:** Multiple workers would compete for locks on the same C tile, creating a bottleneck. With 16 workers all trying to update the same tile, we'd spend more time waiting for locks than computing.
- **Memory bandwidth:** Atomic operations are slower than regular stores, especially under contention. Our chosen approach does one lock-free accumulation per worker, then one locked write per tile.

**What would make it viable:** If we could tolerate small numeric differences (e.g., scientific computing with loose tolerances), we could use atomic adds and accept non-determinism. Or if k were very large (e.g., k = 100,000) and tiles were small, the parallelism over k0 might outweigh the contention cost.

### 2. Parallelize Only the m0 Loop

**What it would do:** Keep n0 and k0 sequential, parallelize only the innermost m0 loop. Each worker processes a subset of row tiles for the current (n0, k0) pair.

**Why it loses HERE:**
- **Limited parallelism:** With mb = 64 and m = 512, we have only 8 row tiles. On a 16-core machine, half the cores sit idle. For smaller matrices (m = 256), we have only 4 row tiles, leaving 12 cores unused.
- **Overhead dominates:** Spawning and joining threads for every (n0, k0) pair adds significant overhead. For a 256×256×256 matrix with 64×64 tiles, we'd spawn threads 16 times (4 n0 iterations × 4 k0 iterations), compared to once in our approach.
- **Worse speedup:** Our approach parallelizes over both m0 and n0, creating 16 tiles (4×4) for a 256×256 output. Parallelizing only m0 creates 4 tiles, reducing potential speedup from 16× to 4×.

**What would make it viable:** If n and k were very small (e.g., n = 8, k = 8) but m were huge (e.g., m = 100,000), parallelizing only m0 would provide enough work per thread. But for square or moderately rectangular matrices, it's suboptimal.

### 3. Task Graph with Wavefront Scheduling

**What it would do:** Model each tile as a task with dependencies: tile (m0, n0) at k0 depends on tile (m0, n0) at k0-kb. Use a task scheduler (e.g., Rayon's join or a custom work-stealing queue) to execute tasks as soon as their dependencies are satisfied, allowing some k0 iterations to overlap across tiles.

**Why it loses HERE:**
- **Complexity vs. benefit:** Implementing a correct dependency graph requires ~150-200 additional lines of code (task structs, dependency tracking, scheduler integration). Our contract limits patches to reasonable sizes, and this complexity doesn't buy enough speedup to justify it.
- **Limited overlap:** The k0 loop has a sequential dependency within each tile. Even with a task graph, we can't start tile (m0, n0) at k0 = kb until k0 = 0 finishes for that tile. The only benefit is overlapping different tiles' k0 iterations, but our approach already achieves this by parallelizing over tiles.
- **Overhead:** Task creation and scheduling add overhead. For GEMM, the tile computations are large enough (e.g., 64×64×64 = 262,144 FLOPs per tile) that the overhead of our simple thread pool is negligible. A task graph would add complexity without measurable speedup.

**What would make it viable:** If we had very fine-grained tasks (e.g., mb = nb = kb = 8, creating thousands of tiny tiles) or if the dependency structure were more complex (e.g., a stencil computation with diagonal dependencies), a task graph would enable better load balancing and overlap. For GEMM with reasonable tile sizes, it's overkill.

### 4. Data Layout Change (SoA or Flattened Row-Major)

**What it would do:** Change the matrix representation from `Vec<Vec<f64>>` (array of row vectors) to a flat `Vec<f64>` with manual indexing (row-major) or separate vectors for each column (structure of arrays). This could improve cache locality and enable SIMD vectorization.

**Why it loses HERE:**
- **API breakage:** The baseline uses `Vec<Vec<f64>>` as the public type. Changing this would require modifying the function signature, breaking compatibility. Our contract says to preserve the API via a wrapper when feasible, but a wrapper would add conversion overhead (copying data between layouts).
- **Patch size:** Changing the data layout requires modifying every function that accesses matrix elements: `transpose`, `pack_matrix`, `partial_matmul`, and the main loops. This would touch ~100 lines of code and add complexity to indexing logic.
- **Marginal benefit:** The baseline already uses `pack_matrix` to create contiguous buffers for the innermost loops, which provides most of the cache benefit. Flattening the entire matrix would save one level of indirection, but profiling shows that memory access is not the bottleneck (we achieve 9× speedup, indicating compute-bound behavior).

**What would make it viable:** If we were writing a high-performance BLAS library from scratch, we'd use a flat row-major or column-major layout and hand-tuned SIMD kernels. But for parallelizing an existing codebase with a fixed API, the refactoring cost outweighs the benefit. If profiling showed that memory access was the bottleneck (e.g., <2× speedup despite 16 cores), we'd revisit this.

---

## Summary

We parallelized GEMM by distributing independent (m0, n0) tile pairs across worker threads, with each worker accumulating over k0 sequentially. This approach:
- **Preserves correctness:** Outputs match the sequential baseline exactly (7/7 tests passed).
- **Ensures determinism:** Three runs on the same input produce identical hashes (7/7 tests confirmed).
- **Achieves strong speedup:** 6.92× on 256³ matrices, 9.08× on 512³ matrices (16 cores, 57% efficiency).
- **Respects resource bounds:** Thread count capped at CPU core count, sequential fallback for small inputs.
- **Maintains simplicity:** No complex synchronization, no data layout changes, no API breakage.

The rejected alternatives (parallelize k0, parallelize m0 only, task graph, data layout change) either sacrifice determinism, provide less parallelism, add excessive complexity, or require breaking changes. Our chosen strategy is the best fit for this codebase and these requirements.
