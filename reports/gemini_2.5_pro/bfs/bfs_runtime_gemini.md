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

## PARALLEL: Python

### Results

Average BFS runtime : 5485.45 ms/run  
Standard deviation : ±71.95 ms  
Number of repeats : 5

### Interpretation

BFS on the complete graph with 2000 nodes (~4M directed edges) completes
in ~5485 ms per run. The standard deviation (~1.3%) indicates stable
performance across runs, but the runtime is an order of magnitude slower
than the sequential baseline, showing poor scalability for dense graphs.

## SEQUENTIAL: GO

### Results

Average BFS runtime : 87.34 ms/run  
Standard deviation : ±0.28 ms  
Number of repeats : 5

## PARALLEL: GO

### Results

Average BFS runtime : 51.51 ms/run
Standard deviation : ±2.35 ms  
Number of repeats : 5

## SEQUENTIAL: CPP

### Results

Average BFS runtime : 65.72 ms/run  
Standard deviation : ±0.44 ms  
Number of repeats : 5

## PARALLEL: CPP

### Results

Average BFS runtime : 1268.123367 ms/run
Standard deviation : ±21.97 ms  
Number of repeats : 5
