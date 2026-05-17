// gemm_tests.cpp
#include <cmath>
#include <cstdint>
#include <exception>
#include <functional>
#include <iostream>
#include <random>
#include <string>
#include <utility>
#include <vector>
#include <chrono>

// Include your implementation (adjust path/name as needed)
#include "../../GEMM/cpp/gemm_seq.hpp"  // or: #include "gemm.hpp"

using Matrix = std::vector<std::vector<double>>;

// ---------- helpers ----------
static Matrix makeMatrix(int rows, int cols, double fill = 0.0) {
    return Matrix(rows, std::vector<double>(cols, fill));
}

static Matrix makeRandomMatrix(int rows, int cols, double lo, double hi, uint64_t seed) {
    std::mt19937_64 rng(seed);
    std::uniform_real_distribution<double> dist(lo, hi);
    Matrix m(rows, std::vector<double>(cols));
    for (int i = 0; i < rows; ++i)
        for (int j = 0; j < cols; ++j)
            m[i][j] = dist(rng);
    return m;
}

static Matrix copyMatrix(const Matrix& X) { return X; }

static void matAlmostEqual(const Matrix& X, const Matrix& Y, double tol = 1e-9) {
    if (X.size() != Y.size() || X[0].size() != Y[0].size())
        throw std::runtime_error("matAlmostEqual: dimension mismatch");
    for (size_t i = 0; i < X.size(); ++i) {
        for (size_t j = 0; j < X[0].size(); ++j) {
            double x = X[i][j], y = Y[i][j];
            if (std::isnan(x) || std::isnan(y)) {
                if (!(std::isnan(x) && std::isnan(y)))
                    throw std::runtime_error("NaN mismatch at (" + std::to_string(i) + "," + std::to_string(j) + ")");
            } else {
                if (std::abs(x - y) > tol) {
                    throw std::runtime_error("diff at (" + std::to_string(i) + "," + std::to_string(j) +
                                             "): " + std::to_string(x) + " vs " + std::to_string(y));
                }
            }
        }
    }
}

// Reference: C := alpha*A*B + beta*C (no blocking).
static Matrix naiveGemm(const Matrix& A, const Matrix& B, double alpha = 1.0, Matrix C = {}, double beta = 0.0) {
    int m = (int)A.size(), k = (int)A[0].size();
    int k2 = (int)B.size(), n = (int)B[0].size();
    if (k != k2) throw std::runtime_error("naiveGemm: shape mismatch");
    if (C.empty()) {
        C = makeMatrix(m, n, 0.0);
    } else {
        if ((int)C.size() != m || (int)C[0].size() != n)
            throw std::runtime_error("naiveGemm: C shape mismatch");
        if (beta != 1.0) {
            for (int i = 0; i < m; ++i)
                for (int j = 0; j < n; ++j)
                    C[i][j] *= beta;
        }
    }
    if (alpha == 0.0) return C;
    for (int i = 0; i < m; ++i) {
        for (int kk = 0; kk < k; ++kk) {
            double a = alpha * A[i][kk];
            if (a == 0.0) continue;
            const auto& Bk = B[kk];
            auto& Ci = C[i];
            for (int j = 0; j < n; ++j) Ci[j] += a * Bk[j];
        }
    }
    return C;
}

// --- tiny testing harness ---
static int passed = 0, failed = 0;

static void RUN(const std::string& name, const std::function<void()>& fn) {
    try {
        fn();
        ++passed;
        std::cout << "[PASS] " << name << "\n";
    } catch (const std::exception& e) {
        ++failed;
        std::cout << "[FAIL] " << name << " -> " << e.what() << "\n";
    } catch (...) {
        ++failed;
        std::cout << "[FAIL] " << name << " -> unknown exception\n";
    }
}

// ---------- tests ----------

static void test_identity_left() {
    int m = 3, n = 4;
    Matrix I(m, std::vector<double>(m, 0.0));
    for (int i = 0; i < m; ++i) I[i][i] = 1.0;
    Matrix B = makeRandomMatrix(m, n, -1.0, 1.0, 1);
    Matrix out = gemm(I, B, 1.0, nullptr, 0.0);
    matAlmostEqual(out, B);
}

