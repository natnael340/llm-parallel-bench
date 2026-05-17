// gemm_common.cpp - Common utility functions
#include <vector>
#include <stdexcept>
#include <string>
#include <algorithm>
#include "gemm_common.hpp"

// getSize returns (rows, cols) of a rectangular matrix.
std::pair<int,int> getSize(const Matrix& m) {
    if (m.empty()) return {0, 0};
    return {static_cast<int>(m.size()), static_cast<int>(m[0].size())};
}

// validateMatrix checks that the matrix is non-empty and rectangular.
void validateMatrix(const Matrix& m, const std::string& name) {
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
                name + " is ragged: row " + std::to_string(r) +
                " has " + std::to_string(m[r].size()) +
                " cols, expected " + std::to_string(cols));
        }
    }
}

// generateMatrix returns a rows x cols zero matrix.
Matrix generateMatrix(int rows, int cols) {
    return Matrix(rows, std::vector<double>(cols, 0.0));
}

// partialMatmul computes, for the provided packed blocks:
//   C[m0+i_off][n0+j_off] += alpha * sum_{k=0..kb-1} A[i_off][k] * B[j_off][k]
void partialMatmul(const Matrix& A, const Matrix& B, Matrix& C,
                   double alpha, int m0, int n0, int kb) {
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
Matrix transpose(const Matrix& m) {
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
Matrix packMatrix(const Matrix& matrix, int a0, int a1, int b0, int b1) {
    Matrix out;
    out.reserve(b1 - b0);
    for (int i = b0; i < b1; ++i) {
        const auto& row = matrix.at(i);
        out.emplace_back(row.begin() + a0, row.begin() + a1);
    }
    return out;
}
