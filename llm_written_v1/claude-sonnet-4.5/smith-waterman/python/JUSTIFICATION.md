# Smith-Waterman Parallel Implementation Justification

## 1. What Changed and Why

### The Original Sequential Process

Smith-Waterman is a **DNA sequence alignment algorithm**. Imagine you have two DNA sequences (strings of letters A, C, G, T) and you want to find the best matching region between them.

The algorithm builds a **scoring table** (called matrix H) where each cell (i,j) represents how well the first i letters of sequence A match the first j letters of sequence B. To compute each cell's score, you need three neighbors:
- The cell diagonally above-left (match/mismatch)
- The cell directly above (gap in sequence B)
- The cell directly to the left (gap in sequence A)

You pick the best of these three options (or zero if all are negative). Then you find the cell with the highest score in the entire table—that's where the best local alignment ends. Finally, you trace backward from that cell to reconstruct the actual alignment.

**Concrete Example with 5-letter sequences:**

```
Query:     A C G T A
Reference: A G G T C

Step 1: Build scoring table (each cell depends on three neighbors)
Step 2: Find max score in the table → (4, 4) with score 8
Step 3: Trace back to build alignment → "ACGT" aligns with "AGGT"
```

### Why This Was Hard to Parallelize

Each cell in the scoring table depends on three cells that must be computed first. This creates a **dependency chain** like dominoes—you can't knock over domino 5 until dominos 1-4 have fallen. In a 600×600 table, that's 360,000 dominoes that must fall in a specific order.


## 2. How We Made It Parallel

Our parallel version uses **two strategies**:

### Strategy A: Optimize with NumPy (Not True Parallelism, But Faster)

For the scoring table construction (the bottleneck), we switched from Python lists to **NumPy arrays**. NumPy is a math library that uses low-level optimized code (written in C) to process numbers faster. Think of it like upgrading from a bicycle to a motorcycle—still one rider, but much faster.

**Why we couldn't truly parallelize this step:**  
The dependency chain means workers would spend most of their time waiting for each other. It's like trying to speed up a relay race by adding more runners—each runner still has to wait for the baton.

### Strategy B: Parallel Maximum-Finding

After building the table, we need to find the highest score among 360,000 cells. This part **is** embarrassingly parallel because checking cell A doesn't depend on checking cell B.

**How we split the work:**

```
Input table (600 rows × 600 columns)
     ↓
Divide rows into 8 chunks (75 rows each)
     ↓
[Chunk 1: rows 0-74  ] → Worker 1 finds max in its chunk
[Chunk 2: rows 75-149] → Worker 2 finds max in its chunk
[Chunk 3: rows 150-224] → Worker 3 finds max in its chunk
...
[Chunk 8: rows 525-599] → Worker 8 finds max in its chunk
     ↓
Fixed-order merge: Compare maxes from Worker 1, then 2, then 3... to 8
     ↓
Overall maximum found
```

### ASCII Sketch of the Parallel Flow

```
Query DNA   ──┐
              ├──► [Build Scoring Table] ──► H matrix (600×600)
Reference DNA─┘         (Sequential)              │
                                                  ├─► [Chunk 0-74  ] ──► Worker 1
                                                  ├─► [Chunk 75-149] ──► Worker 2
                                                  ├─► [Chunk 150-224] ──► Worker 3
                                                  ├─► [Chunk 225-299] ──► Worker 4
                                                  ├─► [Chunk 300-374] ──► Worker 5
                                                  ├─► [Chunk 375-449] ──► Worker 6
                                                  ├─► [Chunk 450-524] ──► Worker 7
                                                  └─► [Chunk 525-599] ──► Worker 8
                                                          │
                              ┌───────────────────────────┴─────────────────────┐
                              ↓                                                 ↓
                      [Fixed-order merge: 1→2→3→4→5→6→7→8]                Traceback
                              ↓                                          (Sequential)
                         Maximum position                                    ↓
                              └────────────────────────────────────────────►  Final alignment
```


## 3. Why the Answer Is Always the Same (Determinism)

### Same Split Every Time
- For a 600×600 table with 8 workers, Worker 1 always gets rows 0-74, Worker 2 always gets rows 75-149, etc.
- The chunk assignments are fixed by a simple formula: `chunk_size = 600 ÷ 8 = 75 rows`.

### Same Combine Order
- After workers find their local maxima, we **always** compare them in order: Worker 1's result first, then Worker 2's, then Worker 3's, and so on.
- We never use unordered sets or race conditions. If Worker 3 finishes before Worker 2, we still wait and process Worker 2's result first.

### No Conflicts
- Each worker reads from the shared table but only writes to its own private "max found so far" variable.
- The only place where results are combined is in the main thread, one at a time, in a fixed order.
- Because matrix construction is sequential (not truly parallel), there are no race conditions there either.

### Integers Only
- All scores are whole numbers (integers), so there are no floating-point rounding issues.


## 4. Proof It Works

