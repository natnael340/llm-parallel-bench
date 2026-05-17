#ifndef GEMM_COMMON_HPP
#define GEMM_COMMON_HPP

#include <vector>
#include <string>
#include <utility>

using Matrix = std::vector<std::vector<double>>;

// Utility functions
std::pair<int,int> getSize(const Matrix& m);
void validateMatrix(const Matrix& m, const std::string& name);
Matrix generateMatrix(int rows, int cols);
Matrix transpose(const Matrix& m);
Matrix packMatrix(const Matrix& matrix, int a0, int a1, int b0, int b1);
void partialMatmul(const Matrix& A, const Matrix& B, Matrix& C,
                   double alpha, int m0, int n0, int kb);

// Default block sizes
constexpr int defaultMB = 64;
constexpr int defaultNB = 64;
constexpr int defaultKB = 64;

#endif // GEMM_COMMON_HPP
