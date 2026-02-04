# Parallel BFS Implementation

A deterministic parallel implementation of Breadth-First Search (BFS) in Go, with comprehensive testing and performance analysis.

## Files

- **graph.go** - Graph data structure and utilities
- **bfs_sequential.go** - Sequential BFS baseline implementation
- **bfs_parallel.go** - Parallel BFS implementation (main deliverable)
- **test_bfs.go** - Test utilities and test case definitions
- **run_bfs.go** - Test runner (correctness and determinism)
- **perf_bfs.go** - Performance benchmark runner
- **JUSTIFICATION.md** - Detailed explanation of design decisions (600-1100 words)
- **run_summary.txt** - Test results (correctness and determinism)
- **perf.txt** - Performance benchmark results

## Quick Start

### Run All Tests
```bash
go run graph.go bfs_sequential.go bfs_parallel.go test_bfs.go run_bfs.go
```

### Run Performance Benchmarks
```bash
go run graph.go bfs_sequential.go bfs_parallel.go perf_bfs.go
```

## Test Results Summary

- **Correctness:** 9/9 tests passed ✓
- **Determinism:** 9/9 tests passed ✓
- **Test cases:** Empty graph, single vertex, chains, stars, grids, complete graphs, random sparse graphs, binary trees

## Key Features

- **Deterministic:** Same input always produces same output
- **Correct:** Matches sequential baseline exactly
- **Safe:** No data races, bounded resource usage
- **Well-tested:** Edge cases, small/medium/large inputs, repeated runs

## Performance Note

The parallel implementation is **correct and deterministic** but **not faster** than sequential for typical graph sizes. This is due to BFS's inherent level-synchronization requirements and the overhead of parallelization.

See **JUSTIFICATION.md** for detailed analysis of why BFS is fundamentally limited for parallelization and what alternatives were considered.

## Implementation Strategy

Level-synchronous parallel BFS:
1. Sort all adjacency lists for deterministic neighbor iteration
2. Process each BFS level in parallel by dividing the frontier into chunks
3. Workers discover neighbors independently in their chunks
4. Merge results in fixed worker order (deterministic)
5. Small graphs (< 100 vertices) use sequential fallback

## Reproduce Results

```bash
# Correctness and determinism tests
go run graph.go bfs_sequential.go bfs_parallel.go test_bfs.go run_bfs.go

# Performance benchmarks
go run graph.go bfs_sequential.go bfs_parallel.go perf_bfs.go
```

Results are written to `run_summary.txt` and `perf.txt`.
