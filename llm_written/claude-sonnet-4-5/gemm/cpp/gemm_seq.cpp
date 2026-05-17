// gemm_seq.cpp - Sequential baseline implementation
#include <iostream>
#include <vector>
#include <stdexcept>
#include <string>
#include <algorithm>
#include "gemm_seq.hpp"

// Gemm computes C := alpha * A * B + beta * C.
// A is (m x k), B is (k x n), C is (m x n).
// If Cptr == nullptr, a fresh matrix is created and returned.
// If MB/NB/KB are 0, sensible defaults are used.
Matrix gemm(const Matrix& A, const Matrix& B,
            double alpha,
            Matrix* Cptr,
            double beta,
            int MB, int NB, int KB
) {
    validateMatrix(A, "A");
    validateMatrix(B, "B");

    auto [m, k] = getSize(A);
    auto [k2, n] = getSize(B);
    if (k != k2) {
        throw std::invalid_argument(
            "shape mismatch: A is (" + std::to_string(m) + "," + std::to_string(k) +
            "), B is (" + std::to_string(k2) + "," + std::to_string(n) + ")");
    }

    Matrix localC;
    Matrix& C = (Cptr ? *Cptr : (localC = generateMatrix(m, n)));

    if (Cptr) {
        validateMatrix(C, "C");
        auto [m2, n2] = getSize(C);
        if (m2 != m || n2 != n) {
            throw std::invalid_argument(
                "C has shape (" + std::to_string(m2) + "," + std::to_string(n2) +
                "); expected (" + std::to_string(m) + "," + std::to_string(n) + ")");
        }
        if (beta != 1.0) {
            for (int i = 0; i < m; ++i) {
                auto& row = C[i];
                for (int j = 0; j < n; ++j) row[j] *= beta;
            }
        }
    }

    if (alpha == 0.0) {
        return C;
    }

    Matrix Bt = transpose(B);

    for (int n0 = 0; n0 < n; n0 += NB) {
        int n1 = std::min(n0 + NB, n);
        for (int k0 = 0; k0 < k; k0 += KB) {
            int k1 = std::min(k0 + KB, k);
            Matrix Bpack = packMatrix(Bt, k0, k1, n0, n1);

            for (int m0 = 0; m0 < m; m0 += MB) {
                int m1 = std::min(m0 + MB, m);
                Matrix Apack = packMatrix(A, k0, k1, m0, m1);

                int kb = k1 - k0;
                partialMatmul(Apack, Bpack, C, alpha, m0, n0, kb);
            }
        }
    }

    return C;
}