### Correctness Parity
We tested 11 cases (see `evidence/run_summary.txt`):
- **Edge cases:** empty sequences, single character, tiny 4×4 tables
- **Small cases:** 10×10 and 20×20 random DNA
- **Medium cases:** 100×100 and 200×200 random DNA  
- **Large cases:** 400×400 and 600×600 random DNA

**Result:** 11/11 tests passed. Every parallel output exactly matched the sequential baseline (same alignment strings, same score, same identity percentage).

Example hash for 600×600 case:
- Sequential: `c4020121c61f35ba`
- Parallel run 1: `c4020121c61f35ba` ✓
- Parallel run 2: `c4020121c61f35ba` ✓

### Determinism Evidence
We ran the parallel version **twice** on the same input and compared cryptographic hashes (SHA-256) of the outputs. All 11 cases produced identical hashes across both runs.

Example from `evidence/run_summary.txt`:
```
100×100: hash 57141a1a886892fd (Run 1) == 57141a1a886892fd (Run 2) ✓
200×200: hash 9a06c78f07469f65 (Run 1) == 9a06c78f07469f65 (Run 2) ✓
400×400: hash 585175e97c054f73 (Run 1) == 585175e97c054f73 (Run 2) ✓
600×600: hash c4020121c61f35ba (Run 1) == c4020121c61f35ba (Run 2) ✓
```

### Performance (See `evidence/perf.txt`)

**Important Finding:** The parallel version is **slower** than sequential for these input sizes.

| Input Size | Sequential Time | Parallel Time | Speedup  |
|------------|-----------------|---------------|----------|
| 100×100    | 0.009s          | 0.068s        | 0.14× (7× slower) |
| 200×200    | 0.041s          | 0.180s        | 0.23× (4× slower) |
| 400×400    | 0.166s          | 0.552s        | 0.30× (3× slower) |
| 600×600    | 0.441s          | 1.239s        | 0.36× (3× slower) |

**Why the slowdown?**  
Python's multiprocessing has overhead (spawning processes, copying data between them). We parallelized only the max-finding step (about 5% of the work), but the entire algorithm still pays the parallelization overhead cost. The 95% bottleneck (table construction) remains sequential because of data dependencies.

**This is not a bug—it's a demonstration that not all algorithms benefit from parallelization.** The implementation is correct and deterministic; the algorithm just isn't a good fit for Python's multiprocessing model at these input sizes.


## 5. Limits and Safety Switches

### Small Input Fast Path
- If either sequence has fewer than **50 letters**, we skip all parallelization and run purely sequential code.
- **Why:** Spawning workers takes 20-50 milliseconds. For tiny inputs that finish in 1 millisecond, that's a 20-50× slowdown.

### Resource Bounds
- Workers are capped at the **number of CPU cores** (8 on a typical laptop, 16 on the test machine).
- We never spawn unlimited workers, avoiding system overload.

### Edge Case Handling
- **Empty sequences:** Return empty alignment immediately (no table to build).
- **Single cell (1×1):** Compute directly without spawning workers.
- **Very large sequences:** The algorithm scales as O(n²), so a 10,000×10,000 input would need ~100 million cells. The sequential threshold ensures we don't spawn workers for small cases while still accepting large inputs.


## 6. How to Reproduce

### Run All Tests (Correctness + Determinism + Performance)
```bash
python test_smith_waterman.py
```

This runs 11 test cases, checking that:
1. Parallel output matches sequential output (correctness)
2. Two parallel runs produce identical hashes (determinism)
3. Timing is recorded for large cases (performance)

### Run a Single Example Manually
```bash
python algo_parallel.py
```

This runs a quick sanity check with "ACGT" vs "ACGT".

### Verify Evidence Files
```bash
cat evidence/run_summary.txt    # Full test results with hashes
cat evidence/perf.txt            # Performance analysis and slowdown explanation
```


## 7. Glossary

- **Parallel:** Multiple helpers (workers) do different parts of the work at the same time, like 4 people each assembling one corner of a jigsaw puzzle.

- **Deterministic:** Same input always produces the same output, like a recipe that always makes the same cake if you follow it exactly.

- **Worker:** A helper process that does one piece of the total job. In our case, each worker scans a subset of rows to find the max score in that subset.

- **Merge/Combine:** Join partial answers in a fixed order to get the final answer. Like collecting puzzle corners from Helper 1, Helper 2, Helper 3, Helper 4 in that exact sequence.

- **Dependency:** When Task B must wait for Task A to finish first. Like needing to crack an egg (Task A) before you can whisk it (Task B).

- **Bottleneck:** The slowest part of the algorithm that determines overall speed, like the narrowest part of a highway causing a traffic jam.

- **Overhead:** Extra time spent organizing workers instead of doing useful work, like the time managers spend in meetings instead of building products.

- **NumPy:** A Python library that uses fast low-level code (C language) to process arrays of numbers quickly.

- **Dynamic programming (DP):** A technique where you solve small subproblems and combine their answers to solve bigger problems, like building a table where each cell uses previous cells' values.
