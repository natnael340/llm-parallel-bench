#include "smith_waterman.h"
#include <iostream>
#include <iomanip>
#include <chrono>
#include <string>
#include <random>

std::string generateRandomDNA(int length, unsigned seed) {
    std::mt19937 gen(seed);
    std::uniform_int_distribution<> dis(0, 3);
    const char bases[] = {'A', 'C', 'G', 'T'};
    
    std::string result;
    result.reserve(length);
    for (int i = 0; i < length; i++) {
        result += bases[dis(gen)];
    }
    return result;
}

int main() {
    SmithWaterman sw(2, -1, -1);
    
    // Test sizes
    struct BenchCase {
        int size;
        std::string name;
    };
    
    std::vector<BenchCase> cases = {
        {100, "Small"},
        {500, "Medium"},
        {1000, "Large"},
        {2000, "XLarge"}
    };
    
    std::cout << "=== Smith-Waterman Performance Benchmark ===" << std::endl;
    std::cout << std::endl;
    
    for (const auto& bc : cases) {
        std::string query = generateRandomDNA(bc.size, 42);
        std::string reference = generateRandomDNA(bc.size, 123);
        
        std::cout << bc.name << " (" << bc.size << " x " << bc.size << "): ";
        std::cout.flush();
        
        // Warmup
        auto result = sw.findAlignment(query, reference);
        
        // Timed run
        auto start = std::chrono::high_resolution_clock::now();
        result = sw.findAlignment(query, reference);
        auto end = std::chrono::high_resolution_clock::now();
        
        double duration = std::chrono::duration<double>(end - start).count();
        
        std::cout << std::fixed << std::setprecision(4) << duration << " sec";
        std::cout << " (score=" << std::get<2>(result) << ")" << std::endl;
    }
    
    return 0;
}
