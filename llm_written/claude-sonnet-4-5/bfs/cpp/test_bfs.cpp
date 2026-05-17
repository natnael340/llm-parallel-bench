#include "bfs_seq.hpp"
#include "bfs_parallel.hpp"
#include "graph.h"
#include <iostream>
#include <vector>
#include <string>
#include <chrono>
#include <fstream>
#include <sstream>
#include <iomanip>
#include <cstring>
#include <algorithm>
#include <omp.h>

// Simple hash function for vector<int>
size_t hash_vector(const std::vector<int>& vec) {
    size_t hash = vec.size();
    for (int v : vec) {
        hash ^= std::hash<int>{}(v) + 0x9e3779b9 + (hash << 6) + (hash >> 2);
    }
    return hash;
}

// Convert hash to hex string
std::string hash_to_hex(size_t hash) {
    std::stringstream ss;
    ss << std::hex << std::setfill('0') << std::setw(16) << hash;
    return ss.str();
}

// Test result structure
struct TestResult {
    std::string name;
    bool correctness_pass;
    bool determinism_pass;
    std::vector<size_t> hashes;
    int size;
    std::string error_msg;
};

// Create a line graph: 0-1-2-3-...-n
Graph create_line_graph(int n) {
    Graph g;
    for (int i = 0; i < n - 1; i++) {
        g.add_edge(i, i + 1);
    }
    return g;
}

// Create a grid graph: n x n grid
Graph create_grid_graph(int n) {
    Graph g;
    for (int i = 0; i < n; i++) {
        for (int j = 0; j < n; j++) {
            int v = i * n + j;
            if (j < n - 1) g.add_edge(v, v + 1);  // right
            if (i < n - 1) g.add_edge(v, v + n);  // down
        }
    }
    return g;
}

// Create a star graph: center connected to n spokes
Graph create_star_graph(int n) {
    Graph g;
    for (int i = 1; i <= n; i++) {
        g.add_edge(0, i);
    }
    return g;
}

// Create a complete graph: all vertices connected
Graph create_complete_graph(int n) {
    Graph g;
    for (int i = 0; i < n; i++) {
        for (int j = i + 1; j < n; j++) {
            g.add_edge(i, j);
        }
    }
    return g;
}

// Run a single test case
TestResult run_test(const std::string& name, Graph& g, int start, int num_runs = 3) {
    TestResult result;
    result.name = name;
    result.size = g.vertices.size();
    result.correctness_pass = false;
    result.determinism_pass = false;
    
    // Run sequential baseline
    std::vector<int> seq_result;
    try {
        seq_result = bfs(g, start);
    } catch (const std::exception& e) {
        result.error_msg = std::string("Sequential failed: ") + e.what();
        return result;
    }
    
    size_t seq_hash = hash_vector(seq_result);
    
    // Run parallel version multiple times
    std::vector<std::vector<int>> par_results;
    for (int run = 0; run < num_runs; run++) {
        try {
            std::vector<int> par_result = bfs_parallel(g, start);
            par_results.push_back(par_result);
            result.hashes.push_back(hash_vector(par_result));
        } catch (const std::exception& e) {
            result.error_msg = std::string("Parallel run ") + std::to_string(run) + " failed: " + e.what();
            return result;
        }
    }
    
    // Check correctness: first parallel run should match sequential
    result.correctness_pass = (par_results[0] == seq_result);
    
    if (!result.correctness_pass) {
        result.error_msg = "Output mismatch. Seq size: " + std::to_string(seq_result.size()) + 
                          ", Par size: " + std::to_string(par_results[0].size());
        return result;
    }
    
    // Check determinism: all parallel runs should produce identical results
    result.determinism_pass = true;
    for (size_t i = 1; i < par_results.size(); i++) {
        if (par_results[i] != par_results[0]) {
            result.determinism_pass = false;
            result.error_msg = "Determinism failure: run 0 vs run " + std::to_string(i);
            break;
        }
    }
    
    return result;
}

// Performance benchmark
struct PerfResult {
    std::string name;
    int size;
    double seq_time_ms;
    double par_time_ms;
    double speedup;
    int num_threads;
};

PerfResult run_perf_test(const std::string& name, Graph& g, int start) {
    PerfResult result;
    result.name = name;
    result.size = g.vertices.size();
    result.num_threads = omp_get_max_threads();
    
    // Warm-up
    bfs(g, start);
    bfs_parallel(g, start);
    
    // Sequential timing (3 runs, take median)
    std::vector<double> seq_times;
    for (int i = 0; i < 3; i++) {
        auto start_time = std::chrono::high_resolution_clock::now();
        bfs(g, start);
        auto end_time = std::chrono::high_resolution_clock::now();
        seq_times.push_back(std::chrono::duration<double, std::milli>(end_time - start_time).count());
    }
    std::sort(seq_times.begin(), seq_times.end());
    result.seq_time_ms = seq_times[1];
    
    // Parallel timing (3 runs, take median)
    std::vector<double> par_times;
    for (int i = 0; i < 3; i++) {
        auto start_time = std::chrono::high_resolution_clock::now();
        bfs_parallel(g, start);
        auto end_time = std::chrono::high_resolution_clock::now();
        par_times.push_back(std::chrono::duration<double, std::milli>(end_time - start_time).count());
    }
    std::sort(par_times.begin(), par_times.end());
    result.par_time_ms = par_times[1];
    
    result.speedup = result.seq_time_ms / result.par_time_ms;
    
    return result;
}

