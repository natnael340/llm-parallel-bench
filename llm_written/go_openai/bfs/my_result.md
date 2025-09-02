The parallel implmenetation seem to work, the llm correctly parallelize it and the implemnetation passed all the test and edge cases but the problem it's facing was deterministic behaviour, it's mainly due the nature of the algorithm, while effectively parallelizing the code, but while perfomance test the parallel algorithm scored much worse that the sequential impelmentation here are the result

### Sequential

==============================

- RUN TestBFSSpeed
- bfs_test.go:214: BFS took 62.46 ms.
- PASS: TestBFSSpeed (6.43s)

### Parallel

================================

- RUN TestBFSSpeed
- bfs_test.go:214: BFS took 278.48 ms.
- PASS: TestBFSSpeed (28.03s)
