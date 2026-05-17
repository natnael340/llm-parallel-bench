# BFS Parallel Implementation

This project contains a deterministic, correct parallel implementation of Breadth-First Search (BFS) in Rust using Rayon.

## Files

- **bfs_parallel.rs** - Final parallel BFS implementation with full documentation
- **main.rs** - Comprehensive test runner with correctness, determinism, and performance tests
- **JUSTIFICATION.md** - Detailed explanation of design decisions and alternatives (1,850 words)
- **run_summary.txt** - Test results showing correctness and determinism
- **perf.txt** - Performance benchmark results

## Key Features

✅ **Correctness**: Matches sequential BFS output exactly on all test cases  
✅ **Determinism**: Same input produces same output on every run (verified with hash comparison)  
✅ **Performance**: 1.7-2.0× speedup on random graphs with high average degree  
✅ **Safety**: Automatic fallback to sequential for small graphs/levels  
✅ **Resource-bounded**: Thread pool capped at CPU core count  

## Strategy

**Level-synchronous parallel BFS:**
- Process each BFS level in parallel
- Synchronize between levels
- Sort vertices within each level for deterministic ordering
- Use Rayon's work-stealing for load balancing

## Test Results

### Correctness (8/8 passed)
- Edge cases: empty graph, disconnected components
- Small: 6 vertices (tree)
- Medium: 100 vertices (grid)
- Large: 10,000 vertices (grid and random)

### Determinism (6/6 passed)
All test cases produce identical hashes across 3 runs:
- small_tree: `42e0c70b319b6ed3`
- medium_grid: `06d9691786d50e7a`
- large_grid: `89e9d5f513430cc4`
- star_500: `c9bd1157baa044b2`
- star_2000: `0e7cd909e629b07f`
- random_1000_deg20: `13a263c02bf1da17`

### Performance
- **Random 5000 vertices, degree 20:** 2.01× speedup (115.72ms → 57.56ms)
- **Random 10000 vertices, degree 30:** 1.70× speedup (287.21ms → 168.95ms)
- **Grid 100×100:** No speedup (narrow BFS levels, thread overhead dominates)

## How to Run

```bash
# Run all tests (correctness, determinism, performance)
cargo run --release

# Run in debug mode (slower but more output)
cargo run

# Run unit tests
cargo test
```

## Why This Strategy?

BFS has inherent level-by-level dependencies, but vertices within the same level can be explored independently. Level-synchronous parallelization:
- Maintains BFS semantics (correct level ordering)
- Ensures determinism (fixed split and merge order)
- Achieves practical speedup on graphs with wide levels
- Avoids lock contention and race conditions

See JUSTIFICATION.md for detailed analysis of this and 4 rejected alternatives.

## Limitations

- **Amdahl's Law**: Early and late BFS levels have few vertices, limiting parallelism
- **Graph topology**: Narrow graphs (grids, trees) see little benefit
- **Best for**: Random graphs, social networks, web graphs with high average degree

## Implementation Details

- **Language**: Rust
- **Parallelism**: Rayon (bounded thread pool)
- **Thresholds**: 
  - Graph < 100 vertices → sequential
  - Level < 50 vertices → sequential
- **Determinism**: Sort vertices by ID at every level
- **Memory**: Each worker uses private buffers (no shared writes during parallel phase)
