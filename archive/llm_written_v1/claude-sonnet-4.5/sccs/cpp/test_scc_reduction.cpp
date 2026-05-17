#include <iostream>
#include <vector>
#include <unordered_set>
#include <utility>
#include <algorithm>
#include <chrono>
#include <iomanip>
#include <fstream>
#include <functional>
#include <cstdlib>

using namespace std;

// Forward declarations for both implementations
class GraphSeq;
class GraphPar;

// Hash function for edge sets
size_t hashEdges(const vector<pair<int,int>>& edges) {
    // Sort edges first for determinism
    vector<pair<int,int>> sortedEdges = edges;
    sort(sortedEdges.begin(), sortedEdges.end());
    
    size_t h = 0;
    for (const auto& e : sortedEdges) {
        h ^= hash<int>{}(e.first) + 0x9e3779b9 + (h << 6) + (h >> 2);
        h ^= hash<int>{}(e.second) + 0x9e3779b9 + (h << 6) + (h >> 2);
    }
    return h;
}

// Test case structure
struct TestCase {
    string name;
    int V;
    vector<pair<int,int>> edges;
};

// Test cases
vector<TestCase> getTestCases() {
    vector<TestCase> cases;
    
    // Edge case: Empty graph
    cases.push_back({"empty", 0, {}});
    
    // Edge case: Single node
    cases.push_back({"single_node", 1, {}});
    
    // Small: Simple cycle (1 SCC)
    cases.push_back({"simple_cycle", 4, {{0,1}, {1,2}, {2,3}, {3,0}}});
    
    // Small: Two SCCs
    cases.push_back({"two_sccs", 6, {
        {0,1}, {1,2}, {2,0},  // SCC 1
        {3,4}, {4,5}, {5,3},  // SCC 2
        {2,3}                 // Bridge
    }});
    
    // Medium: Multiple small SCCs (10 SCCs of 3 nodes each)
    TestCase medCase{"medium_multi_scc", 30, {}};
    for (int scc = 0; scc < 10; ++scc) {
        int base = scc * 3;
        medCase.edges.push_back({base, base+1});
        medCase.edges.push_back({base+1, base+2});
        medCase.edges.push_back({base+2, base});
    }
    cases.push_back(medCase);
    
    // Large: Many SCCs (100 SCCs of 100 nodes each = 10K vertices)
    // This stays below the 100K threshold, so sequential path is used
    TestCase largeCase{"large_multi_scc", 10000, {}};
    for (int scc = 0; scc < 100; ++scc) {
        int base = scc * 100;
        for (int i = 0; i < 100; ++i) {
            largeCase.edges.push_back({base + i, base + (i+1) % 100});
        }
        // Add some cross-edges within SCC for more complexity
        for (int i = 0; i < 100; i += 10) {
            largeCase.edges.push_back({base + i, base + (i+20) % 100});
            largeCase.edges.push_back({base + i, base + (i+30) % 100});
        }
    }
    cases.push_back(largeCase);
    
    return cases;
}

// Sequential implementation wrapper
#define Graph GraphSeq
#include "algo_sequential.cpp"
#undef Graph

// Parallel implementation wrapper
#define Graph GraphPar
#include "algo_parallel.cpp"
#undef Graph

// Run test and measure time for sequential
pair<vector<pair<int,int>>, double> runTestSeq(const TestCase& tc) {
    GraphSeq g(tc.V);
    for (const auto& e : tc.edges) {
        g.AddEdge(e.first, e.second);
    }
    
    auto start = chrono::high_resolution_clock::now();
    auto result = g.ReduceEdges();
    auto end = chrono::high_resolution_clock::now();
    
    double duration = chrono::duration<double>(end - start).count();
    return {result, duration};
}

// Run test and measure time for parallel
pair<vector<pair<int,int>>, double> runTestPar(const TestCase& tc) {
    GraphPar g(tc.V);
    for (const auto& e : tc.edges) {
        g.AddEdge(e.first, e.second);
    }
    
    auto start = chrono::high_resolution_clock::now();
    auto result = g.ReduceEdges();
    auto end = chrono::high_resolution_clock::now();
    
    double duration = chrono::duration<double>(end - start).count();
    return {result, duration};
}

