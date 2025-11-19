#ifndef GEMM_PARALLEL_HPP
#define GEMM_PARALLEL_HPP

#include <vector>

using Matrix = std::vector<std::vector<double>>;

Matrix gemm(const Matrix& A, const Matrix& B,
            double alpha = 1.0,
            Matrix* Cptr = nullptr,
            double beta = 0.0,
            int MB = 0, int NB = 0, int KB = 0);

#endif // GEMM_PARALLEL_HPP
