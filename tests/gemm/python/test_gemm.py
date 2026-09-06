# test_gemm.py
import math
import copy
import random
import pytest
from tests import bench_utils
# The implementation under test is staged by bench/run.py (see
# bench/manifests/gemm/python.json); the adapter exposes the canonical entry.
from .staging.impl_adapter import bench_gemm as gemm

CONFIG = bench_utils.get_bench_config(default_reps=5, default_iters=5)

# Per-language sweep-tuned tile sizes (see analysis/data/gemm sweep CSVs).
TILES = {"MB": 32, "NB": 32, "KB": 128}


# ---------- helpers ----------

def make_matrix(rows, cols, fill=0.0):
    return [[float(fill) for _ in range(cols)] for _ in range(rows)]

def make_random_matrix(rows, cols, lo=-1.0, hi=1.0, seed=0):
    rng = random.Random(seed)
    return [[rng.uniform(lo, hi) for _ in range(cols)] for _ in range(rows)]

def mat_almost_equal(X, Y, tol=1e-9):
    assert len(X) == len(Y)
    assert len(X[0]) == len(Y[0])
    for i in range(len(X)):
        for j in range(len(X[0])):
            x, y = X[i][j], Y[i][j]
            if math.isnan(x) or math.isnan(y):
                assert math.isnan(x) and math.isnan(y)
            else:
                assert abs(x - y) <= tol

def naive_gemm(A, B, alpha=1.0, C=None, beta=0.0):
    """Reference: C := alpha*A*B + beta*C (no blocking, straightforward)."""
    m, k = len(A), len(A[0])
    k2, n = len(B), len(B[0])
    assert k == k2
    if C is None:
        C = make_matrix(m, n, 0.0)
    else:
        assert len(C) == m and len(C[0]) == n
        if beta != 1.0:
            for i in range(m):
                for j in range(n):
                    C[i][j] *= beta
    if alpha == 0.0:
        return C
    for i in range(m):
        for kk in range(k):
            a = alpha * A[i][kk]
            if a == 0.0:
                continue
            Bk = B[kk]
            Ci = C[i]
            for j in range(n):
                Ci[j] += a * Bk[j]
    return C

# ---------- tests ----------

def test_identity_left():
    m, n = 3, 4
    I = [[1.0 if i == j else 0.0 for j in range(m)] for i in range(m)]
    B = make_random_matrix(m, n, seed=1)
    out = gemm(I, B, alpha=1.0, C=None, beta=0.0)
    mat_almost_equal(out, B)

def test_identity_right():
    m, k = 3, 5
    n = k
    A = make_random_matrix(m, k, seed=2)
    I = [[1.0 if i == j else 0.0 for j in range(n)] for i in range(n)]
    out = gemm(A, I, alpha=1.0, C=None, beta=0.0)
    mat_almost_equal(out, A)

def test_zero_matrices_yield_zero():
    m, k, n = 4, 3, 5
    A = make_matrix(m, k, 0.0)
    B = make_matrix(k, n, 0.0)
    out = gemm(A, B, alpha=1.0, C=None, beta=0.0)
    mat_almost_equal(out, make_matrix(m, n, 0.0))

def test_alpha_zero_with_C_none():
    m, k, n = 2, 3, 4
    A = make_random_matrix(m, k, seed=3)
    B = make_random_matrix(k, n, seed=4)
    out = gemm(A, B, alpha=0.0, C=None, beta=0.0)
    mat_almost_equal(out, make_matrix(m, n, 0.0))

def test_alpha_zero_with_C_beta_one_preserves_C():
    m, k, n = 3, 3, 2
    A = make_random_matrix(m, k, seed=5)
    B = make_random_matrix(k, n, seed=6)
    C = make_random_matrix(m, n, seed=7)
    C_copy = copy.deepcopy(C)
    out = gemm(A, B, alpha=0.0, C=C, beta=1.0)
    assert out is C
    mat_almost_equal(out, C_copy)

def test_alpha_zero_with_C_beta_scales_once_even_with_small_KB():
    m, k, n = 3, 7, 4
    A = make_random_matrix(m, k, seed=8)
    B = make_random_matrix(k, n, seed=9)
    C = make_random_matrix(m, n, seed=10)
    C_copy = copy.deepcopy(C)
    beta = 2.5
    out = gemm(A, B, alpha=0.0, C=C, beta=beta, MB=2, NB=3, KB=1)  # many k-slabs
    assert out is C
    expected = [[beta * x for x in row] for row in C_copy]
    mat_almost_equal(out, expected)

