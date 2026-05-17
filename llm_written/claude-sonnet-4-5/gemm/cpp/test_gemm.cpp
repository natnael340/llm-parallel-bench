// test_gemm.cpp - Differential test harness for GEMM
#include <iostream>
#include <iomanip>
#include <fstream>
#include <vector>
#include <cmath>
#include <cstring>
#include <chrono>
#include <sstream>
#include <functional>
#include <random>
#include <omp.h>
#include "gemm_seq.hpp"
#include "gemm_parallel.hpp"

// Hash function for determinism checking
size_t hashMatrix(const Matrix& m) {
    size_t h = 0;
    const size_t prime = 0x9e3779b97f4a7c15ULL;
    for (const auto& row : m) {
        for (double val : row) {
            // Use bit representation for exact floating-point hashing
            uint64_t bits;
            std::memcpy(&bits, &val, sizeof(double));
            h ^= bits + prime + (h << 6) + (h >> 2);
        }
    }
    return h;
}

// Compare two matrices for exact equality
bool matricesEqual(const Matrix& A, const Matrix& B, double tol = 0.0) {
    auto [m1, n1] = getSize(A);
    auto [m2, n2] = getSize(B);
    if (m1 != m2 || n1 != n2) return false;
    
    for (int i = 0; i < m1; ++i) {
        for (int j = 0; j < n1; ++j) {
            double diff = std::abs(A[i][j] - B[i][j]);
            if (tol == 0.0) {
                if (A[i][j] != B[i][j]) return false;
            } else {
                if (diff > tol) return false;
            }
        }
    }
    return true;
}

// Generate random matrix with seed for reproducibility
Matrix randomMatrix(int rows, int cols, int seed) {
    std::mt19937 gen(seed);
    std::uniform_real_distribution<double> dist(-10.0, 10.0);
    Matrix m(rows, std::vector<double>(cols));
    for (int i = 0; i < rows; ++i) {
        for (int j = 0; j < cols; ++j) {
            m[i][j] = dist(gen);
        }
    }
    return m;
}

// Test case structure
struct TestCase {
    std::string name;
    Matrix A, B;
    double alpha, beta;
    Matrix* C_init;  // nullptr for fresh C
    int MB, NB, KB;
    
    TestCase(std::string n, Matrix a, Matrix b, double al = 1.0, double be = 1.0,
             Matrix* c = nullptr, int mb = defaultMB, int nb = defaultNB, int kb = defaultKB)
        : name(n), A(a), B(b), alpha(al), beta(be), C_init(c), MB(mb), NB(nb), KB(kb) {}
};

// Run a single test case
bool runTest(const TestCase& tc, bool verbose = false) {
    if (verbose) {
        std::cout << "  Running: " << tc.name << std::endl;
    }
    
    try {
        // Run sequential
        Matrix C_seq_copy;
        Matrix* C_seq_ptr = nullptr;
        if (tc.C_init) {
            C_seq_copy = *tc.C_init;
            C_seq_ptr = &C_seq_copy;
        }
        auto seq_result = gemm(tc.A, tc.B, tc.alpha, C_seq_ptr, tc.beta, tc.MB, tc.NB, tc.KB);
        
        // Run parallel (first time)
        Matrix C_par1_copy;
        Matrix* C_par1_ptr = nullptr;
        if (tc.C_init) {
            C_par1_copy = *tc.C_init;
            C_par1_ptr = &C_par1_copy;
        }
        auto par_result1 = gemm_parallel(tc.A, tc.B, tc.alpha, C_par1_ptr, tc.beta, tc.MB, tc.NB, tc.KB);
        
        // Run parallel (second time for determinism check)
        Matrix C_par2_copy;
        Matrix* C_par2_ptr = nullptr;
        if (tc.C_init) {
            C_par2_copy = *tc.C_init;
            C_par2_ptr = &C_par2_copy;
        }
        auto par_result2 = gemm_parallel(tc.A, tc.B, tc.alpha, C_par2_ptr, tc.beta, tc.MB, tc.NB, tc.KB);
        
        // Run parallel (third time for determinism check)
        Matrix C_par3_copy;
        Matrix* C_par3_ptr = nullptr;
        if (tc.C_init) {
            C_par3_copy = *tc.C_init;
            C_par3_ptr = &C_par3_copy;
        }
        auto par_result3 = gemm_parallel(tc.A, tc.B, tc.alpha, C_par3_ptr, tc.beta, tc.MB, tc.NB, tc.KB);
        
        // Check correctness (parallel vs sequential)
        bool correct = matricesEqual(seq_result, par_result1);
        
        // Check determinism (all parallel runs match)
        size_t hash1 = hashMatrix(par_result1);
        size_t hash2 = hashMatrix(par_result2);
        size_t hash3 = hashMatrix(par_result3);
        bool deterministic = (hash1 == hash2) && (hash2 == hash3);
        
        if (verbose) {
            std::cout << "    Correctness: " << (correct ? "PASS" : "FAIL") << std::endl;
            std::cout << "    Determinism: " << (deterministic ? "PASS" : "FAIL") 
                      << " (hashes: " << std::hex << hash1 << ", " << hash2 << ", " << hash3 
                      << std::dec << ")" << std::endl;
        }
        
        return correct && deterministic;
        
    } catch (const std::exception& e) {
        if (verbose) {
            std::cout << "    EXCEPTION: " << e.what() << std::endl;
        }
        return false;
    }
}

