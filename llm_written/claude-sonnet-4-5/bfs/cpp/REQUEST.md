# Parallelization Request

## Input Algorithm
Breadth-First Search (BFS) on a graph

## Language
C++

## Baseline Implementation
- File: bfs_seq.hpp (provided inline)
- Dependencies: graph.h, queue, iostream
- Function signature: `std::vector<int> bfs(Graph& g, int start_vertex)`
- Returns: vector of vertices in BFS traversal order

## Constraints
- Must maintain correctness (same output as sequential)
- Must be deterministic (same input → same output every run)
- Must respect resource bounds (CPU cores)
- C++ with OpenMP preferred

## Key Observations
- BFS has strict level-order dependencies
- Each level must complete before next level begins
- Within a level, neighbors can be discovered in parallel
- Final output order must match sequential baseline
