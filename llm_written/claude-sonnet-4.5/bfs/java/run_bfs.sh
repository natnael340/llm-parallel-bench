#!/bin/bash

# Compile all Java files if needed
if [ ! -f "BfsParallel.class" ] || [ ! -f "TestBfs.class" ]; then
    echo "Compiling Java files..."
    javac Graph.java BfsSequential.java BfsParallel.java TestBfs.java PerfBfs.java RunBfs.java
    echo ""
fi

# Run based on argument
if [ "$1" == "test" ]; then
    java TestBfs
elif [ "$1" == "perf" ]; then
    java PerfBfs
elif [ "$1" == "all" ]; then
    java TestBfs
    echo ""
    echo "=================================================="
    echo ""
    java PerfBfs
else
    echo "Usage: ./run_bfs.sh [test|perf|all]"
    echo "  test - Run correctness and determinism tests"
    echo "  perf - Run performance benchmarks"
    echo "  all  - Run both tests and benchmarks"
fi
