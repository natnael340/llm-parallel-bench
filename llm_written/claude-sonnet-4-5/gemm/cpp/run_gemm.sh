#!/bin/bash
# run_gemm.sh - Compile and run GEMM tests

set -e

echo "Compiling GEMM implementation..."
g++ -O3 -fopenmp gemm_common.cpp gemm_seq.cpp gemm_parallel.cpp test_gemm.cpp -o test_gemm

echo "Running tests..."
./test_gemm

echo ""
echo "Test complete. Results available in:"
echo "  - run_summary.txt (correctness and determinism)"
echo "  - perf.txt (performance details)"
