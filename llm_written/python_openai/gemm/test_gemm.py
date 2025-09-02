import random
from typing import List

from gemm_seq import gemm as gemm_seq
from gemm_parallel import gemm as gemm_par


def equal_matrix(A: List[List[float]], B: List[List[float]]):
    if len(A) != len(B) or len(A[0]) != len(B[0]):
        return False
    for i in range(len(A)):
        for j in range(len(A[0])):
            if A[i][j] != B[i][j]:
                return False
    return True


def rand_matrix(r, c, rng):
    return [[rng.uniform(-5, 5) for _ in range(c)] for _ in range(r)]


def test_small_and_edge():
    rng = random.Random(0)
    # Small edge sizes, these use the sequential fast path in parallel impl
    sizes = [(1,1,1), (1,3,2), (2,1,3), (3,3,1), (2,3,4), (4,3,2)]
    tiles = [(1,1,1), (2,2,2), (4,4,4)]
    for (m,k,n) in sizes:
        A = rand_matrix(m,k,rng)
        B = rand_matrix(k,n,rng)
        for MB,NB,KB in tiles:
            for alpha in [0.0, 1.0, -0.5]:
                for beta in [0.0, 1.0, 0.25]:
                    C0 = rand_matrix(m,n,rng)
                    C1 = [row[:] for row in C0]
                    C2 = [row[:] for row in C0]
                    ref = gemm_seq(A,B,alpha=alpha,C=C1,beta=beta,MB=MB,NB=NB,KB=KB)
                    out = gemm_par(A,B,alpha=alpha,C=C2,beta=beta,MB=MB,NB=NB,KB=KB)
                    assert equal_matrix(ref,out)


def test_parallel_and_determinism():
    rng = random.Random(42)
    # Medium size to exercise process pool path
    m,k,n = 48,48,48
    MB,NB,KB = 16,16,16
    A = rand_matrix(m,k,rng)
    B = rand_matrix(k,n,rng)
    Cinit = rand_matrix(m,n,rng)

    C1 = [row[:] for row in Cinit]
    C2 = [row[:] for row in Cinit]
    ref = gemm_seq(A,B,alpha=1.0,C=C1,beta=0.5,MB=MB,NB=NB,KB=KB)
    out1 = gemm_par(A,B,alpha=1.0,C=C2,beta=0.5,MB=MB,NB=NB,KB=KB)
    assert equal_matrix(ref,out1)

    C3 = [row[:] for row in Cinit]
    out2 = gemm_par(A,B,alpha=1.0,C=C3,beta=0.5,MB=MB,NB=NB,KB=KB)
    assert equal_matrix(out1,out2)


def run_all():
    test_small_and_edge()
    test_parallel_and_determinism()
    print("All tests passed")


if __name__ == "__main__":
    run_all()