static void test_identity_right() {
    int m = 3, k = 5, n = k;
    Matrix A = makeRandomMatrix(m, k, -1.0, 1.0, 2);
    Matrix I(n, std::vector<double>(n, 0.0));
    for (int i = 0; i < n; ++i) I[i][i] = 1.0;
    Matrix out = gemm(A, I, 1.0, nullptr, 0.0);
    matAlmostEqual(out, A);
}

static void test_zero_matrices_yield_zero() {
    int m = 4, k = 3, n = 5;
    Matrix A = makeMatrix(m, k, 0.0);
    Matrix B = makeMatrix(k, n, 0.0);
    Matrix out = gemm(A, B, 1.0, nullptr, 0.0);
    matAlmostEqual(out, makeMatrix(m, n, 0.0));
}

static void test_alpha_zero_with_C_none() {
    int m = 2, k = 3, n = 4;
    Matrix A = makeRandomMatrix(m, k, -1, 1, 3);
    Matrix B = makeRandomMatrix(k, n, -1, 1, 4);
    Matrix out = gemm(A, B, 0.0, nullptr, 0.0);
    matAlmostEqual(out, makeMatrix(m, n, 0.0));
}

static void test_alpha_zero_with_C_beta_one_preserves_C() {
    int m = 3, k = 3, n = 2;
    Matrix A = makeRandomMatrix(m, k, -1, 1, 5);
    Matrix B = makeRandomMatrix(k, n, -1, 1, 6);
    Matrix C = makeRandomMatrix(m, n, -1, 1, 7);
    Matrix Ccopy = copyMatrix(C);
    (void)gemm(A, B, 0.0, &C, 1.0);
    matAlmostEqual(C, Ccopy);
}

static void test_alpha_zero_with_C_beta_scales_once_even_with_small_KB() {
    int m = 3, k = 7, n = 4;
    Matrix A = makeRandomMatrix(m, k, -1, 1, 8);
    Matrix B = makeRandomMatrix(k, n, -1, 1, 9);
    Matrix C = makeRandomMatrix(m, n, -1, 1, 10);
    Matrix Ccopy = copyMatrix(C);
    double beta = 2.5;
    (void)gemm(A, B, 0.0, &C, beta, /*MB=*/2, /*NB=*/3, /*KB=*/1);
    Matrix expected = Ccopy;
    for (int i = 0; i < m; ++i) for (int j = 0; j < n; ++j) expected[i][j] *= beta;
    matAlmostEqual(C, expected);
}

static void test_beta_zero_ignores_input_C() {
    int m = 4, k = 3, n = 5;
    Matrix A = makeRandomMatrix(m, k, -1, 1, 11);
    Matrix B = makeRandomMatrix(k, n, -1, 1, 12);
    Matrix C = makeMatrix(m, n, 7.0);
    Matrix out = gemm(A, B, 1.0, &C, 0.0);
    Matrix ref = naiveGemm(A, B, 1.0, makeMatrix(m, n, 0.0), 0.0);
    matAlmostEqual(out, ref);
}

static void test_beta_one_accumulates_into_C() {
    int m = 3, k = 4, n = 2;
    Matrix A = makeRandomMatrix(m, k, -1, 1, 13);
    Matrix B = makeRandomMatrix(k, n, -1, 1, 14);
    Matrix C = makeRandomMatrix(m, n, -1, 1, 15);
    Matrix Cref = copyMatrix(C);
    Matrix out = gemm(A, B, 0.5, &C, 1.0);
    Matrix ref = naiveGemm(A, B, 0.5, Cref, 1.0);
    matAlmostEqual(out, ref);
}

static void test_negative_alpha_and_beta() {
    int m = 2, k = 3, n = 2;
    Matrix A = makeRandomMatrix(m, k, -1, 1, 16);
    Matrix B = makeRandomMatrix(k, n, -1, 1, 17);
    Matrix C = makeRandomMatrix(m, n, -1, 1, 18);
    Matrix Cref = copyMatrix(C);
    Matrix out = gemm(A, B, -1.0, &C, -0.5);
    Matrix ref = naiveGemm(A, B, -1.0, Cref, -0.5);
    matAlmostEqual(out, ref);
}

