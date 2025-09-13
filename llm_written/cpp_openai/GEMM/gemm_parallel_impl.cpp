#include <iostream>
#include <vector>
#include <stdexcept>
#include <string>
#include <algorithm>
#include <cstdint>
#include <omp.h>
#include "gemm_seq.hpp"

namespace par_internal {

// getSize returns (rows, cols) of a rectangular matrix.
static std::pair<int,int> getSize(const Matrix& m) {
    if (m.empty()) return {0, 0};
    return {static_cast<int>(m.size()), static_cast<int>(m[0].size())};
}

// validateMatrix checks that the matrix is non-empty and rectangular.
static void validateMatrix(const Matrix& m, const std::string& name) {
    if (m.empty()) {
        throw std::invalid_argument(name + " must have at least one row");
    }
    if (m[0].empty()) {
        throw std::invalid_argument(name + " must have at least one column");
    }
    const int cols = static_cast<int>(m[0].size());
    for (size_t r = 0; r < m.size(); ++r) {
        if (static_cast<int>(m[r].size()) != cols) {
            throw std::invalid_argument(
                name + " is ragged: row " + std::to_string(r) + " has " + std::to_string(m[r].size()) + " cols, expected " + std::to_string(cols));
        }
    }
}

// generateMatrix returns a rows x cols zero matrix.
static Matrix generateMatrix(int rows, int cols) {
    return Matrix(rows, std::vector<double>(cols, 0.0));
}

// partialMatmul computes, for the provided packed blocks:
// C[m0+i_off][n0+j_off] += alpha * sum_{k=0..kb-1} A[i_off][k] * B[j_off][k]
static void partialMatmul(const Matrix& A, const Matrix& B, Matrix& C, double alpha, int m0, int n0, int kb) {
    for (int iOff = 0; iOff < static_cast<int>(A.size()); ++iOff) {
        auto& Ci = C[m0 + iOff];
        const auto& Aik = A[iOff];
        for (int jOff = 0; jOff < static_cast<int>(B.size()); ++jOff) {
            const auto& Bjk = B[jOff];
            double s = 0.0;
            for (int k = 0; k < kb; ++k) {
                s += Aik[k] * Bjk[k];
            }
            Ci[n0 + jOff] += alpha * s;
        }
    }
}

// transpose returns the transpose of a rectangular matrix.
static Matrix transpose(const Matrix& m) {
    auto [r, c] = getSize(m);
    Matrix out(c, std::vector<double>(r));
    for (int j = 0; j < c; ++j) {
        for (int i = 0; i < r; ++i) {
            out[j][i] = m[i][j];
        }
    }
    return out;
}

// packMatrix returns a submatrix copy: rows in [b0, b1), cols in [a0, a1).
static Matrix packMatrix(const Matrix& matrix, int a0, int a1, int b0, int b1) {
    Matrix out;
    out.reserve(b1 - b0);
    for (int i = b0; i < b1; ++i) {
        const auto& row = matrix.at(i);
        out.emplace_back(row.begin() + a0, row.begin() + a1);
    }
    return out;
}

// A purely sequential internal kernel identical to the baseline ordering.
static void gemm_seq_kernel(const Matrix& A, const Matrix& B, double alpha, Matrix& C, double beta, int MB, int NB, int KB) {
    auto [m, k] = getSize(A);
    auto [k2, n] = getSize(B);

    if (beta != 1.0) {
        for (int i = 0; i < m; ++i) {
            auto& row = C[i];
            for (int j = 0; j < n; ++j) row[j] *= beta;
        }
    }
    if (alpha == 0.0) return;

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
}

} // namespace par_internal

// Gemm computes C := alpha * A * B + beta * C.
Matrix gemm(const Matrix& A, const Matrix& B, double alpha, Matrix* Cptr, double beta, int MB, int NB, int KB ) {
    using namespace par_internal;
    // validateMatrix(A, "A");
    // validateMatrix(B, "B");

    auto [m, k] = getSize(A);
    auto [k2, n] = getSize(B);
    if (k != k2) {
        throw std::invalid_argument(
            "shape mismatch: A is (" + std::to_string(m) + "," + std::to_string(k) + "), B is (" + std::to_string(k2) + "," + std::to_string(n) + ")");
    }

    if (MB == 0) MB = 64;
    if (NB == 0) NB = 64;
    if (KB == 0) KB = 64;

    Matrix localC;
    Matrix& C = (Cptr ? *Cptr : (localC = generateMatrix(m, n)));

    if (Cptr) {
        // validateMatrix(C, "C");
        auto [m2, n2] = getSize(C);
        if (m2 != m || n2 != n) {
            throw std::invalid_argument(
                "C has shape (" + std::to_string(m2) + "," + std::to_string(n2) + "); expected (" + std::to_string(m) + "," + std::to_string(n) + ")");
        }
    }

    long long total_ops = static_cast<long long>(m) * static_cast<long long>(n) * static_cast<long long>(k);
    const long long SEQ_THRESHOLD = 200000; // ~2e5 MACs
    if (total_ops <= SEQ_THRESHOLD) {
        gemm_seq_kernel(A, B, alpha, C, Cptr ? beta : 1.0, MB, NB, KB);
        return C;
    }

    if (Cptr) {
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
            Matrix Bpack = packMatrix(Bt, k0, k1, n0, n1); // (nChunk x kChunk)

            int mBlocks = (m + MB - 1) / MB;
            int threads = std::min(omp_get_max_threads(), std::max(1, mBlocks));
            #pragma omp parallel for schedule(static) num_threads(threads)
            for (int m0 = 0; m0 < m; m0 += MB) {
                int m1 = std::min(m0 + MB, m);
                Matrix Apack = packMatrix(A, k0, k1, m0, m1); // (mChunk x kChunk)
                int kb = k1 - k0;
                partialMatmul(Apack, Bpack, C, alpha, m0, n0, kb);
            }
        }
    }

    return C;
}
