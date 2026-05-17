#ifndef GEMM_PARALLEL_HPP
#define GEMM_PARALLEL_HPP

#include "gemm_common.hpp"

// Parallel GEMM: C := alpha * A * B + beta * C
Matrix gemm_parallel(const Matrix& A, const Matrix& B,
                     double alpha = 1.0,
                     Matrix* Cptr = nullptr,
                     double beta = 1.0,
                     int MB = defaultMB,
                     int NB = defaultNB,
                     int KB = defaultKB);

#endif // GEMM_PARALLEL_HPP
