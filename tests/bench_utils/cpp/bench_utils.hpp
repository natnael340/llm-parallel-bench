#pragma once
#include <algorithm>
#include <chrono>
#include <cstdlib>
#include <fstream>
#include <functional>
#include <iomanip>
#include <sstream>
#include <string>
#include <vector>

struct BenchResult {
    double median;
    double iqr;  // Q3 - Q1
    std::vector<double> elapsed_ms;
    int iterations;
};

inline BenchResult run_benchmark(std::function<void()> fn,
                                 int reps = 5, int iters = 20, int warmup = 1) {
    for (int i = 0; i < warmup; i++) fn();

    std::vector<double> per_run_ms;
    per_run_ms.reserve(reps);
    for (int r = 0; r < reps; r++) {
        auto start = std::chrono::high_resolution_clock::now();
        for (int k = 0; k < iters; k++) fn();
        auto end = std::chrono::high_resolution_clock::now();
        double ms = std::chrono::duration<double, std::milli>(end - start).count();
        per_run_ms.push_back(ms / iters);
    }

    std::vector<double> s = per_run_ms;
    std::sort(s.begin(), s.end());
    int n = static_cast<int>(s.size());
    double median = (n % 2 == 0) ? (s[n / 2 - 1] + s[n / 2]) / 2.0 : s[n / 2];
    double q1 = s[static_cast<int>((n - 1) * 0.25)];
    double q3 = s[static_cast<int>((n - 1) * 0.75)];
    double iqr = q3 - q1;

    return {median, iqr, per_run_ms, reps};
}

inline std::string format_result(const std::string& label, const BenchResult& r) {
    std::ostringstream ss;
    ss << std::fixed << std::setprecision(2)
       << label << " | " << r.median << " ms/run ± " << r.iqr
       << " IQR (n=" << r.iterations << ")";
    return ss.str();
}

inline void write_result(const BenchResult& r, const std::string& out_path,
                         const std::string& algo, const std::string& lang,
                         const std::string& impl, int iters_per_rep) {
    if (out_path.empty()) return;
    std::ofstream f(out_path);
    if (!f) return;
    f << std::fixed << std::setprecision(6);
    f << "{\n"
      << "  \"algo\": \"" << algo << "\",\n"
      << "  \"lang\": \"" << lang << "\",\n"
      << "  \"impl\": \"" << impl << "\",\n"
      << "  \"elapsed_ms\": [";
    for (int i = 0; i < static_cast<int>(r.elapsed_ms.size()); i++) {
        if (i) f << ", ";
        f << r.elapsed_ms[i];
    }
    f << "],\n"
      << "  \"median\": " << r.median << ",\n"
      << "  \"iqr\": " << r.iqr << ",\n"
      << "  \"reps\": " << r.iterations << ",\n"
      << "  \"iters_per_rep\": " << iters_per_rep << "\n"
      << "}\n";
}
