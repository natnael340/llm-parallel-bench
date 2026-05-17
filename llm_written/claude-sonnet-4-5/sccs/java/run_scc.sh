#!/bin/bash
# Graph SCC Edge Reduction - Test Runner

echo "╔════════════════════════════════════════════════════╗"
echo "║     Graph SCC Edge Reduction - Full Test Suite    ║"
echo "╚════════════════════════════════════════════════════╝"
echo ""

# Compile all files
echo "Compiling source files..."
javac Graph.java GraphParallel.java TestGraphSCC.java PerfTest.java PerfTestLarge.java
if [ $? -ne 0 ]; then
    echo "❌ Compilation failed!"
    exit 1
fi
echo "✓ Compilation successful"
echo ""

# Run correctness and determinism tests
echo "Running correctness and determinism tests..."
java TestGraphSCC > run_summary.txt 2>&1
TEST_RESULT=$?
cat run_summary.txt
echo ""

if [ $TEST_RESULT -ne 0 ]; then
    echo "❌ Tests failed!"
    exit 1
fi

# Run performance tests
echo "Running performance tests..."
echo "" > perf.txt
java PerfTest
java PerfTestLarge

echo ""
echo "╔════════════════════════════════════════════════════╗"
echo "║                  ALL TESTS COMPLETE                ║"
echo "╚════════════════════════════════════════════════════╝"
echo ""
echo "Results written to:"
echo "  - run_summary.txt (correctness & determinism)"
echo "  - perf.txt (performance benchmarks)"
echo ""
