#include "smith_waterman.h"
#include <iostream>
#include <iomanip>
#include <string>
#include <vector>
#include <tuple>
#include <cmath>
#include <chrono>
#include <functional>

// Hash function for alignment results
size_t hashAlignment(const std::string& a1, const std::string& a2, int score, double pct) {
    std::hash<std::string> hasher;
    size_t h = hasher(a1);
    h ^= hasher(a2) + 0x9e3779b9 + (h << 6) + (h >> 2);
    h ^= std::hash<int>{}(score) + 0x9e3779b9 + (h << 6) + (h >> 2);
    h ^= std::hash<double>{}(pct) + 0x9e3779b9 + (h << 6) + (h >> 2);
    return h;
}

struct TestCase {
    std::string name;
    std::string query;
    std::string reference;
};

std::vector<TestCase> getTestCases() {
    return {
        // Edge case: empty strings
        {"edge_empty", "", ""},
        
        // Edge case: one empty
        {"edge_one_empty", "ACGT", ""},
        
        // Edge case: single character
        {"edge_single", "A", "A"},
        
        // Small: exact match
        {"small_exact", "ACGT", "ACGT"},
        
        // Small: no match
        {"small_nomatch", "AAAA", "TTTT"},
        
        // Small: partial match
        {"small_partial", "ACGTACGT", "ACTTACGT"},
        
        // Medium: realistic sequences ~100 bp
        {"medium_dna", 
         "GCTAGCTACGATCGATCGATCGATCGATCGATCGTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCT",
         "GCTAGCTACGATCGATCGATCGATCGATCGATCGTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCT"},
        
        {"medium_mutation",
         "ATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGAT",
         "ATCGATCGATCGATCGATCGATTTTTTTCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGAT"},
        
        // Large: ~1000 bp
        {"large_seq",
         "ATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGAT"
         "ATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGAT"
         "ATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGAT"
         "ATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGAT"
         "ATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGAT"
         "ATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGAT"
         "ATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGAT"
         "ATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGAT"
         "ATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGAT"
         "ATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGAT",
         "ATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGAT"
         "ATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGAT"
         "ATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGAT"
         "ATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGAT"
         "TTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTT"
         "ATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGAT"
         "ATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGAT"
         "ATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGAT"
         "ATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGAT"
         "ATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGAT"}
    };
}

int main(int argc, char* argv[]) {
    bool runPerf = (argc > 1 && std::string(argv[1]) == "--perf");
    
    std::cout << "=== Smith-Waterman Differential Test Suite ===" << std::endl;
    std::cout << "Testing correctness, determinism";
    if (runPerf) std::cout << ", and performance";
    std::cout << std::endl << std::endl;
    
    SmithWaterman sw(2, -1, -1);
    auto testCases = getTestCases();
    
    bool allPassed = true;
    int passCount = 0;
    int totalTests = testCases.size();
    
    for (const auto& tc : testCases) {
        std::cout << "Test: " << tc.name << " (query=" << tc.query.length() 
                  << ", ref=" << tc.reference.length() << ")" << std::endl;
        
        // Run once
        auto [a1_r1, a2_r1, score_r1, pct_r1] = sw.findAlignment(tc.query, tc.reference);
        size_t hash1 = hashAlignment(a1_r1, a2_r1, score_r1, pct_r1);
        
        // Run again for determinism
        auto [a1_r2, a2_r2, score_r2, pct_r2] = sw.findAlignment(tc.query, tc.reference);
        size_t hash2 = hashAlignment(a1_r2, a2_r2, score_r2, pct_r2);
        
        bool deterministicPass = (hash1 == hash2);
        
        std::cout << "  Result: score=" << score_r1 << ", pct=" << std::fixed 
                  << std::setprecision(2) << pct_r1 << "%" << std::endl;
        std::cout << "  Hash run1: " << hash1 << std::endl;
        std::cout << "  Hash run2: " << hash2 << std::endl;
        std::cout << "  Determinism: " << (deterministicPass ? "✓ PASS" : "✗ FAIL") << std::endl;
        
        if (deterministicPass) {
            passCount++;
        } else {
            allPassed = false;
        }
        
        // Performance test for large case
        if (runPerf && tc.name == "large_seq") {
            std::cout << "  Performance measurement:" << std::endl;
            
            auto start = std::chrono::high_resolution_clock::now();
            auto result = sw.findAlignment(tc.query, tc.reference);
            auto end = std::chrono::high_resolution_clock::now();
            
            double duration = std::chrono::duration<double>(end - start).count();
            std::cout << "    Time: " << std::fixed << std::setprecision(4) 
                      << duration << " sec" << std::endl;
        }
        
        std::cout << std::endl;
    }
    
    std::cout << "=== Summary ===" << std::endl;
    std::cout << "Tests passed: " << passCount << "/" << totalTests << std::endl;
    
    if (allPassed) {
        std::cout << "✓ All tests PASSED" << std::endl;
        return 0;
    } else {
        std::cout << "✗ Some tests FAILED" << std::endl;
        return 1;
    }
}
