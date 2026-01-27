#include <iostream>
#include <random>
#include <cassert>
#include <cmath>
#include <vector>
#include <chrono>

// Provide Matrix typedef and gemm prototype
#include "gemm_seq.hpp"

// Rename gemm to seq_gemm and include the sequential implementation body
#define gemm seq_gemm
#include "gemm_seq_impl.cpp"
#undef gemm

// Rename gemm to par_gemm and include the parallel implementation body
#define gemm par_gemm
#include "gemm_parallel_impl.cpp"
#undef gemm

static std::pair<int,int> getSize(const Matrix& m) {
    if (m.empty()) return {0, 0};
    return {static_cast<int>(m.size()), static_cast<int>(m[0].size())};
}

static Matrix randMatrix(int r, int c, std::mt19937& rng) {
    std::uniform_real_distribution<double> dist(-1.0, 1.0);
    Matrix M(r, std::vector<double>(c));
    for (int i = 0; i < r; ++i) {
        for (int j = 0; j < c; ++j) M[i][j] = dist(rng);
    }
    return M;
}

static bool equalMatrix(const Matrix& A, const Matrix& B, double tol=0.0) {
    if (A.size() != B.size()) return false;
    for (size_t i = 0; i < A.size(); ++i) {
        if (A[i].size() != B[i].size()) return false;
        for (size_t j = 0; j < A[i].size(); ++j) {
            double a = A[i][j];
            double b = B[i][j];
            if (tol == 0.0) { if (a != b) return false; }
            else { if (std::abs(a-b) > tol) return false; }
        }
    }
    return true;
}

static void run_case(const Matrix& A, const Matrix& B, double alpha, Matrix* Cptr, double beta, int MB, int NB, int KB) {
    Matrix C1; Matrix C2;
    if (Cptr) { C1 = *Cptr; C2 = *Cptr; }

    Matrix out_seq = seq_gemm(A, B, alpha, Cptr ? &C1 : nullptr, beta, MB, NB, KB);
    Matrix out_par = par_gemm(A, B, alpha, Cptr ? &C2 : nullptr, beta, MB, NB, KB);

    bool ok = equalMatrix(out_seq, out_par, 0.0);
    if (!ok) {
        std::cerr << "Mismatch!\n";
        auto [m, n] = getSize(out_seq);
        for (int i = 0; i < m; ++i) {
            for (int j = 0; j < n; ++j) {
                if (out_seq[i][j] != out_par[i][j]) {
                    std::cerr << "First diff at (" << i << "," << j << "): seq=" << out_seq[i][j] << ", par=" << out_par[i][j] << "\n";
                    i = m; break;
                }
            }
        }
        assert(false);
    }
}

int main() {
    std::mt19937 rng(12345);

    // Edge cases
    {
        Matrix A{{1.0}}; Matrix B{{2.0}}; Matrix C{{3.0}};
        run_case(A,B,1.0,nullptr,0.0,64,64,64);
        Matrix Ccopy = C; run_case(A,B,1.0,&Ccopy,0.0,64,64,64); // C provided, beta=0
        Ccopy = C; run_case(A,B,0.0,&Ccopy,1.0,64,64,64); // alpha=0
        Ccopy = C; run_case(A,B,2.0,&Ccopy,0.5,64,64,64);
    }

    // Small sizes, various tiles
    for (int m : {1,2,3,4,5,8})
        for (int k : {1,2,3,4,5,7})
            for (int n : {1,2,3,4,6})
                for (int MB : {1,2,3,4})
                    for (int NB : {1,2,3,4})
                        for (int KB : {1,2,3,4}) {
                            Matrix A = randMatrix(m,k,rng);
                            Matrix B = randMatrix(k,n,rng);
                            run_case(A,B,1.0,nullptr,0.0,MB,NB,KB);
                            Matrix C = randMatrix(m,n,rng);
                            run_case(A,B,0.0,&C,1.0,MB,NB,KB);
                            C = randMatrix(m,n,rng);
                            run_case(A,B,1.0,&C,0.0,MB,NB,KB);
                            C = randMatrix(m,n,rng);
                            run_case(A,B,0.5,&C,0.3,MB,NB,KB);
                        }

    // Random moderate cases
    for (int t = 0; t < 10; ++t) {
        int m = 15 + (t % 5);
        int k = 17 + (t % 7);
        int n = 13 + (t % 6);
        Matrix A = randMatrix(m,k,rng);
        Matrix B = randMatrix(k,n,rng);
        Matrix C = randMatrix(m,n,rng);
        run_case(A,B,1.0,nullptr,0.0,64,64,64);
        Matrix C1 = C; run_case(A,B,1.0,&C1,0.0,64,64,64);
        C1 = C; run_case(A,B,0.0,&C1,1.0,64,64,64);
        C1 = C; run_case(A,B,0.5,&C1,0.3,32,48,16);
    }

    // Determinism: run par twice and compare
    {
        int m=20,k=25,n=18; Matrix A = randMatrix(m,k,rng); Matrix B = randMatrix(k,n,rng); Matrix C = randMatrix(m,n,rng);
        Matrix Cp1 = C; Matrix Cp2 = C;
        Matrix out1 = par_gemm(A,B,0.7,&Cp1,0.2,32,32,32);
        Matrix out2 = par_gemm(A,B,0.7,&Cp2,0.2,32,32,32);
        assert(equalMatrix(out1,out2,0.0));
    }

    std::cout << "All tests passed\n";
    return 0;
}
