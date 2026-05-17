#include "bfs_seq.hpp"
#include "bfs_parallel.hpp"
#include "graph.h"
#include <iostream>
#include <chrono>
#include <iomanip>
#include <fstream>
#include <omp.h>

Graph create_grid_graph(int n) {
    Graph g;
    for (int i = 0; i < n; i++) {
        for (int j = 0; j < n; j++) {
            int v = i * n + j;
            if (j < n - 1) g.add_edge(v, v + 1);
            if (i < n - 1) g.add_edge(v, v + n);
        }
    }
    return g;
}

int main() {
    std::cout << "=== BFS Performance Benchmark ===" << std::endl;
    std::cout << "Threads available: " << omp_get_max_threads() << std::endl << std::endl;
    
    std::ofstream perf_file("perf.txt");
    perf_file << "BFS Performance Results\n";
    perf_file << "=======================\n";
    perf_file << "Threads: " << omp_get_max_threads() << "\n\n";
    
    // Test 1: 200x200 grid
    {
        std::cout << "Test 1: Grid 200x200 (40,000 vertices)" << std::endl;
        Graph g = create_grid_graph(200);
        int start = 20100;  // center
        
        // Warm-up
        bfs(g, start);
        bfs_parallel(g, start);
        
        // Sequential timing
        auto t1 = std::chrono::high_resolution_clock::now();
        auto seq_result = bfs(g, start);
        auto t2 = std::chrono::high_resolution_clock::now();
        double seq_time = std::chrono::duration<double, std::milli>(t2 - t1).count();
        
        // Parallel timing
        auto t3 = std::chrono::high_resolution_clock::now();
        auto par_result = bfs_parallel(g, start);
        auto t4 = std::chrono::high_resolution_clock::now();
        double par_time = std::chrono::duration<double, std::milli>(t4 - t3).count();
        
        double speedup = seq_time / par_time;
        double efficiency = speedup / omp_get_max_threads() * 100;
        
        std::cout << "  Sequential: " << std::fixed << std::setprecision(2) << seq_time << " ms" << std::endl;
        std::cout << "  Parallel:   " << par_time << " ms" << std::endl;
        std::cout << "  Speedup:    " << std::setprecision(2) << speedup << "x" << std::endl;
        std::cout << "  Efficiency: " << std::setprecision(1) << efficiency << "%" << std::endl;
        std::cout << "  Correctness: " << (seq_result == par_result ? "PASS" : "FAIL") << std::endl;
        std::cout << std::endl;
        
        perf_file << "Grid 200x200 (40,000 vertices)\n";
        perf_file << "  Sequential: " << std::fixed << std::setprecision(2) << seq_time << " ms\n";
        perf_file << "  Parallel:   " << par_time << " ms\n";
        perf_file << "  Speedup:    " << speedup << "x\n";
        perf_file << "  Efficiency: " << std::setprecision(1) << efficiency << "%\n\n";
    }
    
    // Test 2: 300x300 grid
    {
        std::cout << "Test 2: Grid 300x300 (90,000 vertices)" << std::endl;
        Graph g = create_grid_graph(300);
        int start = 45150;  // center
        
        // Warm-up
        bfs(g, start);
        bfs_parallel(g, start);
        
        // Sequential timing
        auto t1 = std::chrono::high_resolution_clock::now();
        auto seq_result = bfs(g, start);
        auto t2 = std::chrono::high_resolution_clock::now();
        double seq_time = std::chrono::duration<double, std::milli>(t2 - t1).count();
        
        // Parallel timing
        auto t3 = std::chrono::high_resolution_clock::now();
        auto par_result = bfs_parallel(g, start);
        auto t4 = std::chrono::high_resolution_clock::now();
        double par_time = std::chrono::duration<double, std::milli>(t4 - t3).count();
        
        double speedup = seq_time / par_time;
        double efficiency = speedup / omp_get_max_threads() * 100;
        
        std::cout << "  Sequential: " << std::fixed << std::setprecision(2) << seq_time << " ms" << std::endl;
        std::cout << "  Parallel:   " << par_time << " ms" << std::endl;
        std::cout << "  Speedup:    " << std::setprecision(2) << speedup << "x" << std::endl;
        std::cout << "  Efficiency: " << std::setprecision(1) << efficiency << "%" << std::endl;
        std::cout << "  Correctness: " << (seq_result == par_result ? "PASS" : "FAIL") << std::endl;
        std::cout << std::endl;
        
        perf_file << "Grid 300x300 (90,000 vertices)\n";
        perf_file << "  Sequential: " << std::fixed << std::setprecision(2) << seq_time << " ms\n";
        perf_file << "  Parallel:   " << par_time << " ms\n";
        perf_file << "  Speedup:    " << speedup << "x\n";
        perf_file << "  Efficiency: " << std::setprecision(1) << efficiency << "%\n\n";
    }
    
    perf_file.close();
    
    std::cout << "Results written to perf.txt" << std::endl;
    
    return 0;
}