static void test_rectangular_tall_skinny() {
    int m = 10, k = 2, n = 7;
    Matrix A = makeRandomMatrix(m, k, -1, 1, 19);
    Matrix B = makeRandomMatrix(k, n, -1, 1, 20);
    Matrix out = gemm(A, B);
    Matrix ref = naiveGemm(A, B);
    matAlmostEqual(out, ref);
}

static void test_rectangular_short_fat() {
    int m = 3, k = 8, n = 20;
    Matrix A = makeRandomMatrix(m, k, -1, 1, 21);
    Matrix B = makeRandomMatrix(k, n, -1, 1, 22);
    Matrix out = gemm(A, B, 1.0, nullptr, 0.0, 2, 7, 3);
    Matrix ref = naiveGemm(A, B);
    matAlmostEqual(out, ref);
}

static void test_single_row_times_single_column_scalar() {
    int m = 1, k = 5, n = 1;
    Matrix A = makeRandomMatrix(m, k, -1, 1, 23);
    Matrix B = makeRandomMatrix(k, n, -1, 1, 24);
    Matrix out = gemm(A, B);
    Matrix ref = naiveGemm(A, B);
    matAlmostEqual(out, ref);
}

static void test_row_vector_times_matrix() {
    int m = 1, k = 6, n = 4;
    Matrix A = makeRandomMatrix(m, k, -1, 1, 25);
    Matrix B = makeRandomMatrix(k, n, -1, 1, 26);
    Matrix out = gemm(A, B, 1.0, nullptr, 0.0, 1, 3, 2);
    Matrix ref = naiveGemm(A, B);
    matAlmostEqual(out, ref);
}

static void test_matrix_times_column_vector() {
    int m = 7, k = 5, n = 1;
    Matrix A = makeRandomMatrix(m, k, -1, 1, 27);
    Matrix B = makeRandomMatrix(k, n, -1, 1, 28);
    Matrix out = gemm(A, B, 1.0, nullptr, 0.0, 4, 1, 3);
    Matrix ref = naiveGemm(A, B);
    matAlmostEqual(out, ref);
}

static void test_general_random_compare_reference() {
    int m = 9, k = 11, n = 8;
    Matrix A = makeRandomMatrix(m, k, -1, 1, 29);
    Matrix B = makeRandomMatrix(k, n, -1, 1, 30);
    Matrix C = makeRandomMatrix(m, n, -1, 1, 31);
    Matrix Cdeep = copyMatrix(C);
    Matrix out = gemm(A, B, 1.2, &Cdeep, 0.7, 4, 5, 3);
    Matrix ref = naiveGemm(A, B, 1.2, C, 0.7);
    matAlmostEqual(out, ref);
}

static void test_not_multiple_of_block_sizes() {
    int m = 13, k = 17, n = 19;
    Matrix A = makeRandomMatrix(m, k, -1, 1, 32);
    Matrix B = makeRandomMatrix(k, n, -1, 1, 33);
    Matrix out = gemm(A, B, 1.0, nullptr, 0.0, 5, 6, 7);
    Matrix ref = naiveGemm(A, B);
    matAlmostEqual(out, ref);
}

static void test_block_sizes_one_matches_naive() {
    int m = 5, k = 6, n = 4;
    Matrix A = makeRandomMatrix(m, k, -1, 1, 34);
    Matrix B = makeRandomMatrix(k, n, -1, 1, 35);
    Matrix out = gemm(A, B, 1.0, nullptr, 0.0, 1, 1, 1);
    Matrix ref = naiveGemm(A, B);
    matAlmostEqual(out, ref);
}