def test_beta_zero_ignores_input_C():
    m, k, n = 4, 3, 5
    A = make_random_matrix(m, k, seed=11)
    B = make_random_matrix(k, n, seed=12)
    C = make_matrix(m, n, 7.0)
    out = gemm(A, B, alpha=1.0, C=C, beta=0.0)
    ref = naive_gemm(A, B, alpha=1.0, C=make_matrix(m, n, 0.0), beta=0.0)
    mat_almost_equal(out, ref)

def test_beta_one_accumulates_into_C():
    m, k, n = 3, 4, 2
    A = make_random_matrix(m, k, seed=13)
    B = make_random_matrix(k, n, seed=14)
    C = make_random_matrix(m, n, seed=15)
    Cref = copy.deepcopy(C)
    out = gemm(A, B, alpha=0.5, C=C, beta=1.0)
    ref = naive_gemm(A, B, alpha=0.5, C=Cref, beta=1.0)
    mat_almost_equal(out, ref)

def test_negative_alpha_and_beta():
    m, k, n = 2, 3, 2
    A = make_random_matrix(m, k, seed=16)
    B = make_random_matrix(k, n, seed=17)
    C = make_random_matrix(m, n, seed=18)
    Cref = copy.deepcopy(C)
    out = gemm(A, B, alpha=-1.0, C=C, beta=-0.5)
    ref = naive_gemm(A, B, alpha=-1.0, C=Cref, beta=-0.5)
    mat_almost_equal(out, ref)

def test_rectangular_tall_skinny():
    m, k, n = 10, 2, 7
    A = make_random_matrix(m, k, seed=19)
    B = make_random_matrix(k, n, seed=20)
    out = gemm(A, B)
    ref = naive_gemm(A, B)
    mat_almost_equal(out, ref)

def test_rectangular_short_fat():
    m, k, n = 3, 8, 20
    A = make_random_matrix(m, k, seed=21)
    B = make_random_matrix(k, n, seed=22)
    out = gemm(A, B, MB=2, NB=7, KB=3)
    ref = naive_gemm(A, B)
    mat_almost_equal(out, ref)

def test_single_row_times_single_column_scalar():
    m, k, n = 1, 5, 1
    A = make_random_matrix(m, k, seed=23)
    B = make_random_matrix(k, n, seed=24)
    out = gemm(A, B)
    ref = naive_gemm(A, B)
    mat_almost_equal(out, ref)

def test_row_vector_times_matrix():
    m, k, n = 1, 6, 4
    A = make_random_matrix(m, k, seed=25)
    B = make_random_matrix(k, n, seed=26)
    out = gemm(A, B, MB=1, NB=3, KB=2)
    ref = naive_gemm(A, B)
    mat_almost_equal(out, ref)

def test_matrix_times_column_vector():
    m, k, n = 7, 5, 1
    A = make_random_matrix(m, k, seed=27)
    B = make_random_matrix(k, n, seed=28)
    out = gemm(A, B, MB=4, NB=1, KB=3)
    ref = naive_gemm(A, B)
    mat_almost_equal(out, ref)

def test_general_random_compare_reference():
    m, k, n = 9, 11, 8
    A = make_random_matrix(m, k, seed=29)
    B = make_random_matrix(k, n, seed=30)
    C = make_random_matrix(m, n, seed=31)
    out = gemm(A, B, alpha=1.2, C=copy.deepcopy(C), beta=0.7, MB=4, NB=5, KB=3)
    ref = naive_gemm(A, B, alpha=1.2, C=C, beta=0.7)
    mat_almost_equal(out, ref)

def test_not_multiple_of_block_sizes():
    m, k, n = 13, 17, 19
    A = make_random_matrix(m, k, seed=32)
    B = make_random_matrix(k, n, seed=33)
    out = gemm(A, B, MB=5, NB=6, KB=7)
    ref = naive_gemm(A, B)
    mat_almost_equal(out, ref)

def test_block_sizes_one_matches_naive():
    m, k, n = 5, 6, 4
    A = make_random_matrix(m, k, seed=34)
    B = make_random_matrix(k, n, seed=35)
    out = gemm(A, B, MB=1, NB=1, KB=1)
    ref = naive_gemm(A, B)
    mat_almost_equal(out, ref)

def test_block_sizes_larger_than_dims():
    m, k, n = 4, 3, 2
    A = make_random_matrix(m, k, seed=36)
    B = make_random_matrix(k, n, seed=37)
    out = gemm(A, B, MB=128, NB=128, KB=128)
    ref = naive_gemm(A, B)
    mat_almost_equal(out, ref)

