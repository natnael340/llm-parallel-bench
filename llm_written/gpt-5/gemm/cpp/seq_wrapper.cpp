#include "gemm_seq.hpp"

// Forward declaration from the sequential implementation TU
Matrix gemm(const Matrix& A, const Matrix& B, double alpha, Matrix* Cptr, double beta, int MB, int NB, int KB);

namespace seq {
Matrix gemm(const Matrix& A, const Matrix& B, double alpha, Matrix* Cptr, double beta, int MB, int NB, int KB) {
    return ::gemm(A,B,alpha,Cptr,beta,MB,NB,KB);
}
}