// Performance test
struct PerfResult {
    double seq_time;
    double par_time;
    double speedup;
    int threads;
};

PerfResult runPerfTest(int m, int k, int n, int seed = 42) {
    Matrix A = randomMatrix(m, k, seed);
    Matrix B = randomMatrix(k, n, seed + 1);
    
    // Warmup
    auto warmup = gemm_parallel(A, B);
    
    // Sequential timing
    auto t1 = std::chrono::high_resolution_clock::now();
    auto seq_result = gemm(A, B);
    auto t2 = std::chrono::high_resolution_clock::now();
    double seq_time = std::chrono::duration<double>(t2 - t1).count();
    
    // Parallel timing (average of 3 runs)
    double par_time_sum = 0.0;
    for (int run = 0; run < 3; ++run) {
        auto t3 = std::chrono::high_resolution_clock::now();
        auto par_result = gemm_parallel(A, B);
        auto t4 = std::chrono::high_resolution_clock::now();
        par_time_sum += std::chrono::duration<double>(t4 - t3).count();
    }
    double par_time = par_time_sum / 3.0;
    
    PerfResult result;
    result.seq_time = seq_time;
    result.par_time = par_time;
    result.speedup = seq_time / par_time;
    result.threads = omp_get_max_threads();
    
    return result;
}

