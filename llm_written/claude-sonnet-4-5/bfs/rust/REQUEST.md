# Parallelization Request

## Task
Transform sequential BFS (Breadth-First Search) implementation in Rust into a correct, deterministic, parallel version.

## Baseline Code
- Language: Rust
- Algorithm: BFS graph traversal
- Current implementation: Sequential BFS using VecDeque and HashSet
- Graph structure: Undirected graph with HashMap<i32, Vec<i32>>

## Constraints
1. Correctness: outputs MUST match sequential baseline
2. Determinism: same input MUST produce same output on every run
3. Performance: maximize speedup on large graphs
4. Language: Rust with Rayon, bounded thread pool
5. Avoid shared mutable state and global shared state
6. Preserve order when required

## Key Challenges
- BFS has inherent level-by-level ordering requirements
- Visited set is shared state
- Result ordering must be deterministic
- Need to parallelize within each level while maintaining correctness
