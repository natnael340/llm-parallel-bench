#!/usr/bin/env python3
"""
Quick demo runner for Smith-Waterman parallel implementation.
Shows a simple example with timing comparison.
"""

import time
from smith_waterman_baseline import SmithWaterman as BaselineSW
from algo_parallel import SmithWaterman as ParallelSW


def main():
    print("="*60)
    print("Smith-Waterman Parallel Implementation Demo")
    print("="*60)
    
    # Example sequences
    query = "ACGTACGTACGTACGT" * 10      # 160 bases
    reference = "ACGTACGTTACGTACG" * 10  # 160 bases (one mutation in middle)
    
    print(f"\nQuery length: {len(query)}")
    print(f"Reference length: {len(reference)}")
    print(f"Matrix size: {len(query)}×{len(reference)} = {len(query)*len(reference):,} cells")
    
    # Sequential baseline
    print("\n--- Sequential Baseline ---")
    baseline = BaselineSW(matchScore=2, mismatchScore=-1, gapScore=-1)
    t0 = time.perf_counter()
    aligned_a_seq, aligned_b_seq, score_seq, identity_seq = baseline.findAlignment(query, reference)
    t_seq = time.perf_counter() - t0
    
    print(f"Time: {t_seq:.4f}s")
    print(f"Score: {score_seq}")
    print(f"Identity: {identity_seq:.1f}%")
    print(f"Aligned length: {len(aligned_a_seq)}")
    
    # Parallel version
    print("\n--- Parallel Version ---")
    parallel = ParallelSW(matchScore=2, mismatchScore=-1, gapScore=-1, workers=4)
    t0 = time.perf_counter()
    aligned_a_par, aligned_b_par, score_par, identity_par = parallel.findAlignment(query, reference)
    t_par = time.perf_counter() - t0
    
    print(f"Time: {t_par:.4f}s")
    print(f"Score: {score_par}")
    print(f"Identity: {identity_par:.1f}%")
    print(f"Aligned length: {len(aligned_a_par)}")
    
    # Comparison
    print("\n--- Comparison ---")
    match = (aligned_a_seq == aligned_a_par and 
             aligned_b_seq == aligned_b_par and
             score_seq == score_par and
             identity_seq == identity_par)
    
    if match:
        print("✅ Outputs match exactly (correctness verified)")
    else:
        print("❌ Outputs differ!")
        return 1
    
    speedup = t_seq / t_par if t_par > 0 else 0
    print(f"\nSpeedup: {speedup:.2f}x", end="")
    
    if speedup < 1.0:
        print(f" (parallel is {1/speedup:.1f}x SLOWER due to overhead)")
        print("\nNote: This is expected for Smith-Waterman in Python.")
        print("The algorithm has strong data dependencies that prevent")
        print("effective parallelization at this scale. See JUSTIFICATION.md")
        print("for detailed explanation.")
    elif speedup > 1.0:
        print(f" (parallel is {speedup:.1f}x faster)")
    else:
        print(" (roughly equal)")
    
    print("\n" + "="*60)
    print("For comprehensive tests, run: python test_smith_waterman.py")
    print("="*60)
    
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
