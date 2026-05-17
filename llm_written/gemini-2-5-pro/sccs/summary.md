# SCC Code Review: Gemini 2.5 Pro

## Thesis-Ready Summary

Gemini 2.5 Pro produced structurally consistent parallel SCC edge-reduction implementations across all six languages. Like Claude Sonnet 4.5, the model correctly identifies the two-phase structure: sequential Tarjan's DFS for SCC discovery, followed by embarrassingly parallel per-SCC edge minimization. The algorithmic decomposition is identical to Claude's across all six languages, an independent map over SCC subgraphs followed by a deterministic reduce. Both models converge on the same correct parallelization strategy for this problem.

Where the models diverge is in how they handle determinism and data sharing, two algorithmic concerns that sit below the decomposition level but critically affect correctness and performance.

On determinism, Gemini takes three distinct approaches across its six implementations. Four languages (C++, C#, Go, Python) normalize output via a post-hoc sort, treating the parallel phase as producing an unordered bag. Go additionally fixes a language-specific correctness bug: since Go's map iteration order is non-deterministic by specification, the Go implementation explicitly sorts edges within each SCC worker before returning. This is the only implementation across either model that demonstrates language-level correctness reasoning about iteration order. The Rust implementation is the outlier: it returns edges in whatever order Rayon's work-stealing scheduler produces, without sorting. The justification frames this as deterministic by redefining determinism as multiset equality, conflating "same set of edges" with "same output." This is an algorithmic design error, not a concurrency primitive issue, as a single `.sorted()` call would resolve it.

On data sharing, Gemini's Rust implementation avoids the full adjacency-list cloning that plagued Claude's Rust version. By using Rayon's parallel iterator with shared borrows (`&self`), workers read the graph structure in place rather than each receiving a full copy. Both models parallelize the same phase of the same algorithm, but Gemini's approach treats the graph as read-only shared state while Claude's treats it as per-worker copied input. This is an algorithmic decision about data locality, not a primitive choice, and it has dramatic performance consequences. The same data-sharing gap appears in Python, where Gemini's implementation (like Claude's) serializes the full adjacency lists as arguments to every SCC task rather than transferring graph data once per worker at pool creation. The justification mischaracterizes this as an "I/O bound" problem when it is a serialization-bound problem caused by per-task data duplication.

Gemini's threshold design is notably less conservative than Claude's. Java and Rust have no fallback threshold at all, and the remaining four languages use low thresholds (2-4 SCCs for C#, Go, Python; 100 SCCs for C++). The Java implementation creates and shuts down a full thread pool for every `reduceEdges()` call regardless of SCC count. This reflects a design assumption that the runtime absorbs overhead efficiently, which is correct for lightweight schedulers but architecturally unsound as a general principle. The model does not reason about when the overhead of parallelization exceeds the per-task work, the same gap observed in Claude but expressed as threshold omission rather than threshold miscalibration.

The justification documents are shorter than Claude's and contain systematic accuracy issues. The C# justification claims performance numbers from a test configuration that differs sixfold from the benchmark. The C++ justification describes a 0.98x result as having "showed a speedup." These are documentation errors rather than algorithmic ones, but they indicate the model generates justification prose from intent rather than from verification of actual benchmark output.

For thesis purposes, Gemini 2.5 Pro's SCC implementations reinforce the same core finding as Claude Sonnet 4.5: both models reliably identify embarrassingly parallel structure in graph algorithms and correctly preserve Tarjan's sequential invariant. The algorithmic decomposition is sound and identical across both models. The gaps are in second-order algorithmic decisions: data-sharing strategy (copy vs. share), output determinism guarantees (sort vs. ignore), task granularity (one SCC per task without coarsening), and threshold calibration (absent or qualitative). The Go map-iteration fix is a notable exception, demonstrating that LLMs can reason about language-specific correctness constraints when the non-determinism is well-documented in language specifications.

---

## Per-Language Review

### Java

**Parallelization strategy:** Fixed-size ExecutorService thread pool (one thread per CPU core). Each SCC submitted as an independent Callable task. SCCs sorted by minimum node ID before processing. Results collected in submission order via Future.get().

**Justification claim vs code verification:**
- Claim: "No specific threshold was set" -- **Verified.** Code has no threshold check; all graphs go through the parallel path regardless of SCC count.
- Claim: "We sort the list of SCCs before starting to guarantee that the final list of edges is assembled in the same order every time" -- **Verified.** Code sorts SCCs by minimum node ID on line 136-139.
- Claim: "Rejected `parallelStream()` because it does not guarantee order" -- Reasonable justification, though `parallelStream().collect(Collectors.toList())` does preserve encounter order for ordered sources.

**Performance:**
- Justification perf.txt: Seq 30.44 ms, Par 31.51 ms (~1.0x). Essentially no speedup, consistent with overhead matching computation.
- Benchmark: 9.85 ms mean. Faster than the justification's test, likely due to different graph size.

**Bugs:**
- No parallelization threshold. For a graph with 1 SCC, the code still creates an ExecutorService, submits one task, and shuts down the pool. This is wasteful but not incorrect.
- The justification states parallelStream doesn't guarantee order, but this is partially incorrect. For ordered stream sources, `collect(Collectors.toList())` does preserve encounter order even with parallel streams. The concern about `flatMap` reordering is more nuanced.

**Rating:** Clean implementation. Missing threshold is a design gap. Justification is mostly accurate but contains a minor error about parallelStream ordering guarantees.

---

### Rust

**Parallelization strategy:** Rayon `par_iter().flat_map().collect()` for parallel SCC processing. No explicit threshold. No SCC sorting before parallel processing.

**Justification claim vs code verification:**
- Claim: "The *multiset* of edges is identical on every run. Our tests verify this by sorting the final edge lists before comparison" -- **Verified in code:** `par_iter().flat_map().collect()` does not guarantee output order. Tests sort before comparing.
- Claim: "No explicit fallback is implemented. Rayon's overhead is minimal" -- **Verified.** No threshold in code.
- Claim: "Rayon's `par_iter` is highly optimized; for a small number of SCCs, it introduces negligible overhead" -- Reasonable claim given Rayon's work-stealing design.

**Determinism semantics conflation:**
The justification states the implementation is "deterministic" because the multiset of edges is identical. This conflates two distinct properties:
1. **Set-deterministic:** The same set of edges is always produced (true).
2. **Order-deterministic:** The edges appear in the same order every run (false).

The code relies on downstream sorting for deterministic output, but the `reduce_edges()` function itself does not sort. A caller using the output directly would see non-deterministic ordering. This is a meaningful semantic gap.

**Performance:**
- Justification perf.txt: Seq 37.4 ms, Par 47.4 ms (0.78x). Parallel is slower.
- Benchmark: 16.72 ms mean. This is better than the justification test, and better than the sequential baseline FindSCC (5.28 ms), suggesting rayon's overhead is minimal for the benchmark graph.

**Bugs:** The `reduce_edges()` function produces non-deterministically ordered output. The test harness masks this by sorting.

**Rating:** Architecturally clean rayon usage. Determinism conflation is the main issue.

---

### C++

**Parallelization strategy:** OpenMP `#pragma omp parallel for` with private per-thread edge lists. Thread-safe merge via `#pragma omp critical`. Final sort for determinism. Sequential fallback for fewer than 100 SCCs.

**Justification claim vs code verification:**
- Claim: "If the number of SCCs found is less than 100, the algorithm will not use parallel processing" -- Threshold verified at 100 SCCs.
- Claim: "The number of worker threads is managed by OpenMP and is typically capped at the number of available CPU cores" -- Standard OpenMP behavior, verified.
- Claim: "On the 'Large' test case, the parallel version showed a speedup" -- **Vague.** The evidence file shows 0.98x speedup (45.9 ms seq vs 46.7 ms par), which is essentially no speedup. Calling this "showed a speedup" is misleading.

**Performance:**
- Justification perf.txt: Seq 45.9 ms, Par 46.7 ms (0.98x). Essentially identical.
- Benchmark: 38.94 ms mean.

**Bugs:** None found. The 100-SCC threshold is reasonable for OpenMP overhead.

**Rating:** Correct implementation. Justification's performance claim ("showed a speedup") is misleading for a 0.98x result.

---

### C#

**Parallelization strategy:** Task Parallel Library (Parallel.ForEach) with ConcurrentBag for thread-safe result collection. Final sort for determinism. Threshold at 2 SCCs.

**Justification claim vs code verification:**
- Claim: "Sequential version took 228 ms, parallel version took 168 ms, achieving a 1.36x speedup" -- **Numbers from justification's own test on 5000 vertices, 20000 edges.** The benchmark measures 36.01 ms, which is 6x faster than the claimed sequential time.
- Claim: "A threshold (PARALLEL_THRESHOLD) is in place to fall back to the sequential loop" at fewer than 2 SCCs -- Verified.

**Performance mismatch:**
- Justification: 228 ms sequential, 168 ms parallel on 5K vertices.
- Benchmark: 36.01 ms mean. The massive discrepancy (228 ms vs 36 ms) suggests the justification's test graph has very different characteristics (much denser or differently structured) than the benchmark graph.

**Bugs:** None in code. The performance numbers in the justification do not represent the benchmark workload.

**Rating:** Performance numbers are dramatically mismatched with benchmark. The justification presents favorable numbers from a different workload without noting this distinction.

---

### Go

**Parallelization strategy:** Worker pool with goroutines. Jobs dispatched via channels, results collected with index-based ordering. Sequential fallback for fewer than 4 SCCs. Explicit edge sorting within each SCC worker for determinism.

**Justification claim vs code verification:**
- Claim: "2.11x speedup over the sequential one (166ms vs 78ms) on a multi-core machine" -- **Partially verified.** The perf.txt shows sequential 122 ms, parallel 105-111 ms, with a "2.12x" speedup claimed in the performance check section. However, 122/105 = 1.16x, not 2.12x. The 2.12x appears to come from a separate performance benchmark with different parameters.
- Claim: "A subtle bug was fixed where the simplification process for a single district was not deterministic" -- This is a genuine and valuable insight about Go's map iteration non-determinism.
- Claim: Performance on "20,000 nodes and 100,000 edges" -- The benchmark uses a different (likely smaller) graph, yielding 41.18 ms.

**Performance:**
- Justification claims 78-166 ms range depending on test configuration.
- Benchmark: 41.18 ms mean. Significantly faster than justification numbers, indicating the benchmark graph is simpler.

**Bugs:** The 2.12x speedup claim is inconsistent with the logged times in the same perf.txt file (sequential 122 ms, parallel 105-111 ms would be ~1.1-1.2x). This suggests the speedup was measured differently than the logged individual times.

**Rating:** Best Go implementation feature: explicitly fixing map iteration non-determinism. Performance claims have internal inconsistency.

---

### Python

**Parallelization strategy:** ProcessPoolExecutor with `executor.map()` for order-preserving parallel execution. Top-level `_minimize_scc_worker` function to avoid pickling the Graph object. Sequential fallback for fewer than 2 SCCs.

**Justification claim vs code verification:**
- Claim: "Worker function... cannot be a method of the Graph class because that would require pickling the entire 'self' object, which is inefficient and can fail" -- **Correct observation,** but the chosen approach still passes `(self.adj, self.rev_adj, scc)` as arguments to every task, pickling the full adjacency lists per task.
- Claim: "Performance... did not show a speedup. This is because the overhead of creating processes and transferring data between them outweighs the benefits" -- Honest and accurate.
- Claim: "The problem is I/O bound rather than CPU-bound" -- **Incorrect.** The SCC edge reduction is CPU/memory-bound. The overhead is from Python's multiprocessing serialization (pickling), not I/O.

**Performance:**
- Justification perf.txt: 0.05x-0.11x speedup across test sizes. Consistently negative scaling.
- Benchmark: 23,456.2 ms mean. The serialization overhead means parallelization makes the implementation dramatically slower than even a pure sequential Python approach.

**Bugs:**
- **COW claim absent but implied:** The code sends `(self.adj, self.rev_adj, scc)` as task arguments. Each task receives a pickled copy of the full adjacency lists. Using `initializer`/`initargs` in the ProcessPoolExecutor constructor would send the graph data once per worker process at pool creation time, avoiding per-task serialization. The justification does not mention this optimization.
- **I/O bound mischaracterization:** The justification calls the problem "I/O bound" which is incorrect. It is serialization-bound in the parallel version and CPU-bound in the sequential version.
- Recursion limit fix: The justification mentions converting Tarjan's DFS from recursive to iterative. This is a genuine improvement, but it was a correctness fix for large graphs, not a parallelization optimization.

**Rating:** Honest about negative performance. Contains a factual error about I/O boundedness and misses the `initargs` optimization.

---

## Justification Integrity Scorecard

| Language | Strategy Accuracy | Perf Numbers Match | Threshold Logic Match | Determinism Claims | Overall Grade |
|----------|------------------|-------------------|-----------------------|-------------------|---------------|
| Java     | Accurate          | Consistent        | N/A (no threshold)    | Accurate          | B+            |
| Rust     | Accurate          | Consistent        | N/A (no threshold)    | **Conflated**     | B-            |
| C++      | Accurate          | **Misleading**    | Accurate              | Accurate          | B             |
| C#       | Accurate          | **Dramatic mismatch** | Accurate           | Accurate          | C+            |
| Go       | Accurate          | **Internal inconsistency** | Accurate       | Accurate          | B             |
| Python   | **I/O claim wrong** | Consistent      | Accurate              | Accurate          | B-            |

**Legend:**
- **Strategy Accuracy:** Does the justification correctly describe the parallelization approach?
- **Perf Numbers Match:** Do justification-claimed numbers match benchmark evidence?
- **Threshold Logic Match:** Does the justification correctly describe the fallback threshold?
- **Determinism Claims:** Are the determinism guarantees accurate?
- **Overall Grade:** Composite assessment of justification integrity.

## Key Findings

1. **Systematic performance number mismatch:** Gemini's justifications consistently report performance numbers from ad-hoc tests that do not match standardized benchmark results. The C# justification claims 228 ms sequential when the benchmark measures 36 ms. The Go justification has internal inconsistency between logged times and claimed speedup.

2. **Rust determinism conflation:** The Rust implementation produces non-deterministically ordered output from `par_iter().flat_map().collect()`. The justification frames this as deterministic by defining determinism as multiset equality and relying on test-time sorting. This is a meaningful semantic gap for downstream consumers.

3. **Java missing threshold:** The only implementation without any parallelization threshold. While the benchmark result (9.85 ms, best across all languages) suggests this doesn't hurt performance for the tested graphs, it represents a gap in overhead-aware design.

4. **Go genuine speedup at scale:** The Go implementation is the only one demonstrating meaningful speedup (2.12x claimed, though the logged numbers suggest ~1.2x) at non-trivial graph sizes. The explicit fix for Go's map iteration non-determinism is a valuable engineering insight.

5. **Python serialization overhead:** The per-task pickling of full adjacency lists creates catastrophic overhead. The `initargs` optimization (sending graph data once per worker at pool creation) is not mentioned in the justification and would significantly reduce overhead, though Python's GIL and multiprocessing model still limit practical benefit.

6. **C++ modest overhead:** The OpenMP implementation with a 100-SCC threshold achieves near-parity (0.98x) but never demonstrates actual speedup. The justification misleadingly describes this as having "showed a speedup."
