
import os
import sys
import time
import hashlib
import argparse
from typing import Tuple

# Import the sequential and parallel implementations
from algo_sequential import SmithWaterman as SmithWatermanSequential
from algo_parallel import SmithWaterman as SmithWatermanParallel

# --- Test Data ---

def generate_sequence(length: int, seed: int) -> str:
    """Generates a pseudo-random DNA sequence."""
    bases = ['A', 'C', 'G', 'T']
    m = 2**31 - 1
    a = 1103515245
    c = 12345
    
    rand_state = seed
    seq = []
    for _ in range(length):
        rand_state = (a * rand_state + c) % m
        seq.append(bases[rand_state % 4])
    return "".join(seq)

TEST_CASES = {
    "empty": ("", ""),
    "edge_case_1": ("A", ""),
    "edge_case_2": ("", "A"),
    "small": ("ACG", "AC"),
    "medium": (generate_sequence(100, 42), generate_sequence(90, 43)),
    "large": (generate_sequence(1500, 123), generate_sequence(1400, 456)),
    "large_mismatch": (generate_sequence(1500, 1), "A" * 1400),
}

# --- Utility Functions ---

def run_alignment(aligner_class, query: str, reference: str, **kwargs) -> Tuple[Tuple[str, str, int, float], float]:
    """Runs alignment and measures execution time."""
    aligner = aligner_class(**kwargs)
    start_time = time.monotonic()
    result = aligner.findAlignment(query, reference)
    duration = time.monotonic() - start_time
    return result, duration

def hash_result(result: Tuple[str, str, int, float]) -> str:
    """Hashes the alignment result for determinism checks."""
    result_str = f"{result[0]}|{result[1]}|{result[2]}|{result[3]:.4f}"
    return hashlib.sha256(result_str.encode()).hexdigest()

def print_summary(test_name: str, status: str, details: str = ""):
    """Prints a formatted summary line."""
    print(f"{test_name:<20} | {status:<10} | {details}")
    
# --- Main Test Runner ---

def main():
    parser = argparse.ArgumentParser(description="Differential test runner for Smith-Waterman.")
    parser.add_argument('--perf', action='store_true', help="Run performance checks on large inputs.")
    args = parser.parse_args()

    scoring_params = {"matchScore": 2, "mismatchScore": -1, "gapScore": -1}

    print("="*60)
    print("Running Smith-Waterman Differential and Determinism Tests")
    print("="*60)
    print(f"{'Test Case':<20} | {'Status':<10} | {'Details'}")
    print("-" * 60)

    all_tests_passed = True
    evidence_dir = "evidence"
    if not os.path.exists(evidence_dir):
        os.makedirs(evidence_dir)
        
    summary_path = os.path.join(evidence_dir, "run_summary.txt")
    perf_path = os.path.join(evidence_dir, "perf.txt")

    with open(summary_path, "w") as summary_file, open(perf_path, "w") as perf_file:
        summary_file.write(f"{'Test Case':<20} | {'Status':<10} | {'Details'}\n")
        summary_file.write("-" * 60 + "\n")
        if args.perf:
            perf_file.write(f"{'Test Case':<20} | {'Seq Time (s)':<15} | {'Par Time (s)':<15} | {'Speedup':<10} | {'Cores':<5}\n")
            perf_file.write("-" * 70 + "\n")

        for name, (query, ref) in TEST_CASES.items():
            try:
                # 1. Correctness Check (Sequential vs. Parallel)
                seq_result, seq_duration = run_alignment(SmithWatermanSequential, query, ref, **scoring_params)
                par_result, par_duration = run_alignment(SmithWatermanParallel, query, ref, **scoring_params)

                if hash_result(seq_result) != hash_result(par_result):
                    status = "FAIL"
                    details = "Correctness mismatch"
                    print_summary(name, status, details)
                    summary_file.write(f"{name:<20} | {status:<10} | {details}\n")
                    all_tests_passed = False
                    continue

                # 2. Determinism Check (Parallel vs. Parallel)
                par_result_run1, _ = run_alignment(SmithWatermanParallel, query, ref, **scoring_params)
                par_result_run2, _ = run_alignment(SmithWatermanParallel, query, ref, **scoring_params)

                hash1 = hash_result(par_result_run1)
                hash2 = hash_result(par_result_run2)

                if hash1 != hash2:
                    status = "FAIL"
                    details = f"Determinism mismatch: {hash1[:8]} != {hash2[:8]}"
                    print_summary(name, status, details)
                    summary_file.write(f"{name:<20} | {status:<10} | {details}\n")
                    all_tests_passed = False
                    continue

                status = "PASS"
                details = f"Seq: {seq_duration:.4f}s, Par: {par_duration:.4f}s. Hashes: {hash1[:8]} == {hash2[:8]}"
                print_summary(name, status, details)
                summary_file.write(f"{name:<20} | {status:<10} | {details}\n")

                # 3. Performance Check (optional)
                if args.perf and name.startswith("large"):
                    speedup = seq_duration / par_duration if par_duration > 0 else float('inf')
                    cores = os.cpu_count() or 1
                    perf_file.write(f"{name:<20} | {seq_duration:<15.4f} | {par_duration:<15.4f} | {speedup:<10.2f}x | {cores:<5}\n")
                    
                    if speedup < 1.3:
                        print_summary(f"{name} (Perf)", "WARN", f"Speedup is {speedup:.2f}x, below target of 1.3x")
                    else:
                        print_summary(f"{name} (Perf)", "PASS", f"Speedup is {speedup:.2f}x")

            except Exception as e:
                status = "ERROR"
                details = f"An exception occurred: {e}"
                print_summary(name, status, details)
                summary_file.write(f"{name:<20} | {status:<10} | {details}\n")
                all_tests_passed = False

    print("=" * 60)
    if all_tests_passed:
        print("All tests passed successfully.")
        sys.exit(0)
    else:
        print("Some tests failed. Check logs and evidence/run_summary.txt for details.")
        sys.exit(1)

if __name__ == "__main__":
    main()