int main(int argc, char* argv[]) {
    bool run_perf = false;
    if (argc > 1 && std::strcmp(argv[1], "--perf") == 0) {
        run_perf = true;
    }
    
    std::vector<TestResult> test_results;
    
    std::cout << "=== BFS Differential Testing ===" << std::endl;
    std::cout << "Running correctness and determinism tests..." << std::endl << std::endl;
    
    // Edge cases
    {
        Graph empty_g;
        test_results.push_back(run_test("Empty graph", empty_g, 0));
    }
    
    {
        Graph single_g;
        single_g.vertices[0] = {};
        test_results.push_back(run_test("Single vertex", single_g, 0));
    }
    
    {
        Graph g = create_line_graph(5);
        test_results.push_back(run_test("Start not in graph", g, 99));
    }
    
    // Small graphs
    {
        Graph g = create_line_graph(10);
        test_results.push_back(run_test("Line graph (10)", g, 0));
    }
    
    {
        Graph g = create_star_graph(20);
        test_results.push_back(run_test("Star graph (20)", g, 0));
    }
    
    {
        Graph g = create_complete_graph(15);
        test_results.push_back(run_test("Complete graph (15)", g, 0));
    }
    
    // Medium graphs
    {
        Graph g = create_grid_graph(30);  // 900 vertices
        test_results.push_back(run_test("Grid 30x30 (900)", g, 0));
    }
    
    {
        Graph g = create_line_graph(1000);
        test_results.push_back(run_test("Line graph (1000)", g, 0));
    }
    
    {
        Graph g = create_star_graph(5000);
        test_results.push_back(run_test("Star graph (5000)", g, 0));
    }
    
    // Large graphs
    {
        Graph g = create_grid_graph(100);  // 10,000 vertices
        test_results.push_back(run_test("Grid 100x100 (10k)", g, 5050));  // center
    }
    
    {
        Graph g = create_grid_graph(200);  // 40,000 vertices
        test_results.push_back(run_test("Grid 200x200 (40k)", g, 20100));  // center
    }
    
    // Print results
    int passed = 0;
    int failed = 0;
    
    for (const auto& test : test_results) {
        bool pass = test.correctness_pass && test.determinism_pass;
        std::cout << "[" << (pass ? "PASS" : "FAIL") << "] " << test.name 
                  << " (n=" << test.size << ")" << std::endl;
        
        if (!pass) {
            std::cout << "  Error: " << test.error_msg << std::endl;
            failed++;
        } else {
            std::cout << "  Correctness: ✓  Determinism: ✓" << std::endl;
            if (!test.hashes.empty()) {
                std::cout << "  Hash: " << hash_to_hex(test.hashes[0]) << std::endl;
            }
            passed++;
        }
        std::cout << std::endl;
    }
    
    std::cout << "=== Summary ===" << std::endl;
    std::cout << "Passed: " << passed << "/" << (passed + failed) << std::endl;
    std::cout << "Failed: " << failed << "/" << (passed + failed) << std::endl;
    
    // Write summary to file
    std::ofstream summary("run_summary.txt");
    summary << "BFS Differential Test Results\n";
    summary << "==============================\n\n";
    
    for (const auto& test : test_results) {
        bool pass = test.correctness_pass && test.determinism_pass;
        summary << "[" << (pass ? "PASS" : "FAIL") << "] " << test.name 
                << " (n=" << test.size << ")\n";
        
        if (!pass) {
            summary << "  Error: " << test.error_msg << "\n";
        } else {
            summary << "  Correctness: PASS\n";
            summary << "  Determinism: PASS (3 runs)\n";
            if (!test.hashes.empty()) {
                summary << "  Hashes:\n";
                for (size_t i = 0; i < test.hashes.size(); i++) {
                    summary << "    Run " << i << ": " << hash_to_hex(test.hashes[i]) << "\n";
                }
            }
        }
        summary << "\n";
    }
    
    summary << "Summary: " << passed << " passed, " << failed << " failed\n";
    summary.close();
    
    // Performance tests
    if (run_perf) {
        std::cout << "\n=== Performance Benchmarks ===" << std::endl;
        std::vector<PerfResult> perf_results;
        
        {
            Graph g = create_grid_graph(200);
            perf_results.push_back(run_perf_test("Grid 200x200", g, 20100));
        }
        
        {
            Graph g = create_grid_graph(300);
            perf_results.push_back(run_perf_test("Grid 300x300", g, 45150));
        }
        
        std::ofstream perf_file("perf.txt");
        perf_file << "BFS Performance Results\n";
        perf_file << "=======================\n\n";
        
        for (const auto& perf : perf_results) {
            std::cout << perf.name << " (n=" << perf.size << ")" << std::endl;
            std::cout << "  Sequential: " << std::fixed << std::setprecision(2) 
                     << perf.seq_time_ms << " ms" << std::endl;
            std::cout << "  Parallel (" << perf.num_threads << " threads): " 
                     << perf.par_time_ms << " ms" << std::endl;
            std::cout << "  Speedup: " << std::setprecision(2) << perf.speedup << "x" << std::endl;
            std::cout << "  Efficiency: " << std::setprecision(1) 
                     << (perf.speedup / perf.num_threads * 100) << "%" << std::endl;
            std::cout << std::endl;
            
            perf_file << perf.name << " (n=" << perf.size << ")\n";
            perf_file << "  Sequential: " << std::fixed << std::setprecision(2) 
                     << perf.seq_time_ms << " ms\n";
            perf_file << "  Parallel (" << perf.num_threads << " threads): " 
                     << perf.par_time_ms << " ms\n";
            perf_file << "  Speedup: " << std::setprecision(2) << perf.speedup << "x\n";
            perf_file << "  Efficiency: " << std::setprecision(1) 
                     << (perf.speedup / perf.num_threads * 100) << "%\n\n";
        }
        
        perf_file.close();
    }
    
    return (failed > 0) ? 1 : 0;
}
