#!/bin/bash
# Runner script for Smith-Waterman differential testing

echo "=== Compiling Smith-Waterman ==="
javac SmithWatermanSequential.java SmithWaterman.java TestSmithWaterman.java
if [ $? -ne 0 ]; then
    echo "✗ Compilation failed"
    exit 1
fi
echo "✓ Compilation successful"
echo ""

echo "=== Running Differential Tests ==="
java TestSmithWaterman
EXIT_CODE=$?

if [ $EXIT_CODE -eq 0 ]; then
    echo ""
    echo "=== Summary ==="
    echo "✓ All tests passed (correctness, determinism, performance)"
    echo "See run_summary.txt and perf.txt for detailed results"
    exit 0
else
    echo ""
    echo "=== Summary ==="
    echo "✗ Some tests failed"
    exit 1
fi
