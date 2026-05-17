the claude impelemntation didn't completed with in the given constraints.
this is becuase of level-synchronous BFS algorithm, the timeout is caused by
python IPC overhead caused by multiprocessing module. the python GIL also makes
thread-based parallelism ineffective for CPU-bound tasks like BFS.

This implemntation follows the GPT5 approach of level-synchronous BFS using
multiprocessing to achieve parallelism. however, due to the overhead of process
creation and inter-process communication, the performance gains are limited,
especially for smaller graphs.

we reported the python multiprocessig overhead in the introduction of our results

## The good thing about Claude is it identified the problem:

For these test sizes, ProcessPoolExecutor overhead exceeds parallelization benefit.
BFS is well-suited for parallel execution on:

- Large graphs (millions of vertices)
- Wide levels (thousands of vertices per level consistently)
- Lower overhead parallel frameworks (threads, compiled languages)

Current implementation correctly prioritizes determinism and correctness.
Sequential fallback at 100 vertices/level prevents worst-case overhead on tiny levels.

For Python BFS, sequential implementation is appropriate for graphs <100K vertices.
Parallel BFS shows value only on very large graphs where level width justifies
process spawning overhead.

This is a great thing for the llm implemntation,
but one problem we noticed is the soring this would make the result
incorrect compared to the sequential BFS implemntation visiting order