int main() {
    std::cout << "=== GEMM Differential Test Suite ===" << std::endl;
    std::cout << "OpenMP threads available: " << omp_get_max_threads() << std::endl << std::endl;
    
    std::vector<TestCase> tests;
    
    // Edge case: 1x1 matrices
    tests.emplace_back("Edge: 1x1 matrices",
                       Matrix{{2.0}}, Matrix{{3.0}});
    
    // Edge case: single row
    tests.emplace_back("Edge: single row A",
                       Matrix{{1.0, 2.0, 3.0}},
                       Matrix{{1.0}, {2.0}, {3.0}});
    
    // Edge case: single column
    tests.emplace_back("Edge: single column B",
                       Matrix{{1.0}, {2.0}, {3.0}},
                       Matrix{{1.0, 2.0, 3.0}});
    
    // Small: 4x4 matrices
    tests.emplace_back("Small: 4x4 matrices",
                       randomMatrix(4, 4, 100),
                       randomMatrix(4, 4, 101));
    
    // Small: non-square 5x3 * 3x7
    tests.emplace_back("Small: 5x3 * 3x7",
                       randomMatrix(5, 3, 200),
                       randomMatrix(3, 7, 201));
    
    // Small: with alpha and beta
    Matrix C_init = randomMatrix(4, 4, 300);
    tests.emplace_back("Small: alpha=2.5, beta=0.5",
                       randomMatrix(4, 4, 301),
                       randomMatrix(4, 4, 302),
                       2.5, 0.5, &C_init);
    
    // Medium: 64x64 (at block boundary)
    tests.emplace_back("Medium: 64x64 (block boundary)",
                       randomMatrix(64, 64, 400),
                       randomMatrix(64, 64, 401));
    
    // Medium: 100x80 * 80x120
    tests.emplace_back("Medium: 100x80 * 80x120",
                       randomMatrix(100, 80, 500),
                       randomMatrix(80, 120, 501));
    
    // Medium: 128x128 (crosses parallel threshold)
    tests.emplace_back("Medium: 128x128",
                       randomMatrix(128, 128, 600),
                       randomMatrix(128, 128, 601));
    
    // Large: 256x256
    tests.emplace_back("Large: 256x256",
                       randomMatrix(256, 256, 700),
                       randomMatrix(256, 256, 701));
    
    // Large: non-square 512x256 * 256x128
    tests.emplace_back("Large: 512x256 * 256x128",
                       randomMatrix(512, 256, 800),
                       randomMatrix(256, 128, 801));
    
    // Run all tests
    int passed = 0;
    int total = tests.size();
    
    std::cout << "Running " << total << " correctness and determinism tests..." << std::endl << std::endl;
    
    for (const auto& tc : tests) {
        bool result = runTest(tc, true);
        if (result) {
            passed++;
            std::cout << "  ✓ PASS" << std::endl;
        } else {
            std::cout << "  ✗ FAIL" << std::endl;
        }
        std::cout << std::endl;
    }
    
    std::cout << "=== Correctness Summary ===" << std::endl;
    std::cout << "Passed: " << passed << "/" << total << std::endl;
    std::cout << "Failed: " << (total - passed) << "/" << total << std::endl << std::endl;
    
    // Performance tests
    std::cout << "=== Performance Tests ===" << std::endl;
    
    std::vector<std::tuple<int, int, int>> perf_sizes = {
        {256, 256, 256},
        {512, 512, 512},
        {1024, 512, 512}
    };
    
    std::vector<PerfResult> perf_results;
    
    for (const auto& [m, k, n] : perf_sizes) {
        std::cout << "Testing " << m << "x" << k << " * " << k << "x" << n << "..." << std::endl;
        PerfResult pr = runPerfTest(m, k, n);
        perf_results.push_back(pr);
        
        std::cout << "  Sequential: " << std::fixed << std::setprecision(4) << pr.seq_time << " s" << std::endl;
        std::cout << "  Parallel:   " << std::fixed << std::setprecision(4) << pr.par_time << " s" << std::endl;
        std::cout << "  Speedup:    " << std::fixed << std::setprecision(2) << pr.speedup << "x" << std::endl;
        std::cout << "  Efficiency: " << std::fixed << std::setprecision(1) 
                  << (pr.speedup / pr.threads * 100.0) << "%" << std::endl << std::endl;
    }
    
    // Write summary to file
    std::ofstream summary("run_summary.txt");
    summary << "GEMM Test Results\n";
    summary << "=================\n\n";
    summary << "Correctness Tests: " << passed << "/" << total << " passed\n";
    summary << "Failed: " << (total - passed) << "\n\n";
    
    summary << "Test Details:\n";
    for (const auto& tc : tests) {
        bool result = runTest(tc, false);
        summary << "  " << tc.name << ": " << (result ? "PASS" : "FAIL") << "\n";
    }
    
    summary << "\nPerformance Results:\n";
    summary << "Threads: " << omp_get_max_threads() << "\n\n";
    
    int idx = 0;
    for (const auto& [m, k, n] : perf_sizes) {
        const auto& pr = perf_results[idx++];
        summary << m << "x" << k << " * " << k << "x" << n << ":\n";
        summary << "  Sequential: " << std::fixed << std::setprecision(4) << pr.seq_time << " s\n";
        summary << "  Parallel:   " << std::fixed << std::setprecision(4) << pr.par_time << " s\n";
        summary << "  Speedup:    " << std::fixed << std::setprecision(2) << pr.speedup << "x\n";
        summary << "  Efficiency: " << std::fixed << std::setprecision(1) 
                << (pr.speedup / pr.threads * 100.0) << "%\n\n";
    }
    summary.close();
    
    // Write performance details
    std::ofstream perf("perf.txt");
    perf << "GEMM Performance Results\n";
    perf << "========================\n\n";
    perf << "Threads: " << omp_get_max_threads() << "\n\n";
    
    idx = 0;
    for (const auto& [m, k, n] : perf_sizes) {
        const auto& pr = perf_results[idx++];
        perf << "Test: " << m << "x" << k << " * " << k << "x" << n << "\n";
        perf << "  t_seq:      " << std::fixed << std::setprecision(4) << pr.seq_time << " s\n";
        perf << "  t_par:      " << std::fixed << std::setprecision(4) << pr.par_time << " s\n";
        perf << "  Speedup:    " << std::fixed << std::setprecision(2) << pr.speedup << "x\n";
        perf << "  Efficiency: " << std::fixed << std::setprecision(1) 
             << (pr.speedup / pr.threads * 100.0) << "%\n\n";
    }
    perf.close();
    
    std::cout << "Results written to run_summary.txt and perf.txt" << std::endl;
    
    return (passed == total) ? 0 : 1;
}
