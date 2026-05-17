#!/bin/bash
# Runner script for SCC parallel tests

echo "=== Running SCC Parallel Tests ==="
echo ""
echo "Running in debug mode (unoptimized)..."
cargo run --bin llm_written

echo ""
echo "=== Test Results ==="
cat run_summary.txt

echo ""
echo "=== Performance Results ==="
cat perf.txt

echo ""
echo "To run with optimizations for better performance:"
echo "  cargo run --release --bin llm_written"
