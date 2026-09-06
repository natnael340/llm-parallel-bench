#include <cmath>
#include <cstdlib>
#include <fstream>
#include <iostream>
#include <sstream>
#include <string>
#include <tuple>

#include "impl.hpp"          // staged adapter: class SmithWaterman with findAlignment(query, reference)
#include "bench_utils.hpp"

using namespace std;

static int g_failures = 0;
static const double EPS = 1e-6;

static void check(bool ok, const string& name) {
    cout << name << (ok ? " passed" : " failed") << endl;
    if (!ok) g_failures++;
}

static void test_case(const string& name, const string& query, const string& reference,
                      const string& expA, const string& expB, int expScore, double expIdentity) {
    SmithWaterman sw(2, -1, -1);
    auto [a, b, score, identity] = sw.findAlignment(query, reference);
    bool ok = (a == expA) && (b == expB) && (score == expScore)
              && (fabs(identity - expIdentity) <= EPS);
    if (!ok) {
        cout << "  got: a=" << a << " b=" << b << " score=" << score
             << " identity=" << identity << endl;
    }
    check(ok, name);
}

static bool readSWInput(string& query, string& reference, int& score, double& identity) {
    const char* path = getenv("SW_INPUT");
    if (!path) return false;
    ifstream f(path);
    if (!f) return false;
    string sScore, sIdentity;
    getline(f, query);
    getline(f, reference);
    getline(f, sScore);
    getline(f, sIdentity);
    score = stoi(sScore);
    identity = stod(sIdentity);
    return true;
}

int main() {
    test_case("test_perfect_match", "ACGT", "ACGT", "ACGT", "ACGT", 8, 100.0);
    test_case("test_no_match", "AAAA", "TTTT", "", "", 0, 0.0);
    test_case("test_partial_match", "ACGTACGT", "TACGTGCA", "TACGT", "TACGT", 10, 100.0);
    test_case("test_gap_in_query", "ACGT", "ACAGT", "AC-GT", "ACAGT", 7, 80.0);
    test_case("test_gap_in_reference", "ACAGT", "ACGT", "ACAGT", "AC-GT", 7, 80.0);
    test_case("test_single_char_match", "A", "A", "A", "A", 2, 100.0);

    string query, reference;
    int expScore = 0;
    double expIdentity = 0.0;
    bool haveInput = readSWInput(query, reference, expScore, expIdentity);

    if (haveInput) {
        SmithWaterman sw(2, -1, -1);
        auto [a, b, score, identity] = sw.findAlignment(query, reference);
        bool ok = (a.size() == b.size()) && (score == expScore)
                  && (fabs(identity - expIdentity) <= EPS);
        check(ok, "test_large_sequences_from_file");
    }

    if (g_failures > 0) {
        cout << g_failures << " test(s) failed — skipping benchmark" << endl;
        return 1;
    }

    if (!haveInput) {
        cout << "SW_INPUT not set — skipping benchmark" << endl;
        return 0;
    }

    SmithWaterman sw(2, -1, -1);
    int reps = bench_reps(5), iters = bench_iters(1);
    auto bm = run_benchmark([&]() { sw.findAlignment(query, reference); }, reps, iters, 1);
    cout << format_result("SW large sequences", bm) << endl;

    string params = "{\"query_len\": " + to_string(query.size())
        + ", \"reference_len\": " + to_string(reference.size()) + "}";
    write_result(bm, bench_out(), "smith-waterman", "cpp", bench_impl(), iters, params);
    return 0;
}
