#include <iostream>
#include <vector>
#include <random>
#include <cmath>
#include <cassert>
#include <string>
#include <iomanip>
#include <stdexcept>

#include "gemm_seq.hpp"
#include "gemm_parallel.hpp"

// Helper to generate a random matrix
Matrix createRandomMatrix(int rows, int cols, std::mt19937& gen) {
    if (rows == 0 || cols == 0) {
        return Matrix();
    }
    std::uniform_real_distribution<> dis(-1.0, 1.0);
    Matrix m(rows, std::vector<double>(cols));
    for (int i = 0; i < rows; ++i) {
        for (int j = 0; j < cols; ++j) {
            m[i][j] = dis(gen);
        }
    }
    return m;
}

// Helper to compare matrices
bool areMatricesEqual(const Matrix& a, const Matrix& b, double tol = 1e-9) {
    if (a.empty() && b.empty()) return true;
    if (a.size() != b.size()) {
        std::cerr << "Matrix row counts differ: " << a.size() << " vs " << b.size() << std::endl;
        return false;
    }
    if (a.empty() || b.empty()) return false; // One is empty, the other is not
    if (a[0].size() != b[0].size()) {
        std::cerr << "Matrix column counts differ: " << a[0].size() << " vs " << b[0].size() << std::endl;
        return false;
    }

    for (size_t i = 0; i < a.size(); ++i) {
        for (size_t j = 0; j < a[i].size(); ++j) {
            if (std::abs(a[i][j] - b[i][j]) > tol) {
                std::cerr << std::fixed << std::setprecision(12)
                          << "Mismatch at (" << i << "," << j << "): "
                          << a[i][j] << " (seq) vs " << b[i][j] << " (par)" << std::endl;
                return false;
            }
        }
    }
    return true;
}

void printTestHeader(const std::string& name) {
    std::cout << "--- " << name << " ---" << std::endl;
}

void runTest(const std::string& name, int m, int k, int n, double alpha, double beta, int seed) {
    printTestHeader(name);
    std::mt19937 gen(seed);

    Matrix A = createRandomMatrix(m, k, gen);
    Matrix B = createRandomMatrix(k, n, gen);
    Matrix C_seq_base = createRandomMatrix(m, n, gen);
    Matrix C_par_base = C_seq_base; // Identical starting C

    // Test with Cptr != nullptr
    Matrix C_seq = C_seq_base;
    Matrix C_par = C_par_base;
    gemm_seq(A, B, alpha, &C_seq, beta);
    gemm(A, B, alpha, &C_par, beta);

    assert(areMatricesEqual(C_seq, C_par));
    std::cout << "Test '" << name << "' (Cptr provided) PASSED" << std::endl;

    // Test with Cptr == nullptr
    Matrix C_seq_null = gemm_seq(A, B, alpha, nullptr, beta);
    Matrix C_par_null = gemm(A, B, alpha, nullptr, beta);

    assert(areMatricesEqual(C_seq_null, C_par_null));
    std::cout << "Test '" << name << "' (Cptr null) PASSED" << std::endl;
}

int main() {
    try {
        // Small cases (below or near threshold)
        runTest("Scalar 1x1", 1, 1, 1, 1.0, 1.0, 1);
        runTest("Small 10x10", 10, 10, 10, 1.0, 0.0, 42);
        runTest("Rectangular 20x5x15", 20, 5, 15, 1.5, 1.0, 43);

        // Larger cases (above threshold to trigger parallelism)
        runTest("Typical 250x250", 250, 250, 250, 1.0, 1.0, 44);
        runTest("Rectangular large 512x128x256", 512, 128, 256, 0.5, 0.5, 45);
        runTest("Uneven dimensions 199x301x255", 199, 301, 255, 1.0, 1.0, 46);

        // Edge cases for parameters
        runTest("Alpha is zero", 128, 128, 128, 0.0, 1.5, 47);
        runTest("Beta is zero", 128, 128, 128, 1.5, 0.0, 48);
        runTest("Beta is one", 128, 128, 128, 1.5, 1.0, 49);

        // Test with non-default block sizes
        printTestHeader("Custom Block Sizes");
        std::mt19937 gen(50);
        Matrix A_custom = createRandomMatrix(200, 200, gen);
        Matrix B_custom = createRandomMatrix(200, 200, gen);
        Matrix C_seq_custom = gemm_seq(A_custom, B_custom, 1.0, nullptr, 0.0, 32, 32, 32);
        Matrix C_par_custom = gemm(A_custom, B_custom, 1.0, nullptr, 0.0, 32, 32, 32);
        assert(areMatricesEqual(C_seq_custom, C_par_custom));
        std::cout << "Test 'Custom Block Sizes' PASSED" << std::endl;

        std::cout << "\nAll tests passed successfully!" << std::endl;
    } catch (const std::exception& e) {
        std::cerr << "An assertion failed or an exception occurred: " << e.what() << std::endl;
        return 1;
    }

    return 0;
}
