#!/usr/bin/env python3
"""
Differential test harness for BFS.
Tests correctness, determinism, and performance.
"""

import sys
import time
import hashlib
from typing import Callable
from bfs_sequential import Graph as SeqGraph, bfs as bfs_seq
from algo_parallel import Graph as ParGraph, bfs as bfs_par


def create_graph_sequential(edges: list[tuple[int, int]]) -> SeqGraph:
    """Create a sequential graph from edge list."""
    g = SeqGraph()
    for u, v in edges:
        g.add_edge(u, v)
    return g


def create_graph_parallel(edges: list[tuple[int, int]]) -> ParGraph:
    """Create a parallel graph from edge list."""
    g = ParGraph()
    for u, v in edges:
        g.add_edge(u, v)
    return g


def hash_result(result: list[int]) -> str:
    """Hash a result list for determinism checking."""
    return hashlib.sha256(str(result).encode()).hexdigest()


def test_case(name: str, edges: list[tuple[int, int]], start: int, expected_size: int = None) -> bool:
    """Run a single test case comparing sequential and parallel."""
    print(f"\n{'='*60}")
    print(f"Test: {name}")
    print(f"{'='*60}")
    
    # Build graphs
    g_seq = create_graph_sequential(edges)
    g_par = create_graph_parallel(edges)
    
    # Run sequential
    start_time = time.perf_counter()
    result_seq = bfs_seq(g_seq, start)
    time_seq = time.perf_counter() - start_time
    
    # Run parallel (first time)
    start_time = time.perf_counter()
    result_par1 = bfs_par(g_par, start)
    time_par1 = time.perf_counter() - start_time
    
    # Run parallel (second time for determinism check)
    start_time = time.perf_counter()
    result_par2 = bfs_par(g_par, start)
    time_par2 = time.perf_counter() - start_time
    
    # Check correctness (same elements, same order for valid BFS)
    # Note: BFS order may vary, but we enforce deterministic order via sorting
    print(f"Sequential result: {result_seq[:20]}{'...' if len(result_seq) > 20 else ''}")
    print(f"Parallel result 1: {result_par1[:20]}{'...' if len(result_par1) > 20 else ''}")
    print(f"Parallel result 2: {result_par2[:20]}{'...' if len(result_par2) > 20 else ''}")
    
    # Size check
    size_match = len(result_seq) == len(result_par1) == len(result_par2)
    if expected_size is not None:
        size_match = size_match and len(result_seq) == expected_size
    
    # Content check (same vertices visited)
    content_match = set(result_seq) == set(result_par1) == set(result_par2)
    
    # Determinism check (exact same order for parallel runs)
    hash_par1 = hash_result(result_par1)
    hash_par2 = hash_result(result_par2)
    deterministic = (hash_par1 == hash_par2)
    
    print(f"\nResults:")
    print(f"  Size: seq={len(result_seq)}, par1={len(result_par1)}, par2={len(result_par2)}")
    print(f"  Size match: {size_match}")
    print(f"  Content match (same vertices): {content_match}")
    print(f"  Deterministic (par1==par2): {deterministic}")
    print(f"  Hash par1: {hash_par1[:16]}...")
    print(f"  Hash par2: {hash_par2[:16]}...")
    print(f"\nTiming:")
    print(f"  Sequential: {time_seq*1000:.3f} ms")
    print(f"  Parallel 1: {time_par1*1000:.3f} ms")
    print(f"  Parallel 2: {time_par2*1000:.3f} ms")
    
    passed = size_match and content_match and deterministic
    print(f"\n{'✓ PASS' if passed else '✗ FAIL'}")
    
    return passed


def generate_grid_graph(rows: int, cols: int) -> list[tuple[int, int]]:
    """Generate a grid graph (rows x cols)."""
    edges = []
    for r in range(rows):
        for c in range(cols):
            node = r * cols + c
            # Right edge
            if c < cols - 1:
                edges.append((node, node + 1))
            # Down edge
            if r < rows - 1:
                edges.append((node, node + cols))
    return edges


def generate_tree_graph(levels: int) -> list[tuple[int, int]]:
    """Generate a complete binary tree."""
    edges = []
    nodes = 2 ** levels - 1
    for i in range(nodes):
        left = 2 * i + 1
        right = 2 * i + 2
        if left < nodes:
            edges.append((i, left))
        if right < nodes:
            edges.append((i, right))
    return edges


def main() -> int:
    """Run all test cases."""
    print("BFS Differential Test Suite")
    print("=" * 60)
    
    results = []
    
    # Edge case: empty graph
    results.append(test_case(
        "Edge: Start vertex not in graph",
        edges=[],
        start=99,
        expected_size=0
    ))
    
    # Edge case: single vertex
    results.append(test_case(
        "Edge: Single vertex",
        edges=[],
        start=1,
        expected_size=0  # No edges, vertex not in graph
    ))
    
    # Small: Simple path
    results.append(test_case(
        "Small: Linear path (5 vertices)",
        edges=[(1, 2), (2, 3), (3, 4), (4, 5)],
        start=1,
        expected_size=5
    ))
    
    # Small: Star graph
    results.append(test_case(
        "Small: Star graph (center + 6 leaves)",
        edges=[(0, 1), (0, 2), (0, 3), (0, 4), (0, 5), (0, 6)],
        start=0,
        expected_size=7
    ))
    
    # Medium: Grid
    results.append(test_case(
        "Medium: 10x10 Grid (100 vertices)",
        edges=generate_grid_graph(10, 10),
        start=0,
        expected_size=100
    ))
    
    # Medium: Binary tree
    results.append(test_case(
        "Medium: Binary tree (7 levels, 127 vertices)",
        edges=generate_tree_graph(7),
        start=0,
        expected_size=127
    ))
    
    # Large: Big grid
    results.append(test_case(
        "Large: 100x100 Grid (10,000 vertices)",
        edges=generate_grid_graph(100, 100),
        start=0,
        expected_size=10000
    ))
    
    # Large: Deep tree
    results.append(test_case(
        "Large: Binary tree (12 levels, 4095 vertices)",
        edges=generate_tree_graph(12),
        start=0,
        expected_size=4095
    ))
    
    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    total = len(results)
    passed = sum(results)
    print(f"Total: {total}")
    print(f"Passed: {passed}")
    print(f"Failed: {total - passed}")
    
    if passed == total:
        print("\n✓ ALL TESTS PASSED")
        return 0
    else:
        print("\n✗ SOME TESTS FAILED")
        return 1


if __name__ == "__main__":
    sys.exit(main())
