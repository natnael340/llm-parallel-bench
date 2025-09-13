// fast_gemm_sweep.cpp
// Staged sweep for (MB, NB, KB) using your Matrix + gemm() from gemm.hpp.

#include <algorithm>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <numeric>
#include <random>
#include <set>
#include <string>
#include <tuple>
#include <utility>
#include <vector>
#include <functional>

#include "../../GEMM/cpp/gemm_seq.hpp"  // provides: using Matrix = std::vector<std::vector<double>>;
                    // Matrix gemm(const Matrix& A, const Matrix& B, double alpha=1.0,
                    //              Matrix* Cptr=nullptr, double beta=0.0,
                    //              int MB=64, int NB=64, int KB=64);

using Clock = std::chrono::steady_clock;

// ---------- helpers ----------
Matrix make_random_matrix(int r, int c, int seed = 0) {
    std::mt19937 rng(seed);
    std::uniform_real_distribution<double> dist(-1.0, 1.0);
    Matrix M(r, std::vector<double>(c));
    for (int i = 0; i < r; ++i)
        for (int j = 0; j < c; ++j)
            M[i][j] = dist(rng);
    return M;
}

inline double gflops(std::int64_t m, std::int64_t n, std::int64_t k, double seconds) {
    return (2.0 * double(m) * double(n) * double(k)) / (seconds * 1e9);
}

double time_avg_per_run(std::function<void()> fn, double min_wall = 0.6, int warmup = 1) {
    for (int i = 0; i < warmup; ++i) fn();
    int runs = 0;
    const auto t0 = Clock::now();
    double elapsed = 0.0;
    do {
        fn();
        runs++;
        elapsed = std::chrono::duration<double>(Clock::now() - t0).count();
    } while (elapsed < min_wall);
    return elapsed / std::max(runs, 1);
}

struct EvalResult {
    double avg_ms;
    double sd_ms;
    double gflops;
};

EvalResult eval_config(const Matrix& A,
                       const Matrix& B,
                       int MB, int NB, int KB,
                       int repeats = 3,
                       double min_wall = 0.6) {
    const int m = static_cast<int>(A.size());
    const int k = static_cast<int>(A[0].size());
    const int n = static_cast<int>(B[0].size());

    Matrix C(m, std::vector<double>(n, 0.0));  // reused across runs
    std::vector<double> samples;
    samples.reserve(repeats);

    auto run_once = [&]() {
        // Your gemm writes into C when Cptr is provided; beta=0.0 avoids dependency on prior C.
        gemm(A, B, /*alpha=*/1.0, &C, /*beta=*/0.0, MB, NB, KB);
    };

    for (int r = 0; r < repeats; ++r) {
        const double avg_s = time_avg_per_run(run_once, min_wall, /*warmup=*/1);
        samples.push_back(avg_s);
    }

    const double mean = std::accumulate(samples.begin(), samples.end(), 0.0) / samples.size();
    double var = 0.0;
    for (double x : samples) var += (x - mean) * (x - mean);
    var /= samples.size(); // population variance

    return EvalResult{
        mean * 1000.0,                 // avg_ms
        std::sqrt(var) * 1000.0,       // sd_ms
        gflops(m, n, k, mean)          // gflops
    };
}

static inline int clampi(int v, int lo, int hi) {
    return std::max(lo, std::min(hi, v));
}

struct Row {
    int stage;
    int MB, NB, KB;
    double avg_ms, sd_ms, gflops;
};