static void test_block_sizes_larger_than_dims() {
    int m = 4, k = 3, n = 2;
    Matrix A = makeRandomMatrix(m, k, -1, 1, 36);
    Matrix B = makeRandomMatrix(k, n, -1, 1, 37);
    Matrix out = gemm(A, B, 1.0, nullptr, 0.0, 128, 128, 128);
    Matrix ref = naiveGemm(A, B);
    matAlmostEqual(out, ref);
}

static void test_in_place_C_mutation() {  // adapted from identity check
    int m = 3, k = 3, n = 3;
    Matrix A = makeRandomMatrix(m, k, -1, 1, 38);
    Matrix B = makeRandomMatrix(k, n, -1, 1, 39);
    Matrix C = makeRandomMatrix(m, n, -1, 1, 40);
    Matrix Ccopy = copyMatrix(C);
    Matrix out = gemm(A, B, 0.3, &C, 0.4);
    (void)out; // return is a copy in C++; verify C mutated correctly:
    Matrix ref = naiveGemm(A, B, 0.3, Ccopy, 0.4);
    matAlmostEqual(C, ref);
}

static void test_C_created_when_null() {
    int m = 2, k = 3, n = 2;
    Matrix A = makeRandomMatrix(m, k, -1, 1, 41);
    Matrix B = makeRandomMatrix(k, n, -1, 1, 42);
    Matrix out = gemm(A, B);
    if ((int)out.size() != m || (int)out[0].size() != n)
        throw std::runtime_error("unexpected out shape");
}

static void test_dimension_mismatch_raises() {
    Matrix A = makeRandomMatrix(3, 4, -1, 1, 43);
    Matrix B = makeRandomMatrix(5, 2, -1, 1, 44);
    bool threw = false;
    try { (void)gemm(A, B); } catch (...) { threw = true; }
    if (!threw) throw std::runtime_error("expected exception for dim mismatch");
}

static void test_invalid_C_shape_raises() {
    Matrix A = makeRandomMatrix(3, 2, -1, 1, 45);
    Matrix B = makeRandomMatrix(2, 4, -1, 1, 46);
    Matrix C = makeRandomMatrix(2, 4, -1, 1, 47); // wrong m vs A*B (should be 3x4)
    bool threw = false;
    try { (void)gemm(A, B, 1.0, &C, 0.0); } catch (...) { threw = true; }
    if (!threw) throw std::runtime_error("expected exception for invalid C shape");
}

static void test_ragged_A_rejected() {
    Matrix A = { {1.0, 2.0}, {3.0} }; // ragged
    Matrix B = makeRandomMatrix(2, 2, -1, 1, 48);
    bool threw = false;
    try { (void)gemm(A, B); } catch (...) { threw = true; }
    if (!threw) throw std::runtime_error("expected exception for ragged A");
}

static void test_ragged_B_rejected() {
    Matrix A = makeRandomMatrix(2, 2, -1, 1, 49);
    Matrix B = { {1.0}, {2.0, 3.0} }; // ragged
    bool threw = false;
    try { (void)gemm(A, B); } catch (...) { threw = true; }
    if (!threw) throw std::runtime_error("expected exception for ragged B");
}

static void test_nan_propagation() {
    Matrix A = { {std::numeric_limits<double>::quiet_NaN(), 1.0}, {2.0, 3.0} };
    Matrix B = { {4.0, 5.0}, {6.0, 7.0} };
    Matrix out = gemm(A, B);
    if (!(std::isnan(out[0][0]) && std::isnan(out[0][1])))
        throw std::runtime_error("expected NaN propagation in first row");
}

static void test_infinity_propagation() {
    Matrix A = { {std::numeric_limits<double>::infinity(), 0.0}, {0.0, 1.0} };
    Matrix B = { {1.0, 2.0}, {3.0, 4.0} };
    Matrix out = gemm(A, B);
    if (!(std::isinf(out[0][0]) && std::isinf(out[0][1])))
        throw std::runtime_error("expected Inf propagation in first row");
}

