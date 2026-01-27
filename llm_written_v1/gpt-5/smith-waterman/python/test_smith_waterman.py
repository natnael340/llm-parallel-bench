import os
import sys
import time
import random
import hashlib
from typing import Tuple

from algo_parallel import SmithWatermanSequential, SmithWatermanParallel


def hash_matrix(H):
    m = hashlib.sha256()
    for row in H:
        m.update(bytes(row))
    return m.hexdigest()


def run_case(query: str, reference: str, scores: Tuple[int, int, int]):
    ms, mm, gs = scores
    seq = SmithWatermanSequential(ms, mm, gs)
    par = SmithWatermanParallel(ms, mm, gs)

    Hs = seq.constructMatrix(query, reference)
    Hp1 = par.constructMatrix(query, reference)
    Hp2 = par.constructMatrix(query, reference)

    assert Hs == Hp1, "Parallel matrix mismatch vs sequential"
    assert Hp1 == Hp2, "Parallel runs must be deterministic"

    seq_align = seq.findAlignment(query, reference)
    par_align = par.findAlignment(query, reference)

    assert seq_align == par_align, "Alignment outputs mismatch"

    return Hs, Hp1


def main():
    random.seed(123)
    # Edge cases
    cases = [
        ("", "", (2, -1, -2)),
        ("A", "", (2, -1, -2)),
        ("", "A", (2, -1, -2)),
        ("A", "A", (2, -1, -2)),
        ("G", "T", (2, -1, -2)),
    ]

    # Small
    small = [
        ("AC", "AG", (2, -1, -2)),
        ("ACG", "ACG", (2, -1, -2)),
        ("GATTACA", "GCATGCU", (2, -1, -2)),
    ]

    # Medium and Large random DNA strings
    def rand_dna(n):
        return ''.join(random.choice('ACGT') for _ in range(n))

    medium = [
        (rand_dna(64), rand_dna(64), (2, -1, -2)),
        (rand_dna(128), rand_dna(128), (2, -1, -2)),
    ]

    large = [
        (rand_dna(512), rand_dna(512), (2, -1, -2)),
    ]

    all_cases = cases + small + medium + large

    ok = 0
    for idx, (q, r, sc) in enumerate(all_cases):
        Hs, Hp = run_case(q, r, sc)
        ok += 1
    print(f"Correctness+determinism passed on {ok} cases")

    # Performance smoke test on large case
    q, r, sc = large[0]
    ms, mm, gs = sc
    seq = SmithWatermanSequential(ms, mm, gs)
    par = SmithWatermanParallel(ms, mm, gs)

    t0 = time.time(); seq.constructMatrix(q, r); t1 = time.time()
    t2 = time.time(); par.constructMatrix(q, r); t3 = time.time()

    dt_seq = t1 - t0
    dt_par = t3 - t2
    speedup = dt_seq / dt_par if dt_par > 0 else float('inf')

    print(f"Perf: N=512, seq={dt_seq:.4f}s, par={dt_par:.4f}s, speedup={speedup:.2f}x")


if __name__ == "__main__":
    main()