int main(int argc, char** argv) {
    // Defaults match your Python __main__ quick run
    int M = 256, N = 256, K = 256;
    std::vector<int> kb_list = {16, 32, 48, 64, 96, 128};
    std::vector<int> coarse  = {8, 16, 32, 48, 64};
    int step_refine = 8;
    int top_kb = 2, top_mb_nb = 5;
    int repeats = 3;
    double min_wall = 5.0; // seconds per repeat group
    std::string csv_path = "gemm_sweep_staged_256_2.csv";
    int seedA = 1, seedB = 2;

    // Optional CLI: M N K csv_path
    if (argc >= 4) {
        M = std::stoi(argv[1]);
        N = std::stoi(argv[2]);
        K = std::stoi(argv[3]);
    }
    if (argc >= 5) csv_path = argv[4];

    // Matrices
    Matrix A = make_random_matrix(M, K, seedA);
    Matrix B = make_random_matrix(K, N, seedB);

    std::vector<Row> rows;

    // ---- Stage 1: scan KB with MB=NB=32
    std::vector<std::pair<double,int>> kb_scores; // (gflops, KB)
    for (int KB : kb_list) {
        auto r = eval_config(A, B, /*MB=*/32, /*NB=*/32, KB, repeats, min_wall);
        rows.push_back({1, 32, 32, KB, r.avg_ms, r.sd_ms, r.gflops});
        kb_scores.emplace_back(r.gflops, KB);
        std::cout << "[Stage1] KB=" << KB
                  << "  " << std::fixed << std::setprecision(2)
                  << r.avg_ms << " ms ~" << r.gflops << " GFLOPs (±" << r.sd_ms << " ms)\n";
    }
    std::sort(kb_scores.begin(), kb_scores.end(),
              [](auto& a, auto& b){ return a.first > b.first; });
    std::vector<int> chosen_kb;
    for (int i = 0; i < std::min<int>(top_kb, (int)kb_scores.size()); ++i)
        chosen_kb.push_back(kb_scores[i].second);

    // ---- Stage 2: coarse MB/NB for each chosen KB
    std::set<std::tuple<int,int,int>> mbnb_candidates; // (MB,NB,KB)
    for (int KB : chosen_kb) {
        std::vector<std::tuple<double,int,int>> scored; // (gflops, MB, NB)
        for (int MB : coarse) for (int NB : coarse) {
            auto r = eval_config(A, B, MB, NB, KB, repeats, min_wall);
            rows.push_back({2, MB, NB, KB, r.avg_ms, r.sd_ms, r.gflops});
            scored.emplace_back(r.gflops, MB, NB);
            std::cout << "[Stage2] KB=" << KB << " MB=" << MB << " NB=" << NB
                      << "  " << std::fixed << std::setprecision(2)
                      << r.avg_ms << " ms ~" << r.gflops << " GFLOPs (±" << r.sd_ms << " ms)\n";
        }
        std::sort(scored.begin(), scored.end(),
                  [](auto& a, auto& b){ return std::get<0>(a) > std::get<0>(b); });
        for (int i = 0; i < std::min<int>(top_mb_nb, (int)scored.size()); ++i) {
            auto [/*gflops*/_, MB, NB] = scored[i];
            mbnb_candidates.emplace(MB, NB, KB);
        }
    }

    // ---- Stage 3: local refinement
    std::set<std::tuple<int,int,int>> refined;
    for (auto [MB, NB, KB] : mbnb_candidates) {
        for (int dmb : {-step_refine, 0, step_refine}) {
            for (int dnb : {-step_refine, 0, step_refine}) {
                int MB2 = clampi(MB + dmb, 4, M);
                int NB2 = clampi(NB + dnb, 4, N);
                MB2 = (MB2 / 4) * 4; // snap to multiples of 4
                NB2 = (NB2 / 4) * 4;
                if (MB2 <= 0 || NB2 <= 0) continue;
                refined.emplace(MB2, NB2, KB);
            }
        }
    }
    for (auto [MB, NB, KB] : refined) {
        auto r = eval_config(A, B, MB, NB, KB, repeats, min_wall);
        rows.push_back({3, MB, NB, KB, r.avg_ms, r.sd_ms, r.gflops});
        std::cout << "[Stage3] KB=" << KB << " MB=" << MB << " NB=" << NB
                  << "  " << std::fixed << std::setprecision(2)
                  << r.avg_ms << " ms ~" << r.gflops << " GFLOPs (±" << r.sd_ms << " ms)\n";
    }

    // ---- Save CSV
    {
        std::ofstream f(csv_path);
        f << "stage,MB,NB,KB,avg_ms,sd_ms,gflops\n";
        f << std::fixed << std::setprecision(6);
        for (const auto& r : rows) {
            f << r.stage << ',' << r.MB << ',' << r.NB << ',' << r.KB << ','
              << r.avg_ms << ',' << r.sd_ms << ',' << r.gflops << '\n';
        }
    }

    // ---- Print Top 10
    std::vector<const Row*> sorted;
    sorted.reserve(rows.size());
    for (auto& r : rows) sorted.push_back(&r);
    std::sort(sorted.begin(), sorted.end(),
              [](const Row* a, const Row* b){ return a->gflops > b->gflops; });

    std::cout << "\nTop 10 configs:\n";
    for (std::size_t i = 0; i < std::min<std::size_t>(10, sorted.size()); ++i) {
        const Row* r = sorted[i];
        std::cout << "stage" << r->stage
                  << " MB/NB/KB=" << r->MB << '/' << r->NB << '/' << r->KB
                  << "  " << std::fixed << std::setprecision(2)
                  << r->avg_ms << " ms  ~" << r->gflops << " GFLOPs"
                  << "  (±" << r->sd_ms << " ms)\n";
    }

    std::cout << "\nCSV written to: " << csv_path << "\n";
    return 0;
}
