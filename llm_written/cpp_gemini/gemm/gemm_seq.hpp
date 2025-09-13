#ifndef GEMM_SEQ_HPP
#define GEMM_SEQ_HPP

#include <vector>

using Matrix = std::vector<std::vector<double>>;

Matrix gemm_seq(const Matrix& A, const Matrix& B,
                double alpha,
                Matrix* Cptr,
                double beta,
                int MB = 0, int NB = 0, int KB = 0);

#endif // GEMM_SEQ_HPP
