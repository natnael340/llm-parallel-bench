# Methodology

I gather implmentation of BFS, Merge Sort and GEMM from github
Prepare tests for the implmentation of these algorithms
perfom manual test on the sequential alogrithms and make sure it passes all test
gather perfomance measure like time it take, to run

## Python

### unittest

`py -m unittest .\tests\test_bfs.py`

### performance test

`py -m tests.test_bfs_perf`

## C++

### unittest

`g++ tests/test_bfs.cpp BFS/bfs_seq.cpp -o ./tests/test_bfs`
`./tests/test_bfs`

### Performance test
