# SCC Parallel Implementation

This project parallelizes Tarjan's Strongly Connected Components (SCC) algorithm with edge reduction.

## Files

### Core Implementation
- **`scc_parallel.rs`** - Final parallel implementation (primary deliverable)
- **`scc_sequential.rs`** - Original sequential baseline for comparison
- **`main.rs`** - Comprehensive test harness with 6 test cases

### Documentation
- **`JUSTIFICATION.md`** - Detailed explanation for non-technical readers (600-1100 words)
- **`run_summary.txt`** - Test results showing correctness and determinism
- **`perf.txt`** - Performance metrics (speedup, threads, timing)
- **`REQUEST.md`** - Original parallelization request

### Utilities
- **`run_scc.sh`** - Convenience script to run all tests

## Quick Start

```bash
# Run all tests (debug mode)
cargo run

# Run with optimizations
cargo run --release

# Or use the convenience script
chmod +x run_scc.sh
./run_scc.sh
```

## Test Results

All 6 test cases pass:
- ✅ Correctness: Parallel output matches sequential baseline
- ✅ Determinism: Multiple runs produce identical results
- ✅ Edge cases: Empty graph, single node, simple cycles
- ✅ Medium scale: 100 nodes, 10 SCCs
- ✅ Large scale: 5000 nodes, 50 SCCs

## Performance

**Test configuration:** 5000 nodes, 50 SCCs, 16 CPU cores
- Sequential: 0.029s
- Parallel: 0.040s
- Speedup: 0.72× (slower due to thread overhead)

**Why slower?** Thread creation and memory cloning overhead dominates for graphs with small-to-medium SCCs. The implementation includes a sequential fallback for small inputs (< 1000 vertices or < 4 SCCs).

**When it's faster:** Graphs with hundreds of SCCs or very large SCCs (thousands of nodes each) would benefit from parallelization.

## Algorithm

1. **Find SCCs** (sequential): Use Tarjan's DFS algorithm
2. **Sort SCCs** (deterministic): By minimum node index
3. **Parallelize edge minimization**: Each thread processes a fixed chunk of SCCs
4. **Merge results**: In sorted order for determinism

## Determinism Guarantee

- Fixed SCC sorting by minimum node index
- Fixed chunking: `chunk_size = (num_sccs + num_threads - 1) / num_threads`
- Pre-allocated result array indexed by SCC position
- Fixed merge order (slot 0, then 1, then 2, etc.)

## Reproduction Commands

```bash
# Correctness and determinism
cargo run

# Performance (optimized)
cargo run --release

# View results
cat run_summary.txt
cat perf.txt
```

## Design Decisions

**Chosen strategy:** Parallel per-SCC edge minimization with bounded thread pool

**Rejected alternatives:**
1. Parallel Tarjan's DFS - determinism risk, complex synchronization
2. Wavefront parallelism - limited parallelism, high overhead
3. Rayon parallel iterators - non-determinism, dependency overhead
4. GPU acceleration - transfer overhead, portability issues

See `JUSTIFICATION.md` for detailed analysis.

## Safety Features

- Sequential fallback for small inputs (< 1000 vertices or < 4 SCCs)
- Thread count capped at CPU core count
- No data races (each thread writes to its own result slot)
- No shared mutable state during parallel phase

## Requirements

- Rust 1.70+ (uses `thread::available_parallelism()`)
- Standard library only (no external dependencies)

## License

This is a demonstration project for parallel algorithm implementation.
