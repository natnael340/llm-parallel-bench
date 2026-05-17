// gemm_parallel.cpp - Parallel GEMM implementation with OpenMP
// 
// This file implements a parallel version of blocked matrix multiplication (GEMM).
// Strategy: Parallelize the combined (n-block, m-block) space while keeping k-blocks sequential.
// This ensures deterministic accumulation order while maximizing parallelism.

#include <iostream>
#include <vector>
#include <stdexcept>
#include <string>
#include <algorithm>
#include <omp.h>
#include "gemm_parallel.hpp"

// Parallel threshold: use parallel execution only if m >= this value
// Below this threshold, overhead dominates and sequential execution is faster
constexpr int PARALLEL_THRESHOLD_M = 128;

// gemm_parallel computes C := alpha * A * B + beta * C using OpenMP.
// 
// Parameters:
//   A: m x k matrix
//   B: k x n matrix
//   alpha: scalar multiplier for A*B
//   Cptr: pointer to m x n matrix C (if nullptr, a fresh matrix is created)
//   beta: scalar multiplier for existing C values
//   MB, NB, KB: block sizes for tiling (default 64)
//
// Returns:
//   The result matrix C
//
// Parallelization:
//   - For each k-block (sequential loop for determinism):
//     - Process all (n-block, m-block) pairs in parallel
//     - Each pair writes to a disjoint region of C (no conflicts)
//   - Static scheduling ensures deterministic work distribution
//   - Small matrices (m < 128) use sequential fallback
Matrix gemm_parallel(const Matrix& A, const Matrix& B,
                     double alpha,
                     Matrix* Cptr,
                     double beta,
                     int MB, int NB, int KB
) {
    validateMatrix(A, "A");
    validateMatrix(B, "B");

    auto [m, k] = getSize(A);
    auto [k2, n] = getSize(B);
    if (k != k2) {
        throw std::invalid_argument(
            "shape mismatch: A is (" + std::to_string(m) + "," + std::to_string(k) +
            "), B is (" + std::to_string(k2) + "," + std::to_string(n) + ")");
    }

    Matrix localC;
    Matrix& C = (Cptr ? *Cptr : (localC = generateMatrix(m, n)));

    if (Cptr) {
        validateMatrix(C, "C");
        auto [m2, n2] = getSize(C);
        if (m2 != m || n2 != n) {
            throw std::invalid_argument(
                "C has shape (" + std::to_string(m2) + "," + std::to_string(n2) +
                "); expected (" + std::to_string(m) + "," + std::to_string(n) + ")");
        }
        if (beta != 1.0) {
            // Parallelize beta scaling for large matrices
            if (m >= PARALLEL_THRESHOLD_M) {
                #pragma omp parallel for schedule(static)
                for (int i = 0; i < m; ++i) {
                    auto& row = C[i];
                    for (int j = 0; j < n; ++j) row[j] *= beta;
                }
            } else {
                for (int i = 0; i < m; ++i) {
                    auto& row = C[i];
                    for (int j = 0; j < n; ++j) row[j] *= beta;
                }
            }
        }
    }

    if (alpha == 0.0) {
        return C;
    }

    Matrix Bt = transpose(B);

    // For small matrices, use sequential execution to avoid overhead
    if (m < PARALLEL_THRESHOLD_M) {
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
        return C;
    }

    // For large matrices, parallelize over combined (n, m) space
    // while keeping k-loop sequential for deterministic accumulation.
    
    // Build a list of all (n0, m0) block pairs
    std::vector<std::pair<int, int>> nm_pairs;
    for (int n0 = 0; n0 < n; n0 += NB) {
        for (int m0 = 0; m0 < m; m0 += MB) {
            nm_pairs.emplace_back(n0, m0);
        }
    }
    
    int num_nm_pairs = nm_pairs.size();
    
    // Process k-blocks sequentially (for determinism)
    // For each k-block, process all (n, m) pairs in parallel
    for (int k0 = 0; k0 < k; k0 += KB) {
        int k1 = std::min(k0 + KB, k);
        int kb = k1 - k0;
        
        // Parallelize over (n, m) pairs
        // This is safe because:
        // 1. Different (n0, m0) pairs write to disjoint C regions
        // 2. Same k0 order is maintained across all pairs (determinism)
        // 3. Static schedule ensures same work distribution every run
        #pragma omp parallel for schedule(static)
        for (int idx = 0; idx < num_nm_pairs; ++idx) {
            int n0 = nm_pairs[idx].first;
            int m0 = nm_pairs[idx].second;
            
            int n1 = std::min(n0 + NB, n);
            int m1 = std::min(m0 + MB, m);
            
            // Pack submatrices for this block pair
            Matrix Bpack = packMatrix(Bt, k0, k1, n0, n1);
            Matrix Apack = packMatrix(A, k0, k1, m0, m1);
            
            // Compute partial result for this (n, m, k) block
            partialMatmul(Apack, Bpack, C, alpha, m0, n0, kb);
        }
        // Implicit barrier here ensures all threads finish k-block before proceeding
    }

    return C;
}