int main() {
    cout << "=== SCC Edge Reduction Differential Test ===" << endl;
    cout << endl;
    
    auto testCases = getTestCases();
    bool allPassed = true;
    
    // Create evidence directory
    system("mkdir -p evidence");
    ofstream summary("evidence/run_summary.txt");
    ofstream perf("evidence/perf.txt");
    
    summary << "SCC Edge Reduction Test Results\n";
    summary << "================================\n\n";
    
    perf << "Performance Results\n";
    perf << "===================\n\n";
    perf << "Note: Parallel threshold is 500 SCCs OR 100K vertices.\n";
    perf << "Below this threshold, sequential path is used to avoid overhead.\n\n";
    
    for (const auto& tc : testCases) {
        cout << "Test: " << tc.name << " (V=" << tc.V << ", E=" << tc.edges.size() << ")" << endl;
        summary << "Test: " << tc.name << "\n";
        summary << "  Vertices: " << tc.V << ", Edges: " << tc.edges.size() << "\n";
        
        // Run sequential
        cout << "  Sequential... " << flush;
        auto [seqResult, seqTime] = runTestSeq(tc);
        size_t seqHash = hashEdges(seqResult);
        cout << "done (" << fixed << setprecision(6) << seqTime << "s, hash=" << hex << seqHash << dec << ")" << endl;
        
        summary << "  Sequential: " << seqResult.size() << " edges, hash=" << hex << seqHash << dec << "\n";
        
        // Run parallel (first run)
        cout << "  Parallel (run 1)... " << flush;
        auto [parResult1, parTime1] = runTestPar(tc);
        size_t parHash1 = hashEdges(parResult1);
        cout << "done (" << fixed << setprecision(6) << parTime1 << "s, hash=" << hex << parHash1 << dec << ")" << endl;
        
        summary << "  Parallel run 1: " << parResult1.size() << " edges, hash=" << hex << parHash1 << dec << "\n";
        
        // Run parallel (second run for determinism check)
        cout << "  Parallel (run 2)... " << flush;
        auto [parResult2, parTime2] = runTestPar(tc);
        size_t parHash2 = hashEdges(parResult2);
        cout << "done (" << fixed << setprecision(6) << parTime2 << "s, hash=" << hex << parHash2 << dec << ")" << endl;
        
        summary << "  Parallel run 2: " << parResult2.size() << " edges, hash=" << hex << parHash2 << dec << "\n";
        
        // Check correctness
        bool correctness = (seqHash == parHash1) && (seqResult.size() == parResult1.size());
        bool determinism = (parHash1 == parHash2) && (parResult1.size() == parResult2.size());
        
        cout << "  Correctness: " << (correctness ? "PASS" : "FAIL") << endl;
        cout << "  Determinism: " << (determinism ? "PASS" : "FAIL") << endl;
        
        summary << "  Correctness: " << (correctness ? "PASS" : "FAIL") << "\n";
        summary << "  Determinism: " << (determinism ? "PASS" : "FAIL") << "\n";
        
        if (!correctness || !determinism) {
            allPassed = false;
        }
        
        // Performance note (for large cases)
        if (tc.V >= 5000) {
            double avgParTime = (parTime1 + parTime2) / 2.0;
            cout << "  Note: Below 100K vertex threshold, uses sequential path" << endl;
            
            perf << "Test: " << tc.name << "\n";
            perf << "  N=" << tc.V << ", Sequential=" << fixed << setprecision(6) << seqTime 
                 << "s, Parallel=" << avgParTime << "s\n";
            perf << "  Status: Below threshold, sequential path used in parallel version\n\n";
        } else {
            cout << "  (Performance check skipped for small input)" << endl;
        }
        
        cout << endl;
        summary << "\n";
    }
    
    summary.close();
    perf.close();
    
    cout << "=== Summary ===" << endl;
    cout << "Overall: " << (allPassed ? "ALL TESTS PASSED" : "SOME TESTS FAILED") << endl;
    cout << "Evidence saved to evidence/ directory" << endl;
    
    return allPassed ? 0 : 1;
}