// Optional heavy perf test: compile with -DRUN_PERF to enable.
static void test_gemm_performance_speed() {
    int m = 1024, k = 1024, n = 1024;
    Matrix A = makeRandomMatrix(m, k, -1, 1, 10);
    Matrix B = makeRandomMatrix(k, n, -1, 1, 12);

    // warmup
    (void)gemm(A, B, 1.0, nullptr, 0.0, 32, 32, 16);

    const int iters = 20;
    const int reps = 5;
    std::vector<double> per_run_ms;

    for(int i = 0; i < reps; i++){
        auto t0 = std::chrono::high_resolution_clock::now();
        for(int j =0; j<iters; j++){
            (void)gemm(A, B, 1.0, nullptr, 0.0, 32, 32, 16);
        }
        auto t1 = std::chrono::high_resolution_clock::now();
        double total_ns = std::chrono::duration_cast<std::chrono::nanoseconds>(t1 - t0).count();
        per_run_ms.push_back((total_ns / 1e6) / double(iters));
    }
    
    double mean = 0.0;
    for (double val : per_run_ms) mean+=val;
    mean /= double(reps);

    double sumsq = 0.0;
    for (double val : per_run_ms) {
        double d = val - mean;
        sumsq += d*d;
    }
    double sd = std::sqrt(sumsq / double(reps));

    double means = mean / 1000.0;
    double gflops = (2.0 * double(m) * double(n) * (double)k) / (means * 1e9);
    //GEMM %dx%dx%d: %.2f ms/run ± %.2f (%.3f GFLOPs) [iters=%d, repeats=%d]",m, k, n, mean, sd, gflops, iters, reps)
    std::cout << "GEMM "<<m<<"x"<<n<<"x"<<k<<": "<< std::fixed <<mean << "ms/run ± " 
    << std::fixed <<sd<<" ("<< std::fixed<< gflops << " GFLOPs) [iters="<<iters<<", repeats="<<reps<<"]";
}

int main() {
    RUN("identity_left", test_identity_left);
    RUN("identity_right", test_identity_right);
    RUN("zero_matrices_yield_zero", test_zero_matrices_yield_zero);
    RUN("alpha_zero_with_C_none", test_alpha_zero_with_C_none);
    RUN("alpha_zero_with_C_beta_one_preserves_C", test_alpha_zero_with_C_beta_one_preserves_C);
    RUN("alpha_zero_with_C_beta_scales_once_even_with_small_KB", test_alpha_zero_with_C_beta_scales_once_even_with_small_KB);
    RUN("beta_zero_ignores_input_C", test_beta_zero_ignores_input_C);
    RUN("beta_one_accumulates_into_C", test_beta_one_accumulates_into_C);
    RUN("negative_alpha_and_beta", test_negative_alpha_and_beta);
    RUN("rectangular_tall_skinny", test_rectangular_tall_skinny);
    RUN("rectangular_short_fat", test_rectangular_short_fat);
    RUN("single_row_times_single_column_scalar", test_single_row_times_single_column_scalar);
    RUN("row_vector_times_matrix", test_row_vector_times_matrix);
    RUN("matrix_times_column_vector", test_matrix_times_column_vector);
    RUN("general_random_compare_reference", test_general_random_compare_reference);
    RUN("not_multiple_of_block_sizes", test_not_multiple_of_block_sizes);
    RUN("block_sizes_one_matches_naive", test_block_sizes_one_matches_naive);
    RUN("block_sizes_larger_than_dims", test_block_sizes_larger_than_dims);
    RUN("in_place_C_mutation", test_in_place_C_mutation);
    RUN("C_created_when_null", test_C_created_when_null);
    RUN("dimension_mismatch_raises", test_dimension_mismatch_raises);
    RUN("invalid_C_shape_raises", test_invalid_C_shape_raises);
    RUN("ragged_A_rejected", test_ragged_A_rejected);
    RUN("ragged_B_rejected", test_ragged_B_rejected);
    RUN("nan_propagation", test_nan_propagation);
    RUN("infinity_propagation", test_infinity_propagation);
    RUN("speed_tesT", test_gemm_performance_speed);

    std::cout << "\n=== SUMMARY ===\n"
              << "Passed: " << passed << "\n"
              << "Failed: " << failed << "\n";
    return failed == 0 ? 0 : 1;
}