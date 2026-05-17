#include <iostream>
#include <string>
#include <vector>
#include <tuple>
#include <cassert>
#include <chrono>
#include <functional>
#include <iomanip>
#include <fstream>
#include <sys/stat.h>

#include "smith_waterman_sequential.h"
#include "algo_parallel.h"

// Helper function to generate a random string
std::string generate_random_string(int length) {
    std::string chars = "ACGT";
    std::string result = "";
    for (int i = 0; i < length; ++i) {
        result += chars[rand() % chars.length()];
    }
    return result;
}

// Function to compute the hash of the result tuple
size_t result_hash(const std::tuple<std::string, std::string, int, double>& result) {
    size_t h1 = std::hash<std::string>{}(std::get<0>(result));
    size_t h2 = std::hash<std::string>{}(std::get<1>(result));
    size_t h3 = std::hash<int>{}(std::get<2>(result));
    // Hash double with precision
    std::stringstream ss;
    ss << std::fixed << std::setprecision(5) << std::get<3>(result);
    size_t h4 = std::hash<std::string>{}(ss.str());
    return h1 ^ (h2 << 1) ^ (h3 << 2) ^ (h4 << 3);
}

// Test function
bool run_test(const std::string& query, const std::string& reference, int match, int mismatch, int gap, std::ofstream& summary_file, std::ofstream& perf_file) {
    SmithWatermanSequential sw_seq(match, mismatch, gap);
    SmithWaterman sw_par(match, mismatch, gap);

    // Run sequential version
    auto start_seq = std::chrono::high_resolution_clock::now();
    auto result_seq = sw_seq.findAlignment(query, reference);
    auto end_seq = std::chrono::high_resolution_clock::now();
    std::chrono::duration<double> diff_seq = end_seq - start_seq;

    // Run parallel version
    auto start_par = std::chrono::high_resolution_clock::now();
    auto result_par = sw_par.findAlignment(query, reference);
    auto end_par = std::chrono::high_resolution_clock::now();
    std::chrono::duration<double> diff_par = end_par - start_par;
    
    // Run parallel version again for determinism check
    auto result_par2 = sw_par.findAlignment(query, reference);

    // Correctness and determinism checks
    bool correct = (result_hash(result_seq) == result_hash(result_par));
    bool deterministic = (result_hash(result_par) == result_hash(result_par2));

    summary_file << "Test Case (Query: " << query.length() << ", Reference: " << reference.length() << ")\n";
    summary_file << "  - Correctness: " << (correct ? "PASS" : "FAIL") << "\n";
    summary_file << "  - Determinism: " << (deterministic ? "PASS" : "FAIL") << "\n";
    summary_file << "  - Hashes: \n";
    summary_file << "    - Sequential: " << result_hash(result_seq) << "\n";
    summary_file << "    - Parallel 1: " << result_hash(result_par) << "\n";
    summary_file << "    - Parallel 2: " << result_hash(result_par2) << "\n\n";

    if (query.length() >= 500) {
        perf_file << "Query: " << query.length() << ", Reference: " << reference.length() 
                  << ", Sequential Time (s): " << diff_seq.count() 
                  << ", Parallel Time (s): " << diff_par.count() 
                  << ", Speedup: " << (diff_par.count() > 0 ? diff_seq.count() / diff_par.count() : 0) << "x\n";
    }
    
    return correct && deterministic;
}

int main(int argc, char* argv[]) {
    srand(123); // for reproducibility

    mkdir("evidence", 0755);
    std::ofstream summary_file("evidence/run_summary.txt");
    std::ofstream perf_file("evidence/perf.txt");

    bool all_tests_passed = true;

    // Test cases
    all_tests_passed &= run_test("AGCAT", "GAC", 1, -1, -1, summary_file, perf_file);
    all_tests_passed &= run_test("AGCT", "AGCT", 1, -1, -1, summary_file, perf_file);
    all_tests_passed &= run_test("A", "A", 1, -1, -1, summary_file, perf_file);
    all_tests_passed &= run_test("", "", 1, -1, -1, summary_file, perf_file);
    all_tests_passed &= run_test("AGCT", "", 1, -1, -1, summary_file, perf_file);
    all_tests_passed &= run_test(generate_random_string(100), generate_random_string(100), 1, -1, -1, summary_file, perf_file);
    all_tests_passed &= run_test(generate_random_string(500), generate_random_string(500), 1, -1, -1, summary_file, perf_file);
    all_tests_passed &= run_test(generate_random_string(1000), generate_random_string(1000), 1, -1, -1, summary_file, perf_file);

    summary_file.close();
    perf_file.close();

    if (all_tests_passed) {
        std::cout << "All tests passed!" << std::endl;
        return 0;
    } else {
        std::cout << "Some tests failed. Check evidence/run_summary.txt for details." << std::endl;
        return 1;
    }
}
