#include <iostream>
#include <vector>
#include <string>
#include <random>
#include <chrono>
#include <functional>
#include <algorithm>
#include <iomanip>
#include <thread>
#include <fstream>
#include <sys/stat.h>
#include <tuple>


#include "algo_sequential.cpp"
#include "algo_parallel.cpp"

using namespace std;

// --- Test Utilities ---

template<class GraphType>
GraphType create_random_graph(int V, int E, int seed) {
    GraphType g(V);
    mt19937 rng(seed);
    uniform_int_distribution<int> dist(0, V - 1);

    if (V > 0) {
        for (int i = 0; i < E; ++i) {
            g.AddEdge(dist(rng), dist(rng));
        }
    }
    return g;
}

size_t hash_vector_of_pairs(const vector<pair<int, int>>& vec) {
    size_t seed = vec.size();
    for (const auto& p : vec) {
        seed ^= (static_cast<size_t>(p.first) << 32) ^ static_cast<size_t>(p.second) + 0x9e3779b9 + (seed << 6) + (seed >> 2);
    }
    return seed;
}

// --- Test Case Runner ---

struct TestResult {
    string message;
    bool passed;
    double duration_seq = 0.0;
    double duration_par = 0.0;
    size_t hash_seq = 0;
    size_t hash_par1 = 0;
    size_t hash_par2 = 0;
};

TestResult run_test(int V, int E, int seed, int num_threads) {
    auto g_seq = create_random_graph<GraphSequential>(V, E, seed);
    auto g_par = create_random_graph<GraphParallel>(V, E, seed);
    g_par.SetNumThreads(num_threads);

    auto start_seq = chrono::high_resolution_clock::now();
    auto result_seq = g_seq.ReduceEdges();
    auto end_seq = chrono::high_resolution_clock::now();
    chrono::duration<double> diff_seq = end_seq - start_seq;

    auto start_par1 = chrono::high_resolution_clock::now();
    auto result_par1 = g_par.ReduceEdges();
    auto end_par1 = chrono::high_resolution_clock::now();
    chrono::duration<double> diff_par1 = end_par1 - start_par1;
    
    auto start_par2 = chrono::high_resolution_clock::now();
    auto result_par2 = g_par.ReduceEdges();
    auto end_par2 = chrono::high_resolution_clock::now();

    size_t hash_seq = hash_vector_of_pairs(result_seq);
    size_t hash_par1 = hash_vector_of_pairs(result_par1);
    size_t hash_par2 = hash_vector_of_pairs(result_par2);

    if (result_seq != result_par1) {
        return {"Correctness failed: Sequential and Parallel results differ.", false, diff_seq.count(), diff_par1.count(), hash_seq, hash_par1, hash_par2};
    }
    if (hash_par1 != hash_par2) {
        return {"Determinism failed: Two parallel runs produced different results.", false, diff_seq.count(), diff_par1.count(), hash_seq, hash_par1, hash_par2};
    }

    return {"Correctness and determinism checks passed.", true, diff_seq.count(), diff_par1.count(), hash_seq, hash_par1, hash_par2};
}

// --- Main Test Driver ---

void print_header() {
    cout << left << setw(15) << "Test Case"
         << setw(10) << "Vertices"
         << setw(10) << "Edges"
         << setw(10) << "Result"
         << setw(15) << "Seq Time (s)"
         << setw(15) << "Par Time (s)"
         << setw(10) << "Speedup"
         << "Notes" << endl;
    cout << string(90, '-') << endl;
}

void print_result(const string& name, int V, int E, const TestResult& res) {
    cout << left << setw(15) << name
         << setw(10) << V
         << setw(10) << E
         << setw(10) << (res.passed ? "PASS" : "FAIL")
         << fixed << setprecision(6)
         << setw(15) << res.duration_seq
         << setw(15) << res.duration_par;

    if (res.passed && res.duration_seq > 0.000001) {
        cout << setw(10) << fixed << setprecision(2) << (res.duration_seq / res.duration_par) << "x";
    } else {
        cout << setw(10) << "N/A";
    }
    
    if (!res.passed) {
        cout << res.message;
    }
    cout << endl;
}


int main(int argc, char* argv[]) {
    mkdir("evidence", 0755);
    ofstream summary_file("evidence/run_summary.txt");
    ofstream perf_file("evidence/perf.txt");

    int num_threads = thread::hardware_concurrency();
    if (num_threads == 0) num_threads = 4;

    cout << "Running tests with " << num_threads << " threads." << endl;
    summary_file << "Running tests with " << num_threads << " threads." << endl;

    print_header();

    vector<tuple<string, int, int>> test_cases = {
        {"Empty", 0, 0},
        {"Single Node", 1, 0},
        {"Small", 100, 500},
        {"Medium", 2000, 20000},
        {"Large", 10000, 150000},
        {"Skewed", 5000, 5000}
    };

    bool all_passed = true;

    for (const auto& test : test_cases) {
        string name = get<0>(test);
        int V = get<1>(test);
        int E = get<2>(test);
        
        TestResult res = run_test(V, E, 42, num_threads);
        print_result(name, V, E, res);

        summary_file << "Test Case: " << name << " (V=" << V << ", E=" << E << ")\n";
        summary_file << "  Status: " << (res.passed ? "PASS" : "FAIL") << "\n";
        if (!res.passed) {
            summary_file << "  Reason: " << res.message << "\n";
            all_passed = false;
        }
        summary_file << "  Sequential Hash: " << res.hash_seq << "\n";
        summary_file << "  Parallel Hash 1: " << res.hash_par1 << "\n";
        summary_file << "  Parallel Hash 2: " << res.hash_par2 << "\n";
        summary_file << "  Sequential Time: " << res.duration_seq << "s\n";
        summary_file << "  Parallel Time:   " << res.duration_par << "s\n\n";

        if (name == "Large") {
             perf_file << "Large Test Case Performance\n";
             perf_file << "  Num Cores: " << num_threads << "\n";
             perf_file << "  Sequential Time (s): " << res.duration_seq << "\n";
             perf_file << "  Parallel Time (s):   " << res.duration_par << "\n";
             if (res.duration_par > 0) {
                 perf_file << "  Speedup: " << (res.duration_seq / res.duration_par) << "x\n";
             }
        }
    }

    summary_file.close();
    perf_file.close();

    if (!all_passed) {
        cerr << "\nSome tests failed." << endl;
        return 1;
    }

    cout << "\nAll tests passed successfully." << endl;
    return 0;
}
