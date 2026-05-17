#!/usr/bin/env python3
"""
Differential test harness for GEMM parallelization.
Tests correctness, determinism, and performance.
"""

import sys
import time
import hashlib
import json
from typing import List

# Import both implementations
from gemm_sequential import gemm as gemm_seq
from gemm_parallel import gemm as gemm_par


def matrix_hash(matrix: List[List[float]]) -> str:
    """Compute a deterministic hash of a matrix."""
    # Convert to bytes in a deterministic way
    data = json.dumps(matrix, sort_keys=True).encode('utf-8')
    return hashlib.sha256(data).hexdigest()


def matrices_equal(A: List[List[float]], B: List[List[float]], tol: float = 1e-10) -> bool:
    """Check if two matrices are equal within tolerance."""
    if len(A) != len(B):
        return False
    for i in range(len(A)):
        if len(A[i]) != len(B[i]):
            return False
        for j in range(len(A[i])):
            if abs(A[i][j] - B[i][j]) > tol:
                return False
    return True


def make_matrix(m: int, n: int, seed: int = 0) -> List[List[float]]:
    """Create a deterministic test matrix."""
    # Simple deterministic pattern
    return [[(i * n + j + seed) * 0.1 for j in range(n)] for i in range(m)]


def run_test(name: str, A: List[List[float]], B: List[List[float]], 
             alpha: float = 1.0, beta: float = 0.0, C=None) -> dict:
    """Run a single test case and return results."""
    print(f"\n{'='*60}")
    print(f"Test: {name}")
    print(f"  A: {len(A)}x{len(A[0])}, B: {len(B)}x{len(B[0])}")
    
    # Run sequential
    t0 = time.perf_counter()
    result_seq = gemm_seq(A, B, alpha=alpha, C=C, beta=beta)
    t_seq = time.perf_counter() - t0
    hash_seq = matrix_hash(result_seq)
    
    # Run parallel (first run)
    t0 = time.perf_counter()
    result_par1 = gemm_par(A, B, alpha=alpha, C=C, beta=beta)
    t_par1 = time.perf_counter() - t0
    hash_par1 = matrix_hash(result_par1)
    
    # Run parallel (second run for determinism check)
    t0 = time.perf_counter()
    result_par2 = gemm_par(A, B, alpha=alpha, C=C, beta=beta)
    t_par2 = time.perf_counter() - t0
    hash_par2 = matrix_hash(result_par2)
    
    # Run parallel (third run)
    t0 = time.perf_counter()
    result_par3 = gemm_par(A, B, alpha=alpha, C=C, beta=beta)
    t_par3 = time.perf_counter() - t0
    hash_par3 = matrix_hash(result_par3)
    
    # Check correctness
    correct = matrices_equal(result_seq, result_par1)
    
    # Check determinism
    deterministic = (hash_par1 == hash_par2 == hash_par3)
    
    print(f"  Sequential time: {t_seq:.6f}s")
    print(f"  Parallel time (run 1): {t_par1:.6f}s")
    print(f"  Parallel time (run 2): {t_par2:.6f}s")
    print(f"  Parallel time (run 3): {t_par3:.6f}s")
    print(f"  Hash (seq):  {hash_seq[:16]}...")
    print(f"  Hash (par1): {hash_par1[:16]}...")
    print(f"  Hash (par2): {hash_par2[:16]}...")
    print(f"  Hash (par3): {hash_par3[:16]}...")
    print(f"  Correctness: {'PASS' if correct else 'FAIL'}")
    print(f"  Determinism: {'PASS' if deterministic else 'FAIL'}")
    
    if t_seq > 0:
        speedup = t_seq / t_par1
        print(f"  Speedup: {speedup:.2f}x")
    else:
        speedup = None
    
    return {
        'name': name,
        'correct': correct,
        'deterministic': deterministic,
        't_seq': t_seq,
        't_par': t_par1,
        'speedup': speedup,
        'hash_seq': hash_seq,
        'hash_par1': hash_par1,
        'hash_par2': hash_par2,
        'hash_par3': hash_par3,
    }


