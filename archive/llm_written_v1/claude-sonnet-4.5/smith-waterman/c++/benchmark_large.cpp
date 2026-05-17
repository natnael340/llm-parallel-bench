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
    
    // Test size that exceeds 5M threshold: 3000x3000 = 9M
    int size = 3000;
    
    std::cout << "=== Smith-Waterman Large Performance Test ===" << std::endl;
    std::cout << "Matrix size: " << size << " x " << size << " = " 
              << (size * size / 1000000.0) << "M cells" << std::endl;
    std::cout << std::endl;
    
    std::string query = generateRandomDNA(size, 42);
    std::string reference = generateRandomDNA(size, 123);
    
    std::cout << "Running alignment..." << std::endl;
    
    // Warmup
    auto result = sw.findAlignment(query, reference);
    
    // Timed runs
    const int numRuns = 3;
    double totalTime = 0.0;
    
    for (int run = 0; run < numRuns; run++) {
        auto start = std::chrono::high_resolution_clock::now();
        result = sw.findAlignment(query, reference);
        auto end = std::chrono::high_resolution_clock::now();
        
        double duration = std::chrono::duration<double>(end - start).count();
        totalTime += duration;
        
        std::cout << "Run " << (run + 1) << ": " << std::fixed << std::setprecision(4) 
                  << duration << " sec" << std::endl;
    }
    
    double avgTime = totalTime / numRuns;
    std::cout << std::endl;
    std::cout << "Average: " << std::fixed << std::setprecision(4) << avgTime << " sec" << std::endl;
    std::cout << "Score: " << std::get<2>(result) << std::endl;
    std::cout << "Identity: " << std::fixed << std::setprecision(2) 
              << std::get<3>(result) << "%" << std::endl;
    
    return 0;
}
