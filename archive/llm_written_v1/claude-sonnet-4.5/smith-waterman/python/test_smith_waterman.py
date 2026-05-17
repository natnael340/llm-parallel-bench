#!/usr/bin/env python3
"""
Differential test harness for Smith-Waterman algorithm.
Tests correctness (sequential vs parallel), determinism (repeated parallel runs), 
and performance on various input sizes.
"""

import sys
import time
import hashlib
import os
from typing import Tuple
from smith_waterman_baseline import SmithWaterman as BaselineSW
from algo_parallel import SmithWaterman as ParallelSW


def hash_result(result: Tuple[str, str, float, int]) -> str:
    """Create deterministic hash of alignment result."""
    aligned_a, aligned_b, score, identity = result
    content = f"{aligned_a}|{aligned_b}|{score}|{identity:.6f}"
    return hashlib.sha256(content.encode()).hexdigest()[:16]


def generate_sequence(length: int, seed: int = 42) -> str:
    """Generate deterministic DNA sequence."""
    import random
    random.seed(seed)
    bases = ['A', 'C', 'G', 'T']
    return ''.join(random.choice(bases) for _ in range(length))


def run_test_case(name: str, query: str, reference: str, workers: int = None):
    """Run differential test for a single case."""
    print(f"\n{'='*60}")
    print(f"Test Case: {name}")
    print(f"Query length: {len(query)}, Reference length: {len(reference)}")
    print(f"{'='*60}")
    
    # Baseline sequential
    baseline = BaselineSW(matchScore=2, mismatchScore=-1, gapScore=-1)
    
    t0 = time.perf_counter()
    result_seq = baseline.findAlignment(query, reference)
    t_seq = time.perf_counter() - t0
    
    hash_seq = hash_result(result_seq)
    print(f"✓ Sequential: {t_seq:.4f}s, hash={hash_seq}")
    
    # Parallel run 1
    parallel = ParallelSW(matchScore=2, mismatchScore=-1, gapScore=-1, workers=workers)
    
    t0 = time.perf_counter()
    result_par1 = parallel.findAlignment(query, reference)
    t_par1 = time.perf_counter() - t0
    
    hash_par1 = hash_result(result_par1)
    print(f"✓ Parallel-1: {t_par1:.4f}s, hash={hash_par1}")
    
    # Parallel run 2 (determinism check)
    t0 = time.perf_counter()
    result_par2 = parallel.findAlignment(query, reference)
    t_par2 = time.perf_counter() - t0
    
    hash_par2 = hash_result(result_par2)
    print(f"✓ Parallel-2: {t_par2:.4f}s, hash={hash_par2}")
    
    # Correctness check
    if result_seq != result_par1:
        print(f"❌ FAIL: Sequential and Parallel outputs differ!")
        print(f"   Sequential: {result_seq}")
        print(f"   Parallel:   {result_par1}")
        return False
    
    # Determinism check
    if hash_par1 != hash_par2:
        print(f"❌ FAIL: Parallel runs are non-deterministic!")
        print(f"   Run 1 hash: {hash_par1}")
        print(f"   Run 2 hash: {hash_par2}")
        return False
    
    print(f"✅ PASS: Correctness and determinism verified")
    
    # Performance summary (only for larger inputs)
    if len(query) * len(reference) >= 10000:
        speedup = t_seq / t_par1 if t_par1 > 0 else 0
        print(f"   Speedup: {speedup:.2f}x (seq={t_seq:.4f}s, par={t_par1:.4f}s)")
        return True, t_seq, t_par1, speedup
    
    return True, None, None, None


def main():
    """Run comprehensive differential test suite."""
    print("Smith-Waterman Differential Test Suite")
    print(f"Workers: {os.cpu_count()} cores detected")
    
    results = []
    
    # Edge cases
    print("\n" + "="*60)
    print("EDGE CASES")
    print("="*60)
    
    # Empty sequences
    success, *_ = run_test_case("Empty query", "", "ACGT", workers=2)
    results.append(("Edge: Empty query", success))
    
    success, *_ = run_test_case("Empty reference", "ACGT", "", workers=2)
    results.append(("Edge: Empty reference", success))
    
    success, *_ = run_test_case("Both empty", "", "", workers=2)
    results.append(("Edge: Both empty", success))
    
    # Single character
    success, *_ = run_test_case("Single char match", "A", "A", workers=2)
    results.append(("Edge: Single char", success))
    
    # Small identical
    success, *_ = run_test_case("Small identical", "ACGT", "ACGT", workers=2)
    results.append(("Edge: Small identical", success))
    
    # Small cases
    print("\n" + "="*60)
    print("SMALL CASES")
    print("="*60)
    
    success, *_ = run_test_case(
        "Small similar (10x10)", 
        generate_sequence(10, seed=1),
        generate_sequence(10, seed=2),
        workers=2
    )
    results.append(("Small: 10x10", success))
    
    success, *_ = run_test_case(
        "Small divergent (20x20)",
        "A" * 20,
        "C" * 20,
        workers=2
    )
    results.append(("Small: 20x20 divergent", success))
    
    # Medium cases
    print("\n" + "="*60)
    print("MEDIUM CASES")
    print("="*60)
    
    success, t_seq, t_par, speedup = run_test_case(
        "Medium (100x100)",
        generate_sequence(100, seed=10),
        generate_sequence(100, seed=20),
        workers=4
    )
    results.append(("Medium: 100x100", success))
    
    success, t_seq, t_par, speedup = run_test_case(
        "Medium (200x200)",
        generate_sequence(200, seed=30),
        generate_sequence(200, seed=40),
        workers=4
    )
    results.append(("Medium: 200x200", success))
    
    # Large cases (performance check)
    print("\n" + "="*60)
    print("LARGE CASES (Performance Check)")
    print("="*60)
    
    perf_results = []
    
    success, t_seq, t_par, speedup = run_test_case(
        "Large (400x400)",
        generate_sequence(400, seed=100),
        generate_sequence(400, seed=200),
        workers=None  # Use all cores
    )
    results.append(("Large: 400x400", success))
    if speedup is not None:
        perf_results.append(("400x400", t_seq, t_par, speedup))
    
    success, t_seq, t_par, speedup = run_test_case(
        "Large (600x600)",
        generate_sequence(600, seed=300),
        generate_sequence(600, seed=400),
        workers=None
    )
    results.append(("Large: 600x600", success))
    if speedup is not None:
        perf_results.append(("600x600", t_seq, t_par, speedup))
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    passed = sum(1 for _, success in results if success)
    total = len(results)
    
    print(f"\nResults: {passed}/{total} tests passed")
    for name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"  {status}: {name}")
    
    if perf_results:
        print(f"\nPerformance Summary:")
        for case, t_seq, t_par, speedup in perf_results:
            print(f"  {case}: {speedup:.2f}x speedup (seq={t_seq:.3f}s, par={t_par:.3f}s)")
    
    # Exit code
    if passed == total:
        print("\n✅ All tests passed!")
        return 0
    else:
        print(f"\n❌ {total - passed} test(s) failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