def test_in_place_C_object_identity():
    m, k, n = 3, 3, 3
    A = make_random_matrix(m, k, seed=38)
    B = make_random_matrix(k, n, seed=39)
    C = make_random_matrix(m, n, seed=40)
    out = gemm(A, B, alpha=0.3, C=C, beta=0.4)
    assert out is C  # mutated in place

def test_C_created_when_none():
    m, k, n = 2, 3, 2
    A = make_random_matrix(m, k, seed=41)
    B = make_random_matrix(k, n, seed=42)
    out = gemm(A, B)
    assert out is not A and out is not B
    assert len(out) == m and len(out[0]) == n

def test_dimension_mismatch_raises():
    A = make_random_matrix(3, 4, seed=43)
    B = make_random_matrix(5, 2, seed=44)  # k != k2
    with pytest.raises(ValueError):
        gemm(A, B)

def test_invalid_C_shape_raises():
    A = make_random_matrix(3, 2, seed=45)
    B = make_random_matrix(2, 4, seed=46)
    C = make_random_matrix(2, 4, seed=47)  # wrong m
    with pytest.raises(ValueError):
        gemm(A, B, C=C)

def test_ragged_A_rejected():
    A = [[1.0, 2.0], [3.0]]  # ragged
    B = make_random_matrix(2, 2, seed=48)
    with pytest.raises(ValueError):
        gemm(A, B)

def test_ragged_B_rejected():
    A = make_random_matrix(2, 2, seed=49)
    B = [[1.0], [2.0, 3.0]]  # ragged
    with pytest.raises(ValueError):
        gemm(A, B)

def test_non_numeric_entry_rejected():
    A = [[1.0, "x"], [3.0, 4.0]]
    B = make_random_matrix(2, 2, seed=50)
    with pytest.raises(ValueError):
        gemm(A, B)

def test_nan_propagation():
    m, k, n = 2, 2, 2
    A = [[float('nan'), 1.0], [2.0, 3.0]]
    B = [[4.0, 5.0], [6.0, 7.0]]
    out = gemm(A, B)
    assert math.isnan(out[0][0]) and math.isnan(out[0][1])

def test_infinity_propagation():
    m, k, n = 2, 2, 2
    A = [[float('inf'), 0.0], [0.0, 1.0]]
    B = [[1.0, 2.0], [3.0, 4.0]]
    out = gemm(A, B)
    assert math.isinf(out[0][0]) and math.isinf(out[0][1])

def test_repeat_calls_accumulate_with_beta_one():
    m, k, n = 3, 3, 3
    A = make_random_matrix(m, k, seed=51)
    B = make_random_matrix(k, n, seed=52)
    C = make_matrix(m, n, 0.0)
    gemm(A, B, alpha=1.0, C=C, beta=1.0)
    gemm(A, B, alpha=1.0, C=C, beta=1.0)
    ref_once = naive_gemm(A, B, alpha=1.0, C=make_matrix(m, n, 0.0), beta=1.0)
    ref_twice = naive_gemm(A, B, alpha=1.0, C=ref_once, beta=1.0)
    mat_almost_equal(C, ref_twice)

def test_alpha_scaling_linear():
    m, k, n = 4, 5, 3
    A = make_random_matrix(m, k, seed=53)
    B = make_random_matrix(k, n, seed=54)
    C1 = gemm(A, B, alpha=1.0, C=None, beta=0.0)
    s = 2.75
    C2 = gemm(A, B, alpha=s, C=None, beta=0.0)
    scaled = [[s * x for x in row] for row in C1]
    mat_almost_equal(C2, scaled)


@pytest.mark.perf
def test_gemm_performance_speed():
    m = k = n = 1024
    A = make_random_matrix(m, k, seed=10)
    B = make_random_matrix(k, n, seed=12)

    reps, iters = CONFIG["reps"], CONFIG["iters"]
    result = bench_utils.run_benchmark(
        lambda: gemm(A, B, alpha=1.0, C=None, beta=0, **TILES),
        reps=reps, iters=iters, warmup=1,
    )
    mean_s = result["mean"] / 1000.0
    gflops = (2.0 * m * n * k) / (mean_s * 1e9)
    label = f"GEMM {m}x{n}x{k} ({gflops:.3f} GFLOPs)  [iters={iters}, repeats={reps}]"
    print(bench_utils.format_result(label, result))
    bench_utils.write_result(
        result, algo="gemm", lang="python", impl=CONFIG["impl"], iters_per_rep=iters,
        params={"m": m, "n": n, "k": k, **TILES},
    )