def main():
    print("GEMM Differential Test Suite")
    print("="*60)
    
    results = []
    
    # Test 1: Empty edge case (1x1)
    A1 = [[2.0]]
    B1 = [[3.0]]
    results.append(run_test("1x1 matrices", A1, B1))
    
    # Test 2: Small matrices
    A2 = make_matrix(4, 5, seed=1)
    B2 = make_matrix(5, 6, seed=2)
    results.append(run_test("Small (4x5) x (5x6)", A2, B2))
    
    # Test 3: Medium matrices (single tile)
    A3 = make_matrix(32, 32, seed=3)
    B3 = make_matrix(32, 32, seed=4)
    results.append(run_test("Medium (32x32) x (32x32)", A3, B3))
    
    # Test 4: Medium matrices (multiple tiles)
    A4 = make_matrix(100, 80, seed=5)
    B4 = make_matrix(80, 120, seed=6)
    results.append(run_test("Medium (100x80) x (80x120)", A4, B4))
    
    # Test 5: Larger matrices
    A5 = make_matrix(200, 150, seed=7)
    B5 = make_matrix(150, 200, seed=8)
    results.append(run_test("Large (200x150) x (150x200)", A5, B5))
    
    # Test 6: Non-square with alpha/beta
    A6 = make_matrix(50, 60, seed=9)
    B6 = make_matrix(60, 70, seed=10)
    results.append(run_test("With alpha=2.5 (50x60) x (60x70)", A6, B6, alpha=2.5))
    
    # Test 7: Very large (performance test)
    print("\n" + "="*60)
    print("Performance test on large matrices...")
    A7 = make_matrix(400, 300, seed=11)
    B7 = make_matrix(300, 400, seed=12)
    results.append(run_test("Very Large (400x300) x (300x400)", A7, B7))
    
    # Summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    
    all_correct = all(r['correct'] for r in results)
    all_deterministic = all(r['deterministic'] for r in results)
    
    print(f"Total tests: {len(results)}")
    print(f"Correctness: {'ALL PASS' if all_correct else 'SOME FAILED'}")
    print(f"Determinism: {'ALL PASS' if all_deterministic else 'SOME FAILED'}")
    
    # Write summary to file
    with open('run_summary.txt', 'w') as f:
        f.write("GEMM Differential Test Results\n")
        f.write("="*60 + "\n\n")
        
        for r in results:
            f.write(f"Test: {r['name']}\n")
            f.write(f"  Correctness: {'PASS' if r['correct'] else 'FAIL'}\n")
            f.write(f"  Determinism: {'PASS' if r['deterministic'] else 'FAIL'}\n")
            f.write(f"  Sequential time: {r['t_seq']:.6f}s\n")
            f.write(f"  Parallel time: {r['t_par']:.6f}s\n")
            if r['speedup']:
                f.write(f"  Speedup: {r['speedup']:.2f}x\n")
            f.write(f"  Hash (seq):  {r['hash_seq']}\n")
            f.write(f"  Hash (par1): {r['hash_par1']}\n")
            f.write(f"  Hash (par2): {r['hash_par2']}\n")
            f.write(f"  Hash (par3): {r['hash_par3']}\n")
            f.write("\n")
        
        f.write("="*60 + "\n")
        f.write(f"Overall Correctness: {'PASS' if all_correct else 'FAIL'}\n")
        f.write(f"Overall Determinism: {'PASS' if all_deterministic else 'FAIL'}\n")
    
    # Write performance data
    with open('perf.txt', 'w') as f:
        f.write("GEMM Performance Results\n")
        f.write("="*60 + "\n\n")
        
        # Find the largest test
        largest = max(results, key=lambda r: r['t_seq'])
        f.write(f"Largest test: {largest['name']}\n")
        f.write(f"  Sequential time: {largest['t_seq']:.6f}s\n")
        f.write(f"  Parallel time: {largest['t_par']:.6f}s\n")
        if largest['speedup']:
            f.write(f"  Speedup: {largest['speedup']:.2f}x\n")
        f.write(f"  Workers: capped at CPU count (max 8)\n")
        f.write(f"  Correctness: {'PASS' if largest['correct'] else 'FAIL'}\n")
        f.write(f"  Determinism: {'PASS' if largest['deterministic'] else 'FAIL'}\n")
    
    print("\nResults written to run_summary.txt and perf.txt")
    
    # Exit with appropriate code
    if all_correct and all_deterministic:
        print("\n✓ All tests passed!")
        sys.exit(0)
    else:
        print("\n✗ Some tests failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()
