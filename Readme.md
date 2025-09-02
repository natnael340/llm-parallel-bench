# Methodology

I gather implmentation of BFS, Merge Sort and GEMM from github
Prepare tests for the implmentation of these algorithms
perfom manual test on the sequential alogrithms and make sure it passes all test
gather perfomance measure like time it take, to run

## Python

### unittest

`python -m unittest ./tests/python/test_bfs.py`

## C++

### Build test

`g++ -O3 BFS/cpp/graph.cpp BFS/cpp/bfs_seq.cpp tests/cpp/test_bfs.cpp -o ./tests/cpp/test_bfs`

### Run tests

`./tests/test_bfs`

## Go

`go test -v ./tests/go/`
