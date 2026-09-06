#pragma once
#include <algorithm>
#include <cerrno>
#include <chrono>
#include <cmath>
#include <cstdlib>
#include <ctime>
#include <fstream>
#include <functional>
#include <iomanip>
#include <iostream>
#include <limits>
#include <numeric>
#include <sstream>
#include <string>
#include <vector>

struct BenchResult {
    double median;
    double iqr;  // Q3 - Q1
    double mean;
    double sd;   // sample standard deviation
    std::vector<double> elapsed_ms;
    int iterations;
};

// --- env helpers: the standard benchmark env contract ---
// Rejects malformed values instead of std::atoi's silent 0, which produced an
// empty sample vector, out-of-bounds quantile reads and a bare `nan` token in
// the result JSON -- surfacing far downstream as an unparseable result file.
inline int bench_env_int(const char* name, int def) {
    const char* v = std::getenv(name);
    if (!v || !*v) return def;
    errno = 0;
    char* end = nullptr;
    long parsed = std::strtol(v, &end, 10);
    if (end == v || *end != '\0' || errno == ERANGE || parsed <= 0 ||
        parsed > std::numeric_limits<int>::max()) {
        std::cerr << "bench: " << name << "=" << v
                  << " is not a positive integer\n";
        std::exit(2);
    }
    return static_cast<int>(parsed);
}
inline int bench_reps(int def = 5) { return bench_env_int("BENCH_REPS", def); }
inline int bench_iters(int def = 20) { return bench_env_int("BENCH_ITERS", def); }
inline std::string bench_impl() {
    const char* v = std::getenv("IMPL");
    return v ? std::string(v) : std::string("seq");
}
inline std::string bench_model() {
    const char* v = std::getenv("MODEL");
    return v ? std::string(v) : std::string("baseline");
}
inline std::string bench_out() {
    const char* v = std::getenv("BENCH_OUT");
    return v ? std::string(v) : std::string("");
}

// Interquartile range using the same definition as Python's
// statistics.quantiles(data, n=4) (exclusive, interpolated), so the dispersion
// figure is comparable across all six languages and matches what
// bench/aggregate.py recomputes. Requires n >= 2.
inline double bench_iqr(const std::vector<double>& sorted_s) {
    const int n = static_cast<int>(sorted_s.size());
    const int nq = 4, m = n + 1;
    double q[3];
    for (int i = 1; i <= 3; i++) {
        int j = i * m / nq;
        if (j < 1) j = 1;
        if (j > n - 1) j = n - 1;
        const double delta = i * m - j * nq;
        q[i - 1] = (sorted_s[j - 1] * (nq - delta) + sorted_s[j] * delta) / nq;
    }
    return q[2] - q[0];
}

inline BenchResult run_benchmark(std::function<void()> fn,
                                 int reps = 5, int iters = 20, int warmup = 1) {
    if (reps <= 0 || iters <= 0) {
        std::cerr << "bench: reps and iters must be positive (got reps=" << reps
                  << ", iters=" << iters << ")\n";
        std::exit(2);
    }
    for (int i = 0; i < warmup; i++) fn();

    std::vector<double> per_run_ms;
    per_run_ms.reserve(reps);
    for (int r = 0; r < reps; r++) {
        // steady_clock is guaranteed monotonic; high_resolution_clock may
        // alias a wall clock that can step backwards (observed under WSL2,
        // producing negative elapsed times).
        auto start = std::chrono::steady_clock::now();
        for (int k = 0; k < iters; k++) fn();
        auto end = std::chrono::steady_clock::now();
        double ms = std::chrono::duration<double, std::milli>(end - start).count();
        per_run_ms.push_back(ms / iters);
    }

    std::vector<double> s = per_run_ms;
    std::sort(s.begin(), s.end());
    int n = static_cast<int>(s.size());
    double median = (n % 2 == 0) ? (s[n / 2 - 1] + s[n / 2]) / 2.0 : s[n / 2];
    double iqr = (n > 1) ? bench_iqr(s) : 0.0;

    double mean = std::accumulate(s.begin(), s.end(), 0.0) / n;
    double sq = 0.0;
    for (double v : s) sq += (v - mean) * (v - mean);
    double sd = (n > 1) ? std::sqrt(sq / (n - 1)) : 0.0;

    return {median, iqr, mean, sd, per_run_ms, reps};
}

inline std::string format_result(const std::string& label, const BenchResult& r) {
    std::ostringstream ss;
    ss << std::fixed << std::setprecision(2)
       << label << " | mean " << r.mean << " ms/run ± " << r.sd << " SD"
       << " | median " << r.median << " ms/run ± " << r.iqr
       << " IQR (n=" << r.iterations << ")";
    return ss.str();
}

inline std::string bench_timestamp_utc() {
    std::time_t t = std::time(nullptr);
    char buf[32];
    std::strftime(buf, sizeof(buf), "%Y-%m-%dT%H:%M:%S+00:00", std::gmtime(&t));
    return std::string(buf);
}

// params_json: pre-rendered JSON object, e.g. R"({"graph_size": 2000})".
inline void write_result(const BenchResult& r, const std::string& out_path,
                         const std::string& algo, const std::string& lang,
                         const std::string& impl, int iters_per_rep,
                         const std::string& params_json = "{}") {
    if (out_path.empty()) return;
    std::ofstream f(out_path);
    if (!f) return;
    f << std::fixed << std::setprecision(6);
    f << "{\n"
      << "  \"schema_version\": 2,\n"
      << "  \"algo\": \"" << algo << "\",\n"
      << "  \"lang\": \"" << lang << "\",\n"
      << "  \"impl\": \"" << impl << "\",\n"
      << "  \"model\": \"" << bench_model() << "\",\n"
      << "  \"elapsed_ms\": [";
    for (int i = 0; i < static_cast<int>(r.elapsed_ms.size()); i++) {
        if (i) f << ", ";
        f << r.elapsed_ms[i];
    }
    f << "],\n"
      << "  \"mean\": " << r.mean << ",\n"
      << "  \"sd\": " << r.sd << ",\n"
      << "  \"median\": " << r.median << ",\n"
      << "  \"iqr\": " << r.iqr << ",\n"
      << "  \"reps\": " << r.iterations << ",\n"
      << "  \"iters_per_rep\": " << iters_per_rep << ",\n"
      << "  \"params\": " << (params_json.empty() ? "{}" : params_json) << ",\n"
      << "  \"timestamp\": \"" << bench_timestamp_utc() << "\"\n"
      << "}\n";
}
