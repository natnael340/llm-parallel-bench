# BFS Performance Report

Graph type : Complete Graph
Nodes : 2000
Edges : ≈1,999,000 undirected (≈3,998,000 directed)
Measurement : timeit (5 repeats, 20 iterations per repeat, GC disabled)

## SEQUENTIAL: Python

### Results

Average BFS runtime : 523.51 ms/run
Standard deviation : ±5.11 ms
Number of repeats : 5

### Interpretation

BFS on the complete graph with 2000 nodes (~4M directed edges) completes
in ~523 ms per run. The low standard deviation (~1%) indicates stable
performance across runs. This result can be used as a baseline for
comparison with the multi-core BFS implementation.

## SEQUENTIAL: GO

### Results

Average BFS runtime : 87.34 ms/run  
Standard deviation : ±0.28 ms  
Number of repeats : 5

### Interpretation

BFS on the complete graph with 2000 nodes (~4M directed edges) completes
in ~87 ms per run. The very low standard deviation (<1%) indicates stable
performance across runs, providing a strong sequential baseline for
comparison against parallel implementations.

## PARALLEL: GO

### Results

Average BFS runtime : 13.11 ms/run  
Standard deviation : ±1.07 ms  
Number of repeats : 5

### Interpretation

Parallel BFS on the complete graph with 2000 nodes (~4M directed edges)
completes in ~13 ms per run. The standard deviation (~8%) shows moderate
variation across runs, but overall the implementation is significantly
faster than the sequential baseline (~87 ms/run), demonstrating strong
scalability on dense graphs.

## Sequential: CPP

### Results

Average BFS runtime : 65.72 ms/run  
Standard deviation : ±0.44 ms  
Number of repeats : 5

### Interpretation

BFS on the complete graph with 2000 nodes (~4M directed edges) completes
in ~66 ms per run. The very low standard deviation (<1%) indicates stable
performance across runs, making this a reliable sequential baseline for
comparison with parallel implementations.

### Results

Sequential BFS  
Average runtime : 65.56 ms/run  
Standard deviation : ±0.17 ms  
Number of repeats : 5

Parallel BFS (OpenMP)  
Average runtime : 102.00 ms/run  
Standard deviation : ±1.44 ms  
Number of repeats : 5

### Interpretation

On the complete graph with 2000 nodes (~4M directed edges), the parallel
OpenMP implementation was slightly slower than the sequential baseline.
This is due to the overhead of bucket creation, copying neighbor lists,
and the serial filtering of the global visited set dominating the runtime.
While the parallel design ensures determinism and correctness, it offers
no speedup for dense graphs where the merge step is the true bottleneck.
