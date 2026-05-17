#ifndef GEMM_SEQ_HPP
#define GEMM_SEQ_HPP

#include "gemm_common.hpp"

// Sequential GEMM: C := alpha * A * B + beta * C
Matrix gemm(const Matrix& A, const Matrix& B,
            double alpha = 1.0,
            Matrix* Cptr = nullptr,
            double beta = 1.0,
            int MB = defaultMB,
            int NB = defaultNB,
            int KB = defaultKB);

#endif // GEMM_SEQ_HPP
