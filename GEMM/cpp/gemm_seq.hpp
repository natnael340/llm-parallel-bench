#ifndef BFS_HPP
#define BFS_HPP

#include <vector>

using Matrix = std::vector<std::vector<double>>;

Matrix gemm(const Matrix& A, const Matrix& B, double alpha=1.0, Matrix* Cptr = nullptr, double beta = 0.0, int MB = 64, int NB=64, int KB=64);

#endif