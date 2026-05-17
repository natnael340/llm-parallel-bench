# Parallel BFS Implementation

A correct, deterministic, resource-bounded parallel implementation of Breadth-First Search (BFS) in Java.

## Overview

This implementation transforms a sequential BFS algorithm into a level-synchronous parallel version that:
- ✅ Produces **identical output** to the sequential baseline
- ✅ Runs **deterministically** (same input → same output every time)
- ✅ Respects **resource bounds** (bounded by CPU core count)
- ✅ Achieves **measurable speedup** on large graphs with high edge density

## Files

### Core Implementation
- `BfsSequential.java` - Original sequential BFS baseline
- `BfsParallel.java` - Parallel BFS implementation (also as `bfs_parallel.java`)
- `Graph.java` - Graph data structure (unchanged from baseline)

### Testing & Benchmarking
- `TestBfs.java` - Comprehensive differential test suite (also as `test_bfs.java`)
- `PerfBfs.java` - Performance benchmarking suite
- `RunBfs.java` - Unified test runner (also as `run_bfs.java`)
- `run_bfs.sh` - Shell script for easy execution

### Documentation & Results
- `JUSTIFICATION.md` - Detailed explanation for non-technical readers (1,100+ words)
- `run_summary.txt` - Test results summary (correctness + determinism)
- `perf.txt` - Performance benchmark results
- `REQUEST.md` - Original parallelization requirements

## Quick Start

### Compile Everything
```bash
javac Graph.java BfsSequential.java BfsParallel.java TestBfs.java PerfBfs.java
```

### Run Correctness Tests
```bash
java TestBfs
```

### Run Performance Benchmarks
```bash
java PerfBfs
```

### Using the Shell Script
```bash
chmod +x run_bfs.sh
./run_bfs.sh test    # Run tests
./run_bfs.sh perf    # Run benchmarks
./run_bfs.sh all     # Run both
```

## Test Results

All 12 test cases **PASSED** ✓

### Test Coverage
- **Edge cases**: Empty graph, single vertex, disconnected graph, invalid start
- **Small cases**: Linear chain (10), binary tree (7), cycle (5)
- **Medium cases**: Grid (10×10), random graph (50V, 100E)
- **Large cases**: Grid (50×50), random graph (1000V, 5000E), binary tree (1023)

### Determinism Verification
Each test case was run **3 times** in parallel. All runs produced **identical output hashes**.

Example (Random Graph V=1000, E=5000):
- Sequential hash: `91bd93709037176a`
- Parallel run 1:   `91bd93709037176a`
- Parallel run 2:   `91bd93709037176a`
- Parallel run 3:   `91bd93709037176a`

## Performance Results

Tested on a **16-core system**:

| Test Case | Sequential | Parallel | Speedup | Efficiency |
|-----------|-----------|----------|---------|------------|
| Grid 100×100 (10K vertices) | 14.58 ms | 80.13 ms | 0.18× | 1.1% |
| Grid 200×200 (40K vertices) | 13.65 ms | 145.41 ms | 0.09× | 0.6% |
| Random (5K V, 25K E) | 5.46 ms | 9.03 ms | 0.61× | 3.8% |
| **Random (10K V, 50K E)** | **19.01 ms** | **8.88 ms** | **2.14×** | **13.4%** |

### Analysis
- **Grid graphs**: Poor performance due to shallow BFS trees (many levels, few vertices per level)
- **Random graphs**: Better speedup with higher edge density
- **Best case**: 2.14× speedup on 10K vertex random graph with 50K edges
- **Bottleneck**: BFS is memory-bound and inherently sequential across levels

## Algorithm Strategy

### Level-Synchronous Parallel BFS

The implementation uses a **two-phase approach** for each BFS level:

1. **Phase 1 (Parallel)**: Each worker independently collects neighbors from its assigned vertices
   - Workers read from the graph (immutable)
   - Workers write to private lists (no sharing)
   - No synchronization needed

2. **Phase 2 (Sequential)**: Process all collected neighbors in deterministic order
   - Iterate through workers' lists in fixed order
   - Check and update visited set sequentially
   - Add new vertices to next level

This ensures:
- ✅ **Correctness**: Same discovery order as sequential BFS
- ✅ **Determinism**: Fixed processing order for given input
- ✅ **Safety**: No data races or undefined behavior

### Resource Management
- Thread pool bounded to `Runtime.getRuntime().availableProcessors()`
- Sequential fallback for graphs < 100 vertices
- Sequential processing for levels < 4 vertices

## Key Design Decisions

### Why Level-Synchronous?
BFS has inherent level-by-level dependencies. We can't process level N+1 until level N is complete. Level-synchronous execution respects this constraint while parallelizing work within each level.

### Why Two-Phase Discovery?
To maintain deterministic ordering, we must process neighbors in the exact order they appear in the sequential version. The two-phase approach:
1. Parallelizes the expensive neighbor lookup
2. Serializes only the lightweight visited-check and list-append

### Rejected Alternatives
See `JUSTIFICATION.md` for detailed analysis of:
- Fully asynchronous BFS (non-deterministic)
- Direction-optimizing BFS (requires API changes)
- Graph partitioning (high overhead for these graph sizes)
- Wavefront task graphs (unnecessary complexity)

## Limitations

### When Parallel Version Is Slower
- **Small graphs** (< 100 vertices): Thread overhead dominates
- **Shallow graphs** (high diameter): Limited parallelism per level
- **Sequential-heavy workloads**: BFS is inherently less parallel than algorithms like matrix multiply

### Performance Ceiling
BFS parallelism is limited by:
- **Amdahl's Law**: Sequential merge phase in each level
- **Memory bandwidth**: Graph traversal is memory-bound
- **Level width**: Narrow levels limit parallel work

## Reproducing Results

### Correctness & Determinism
```bash
javac Graph.java BfsSequential.java BfsParallel.java TestBfs.java
java TestBfs
cat run_summary.txt
```

### Performance
```bash
javac Graph.java BfsSequential.java BfsParallel.java PerfBfs.java
java PerfBfs
cat perf.txt
```

## Implementation Details

- **Language**: Java
- **Parallelism**: ForkJoinPool with parallel streams
- **Thread Safety**: ConcurrentHashMap for visited set (read-only during parallel phase)
- **Determinism**: Fixed processing order via sequential merge
- **Resource Bounds**: Bounded by available processors

## License & Attribution

This is a demonstration implementation for educational purposes.

Original sequential BFS provided as baseline.
Parallel implementation and comprehensive testing by ParallelAgent.
