#include <iostream>
#include <vector>
#include <random>
#include <cassert>
#include "graph.h"
#include "bfs_seq.hpp"
#include "bfs_parallel.hpp"

// Utility to print a vector
void print_vector(const std::string& name, const std::vector<int>& vec) {
    std::cout << name << ": ";
    for (int v : vec) {
        std::cout << v << " ";
    }
    std::cout << std::endl;
}

// Utility to compare two vectors
bool compare_vectors(const std::vector<int>& v1, const std::vector<int>& v2) {
    return v1 == v2;
}

void test_graph(Graph& g, int start_node, const std::string& test_name) {
    std::cout << "--- Running test: " << test_name << " ---" << std::endl;

    // Run sequential version
    std::vector<int> seq_result = bfs(g, start_node);

    // Run parallel version first time
    std::vector<int> parallel_result1 = bfs_parallel(g, start_node);

    // Run parallel version second time to check for determinism
    std::vector<int> parallel_result2 = bfs_parallel(g, start_node);

    bool correct = compare_vectors(seq_result, parallel_result1);
    bool deterministic = compare_vectors(parallel_result1, parallel_result2);

    if (correct && deterministic) {
        std::cout << "PASS" << std::endl;
    } else {
        std::cout << "FAIL" << std::endl;
        if (!correct) {
            std::cout << "Mismatch between sequential and parallel results." << std::endl;
            print_vector("Sequential", seq_result);
            print_vector("Parallel  ", parallel_result1);
        }
        if (!deterministic) {
            std::cout << "Parallel implementation is not deterministic." << std::endl;
            print_vector("Parallel Run 1", parallel_result1);
            print_vector("Parallel Run 2", parallel_result2);
        }
    }
    assert(correct && deterministic);
    std::cout << "--------------------------------------" << std::endl << std::endl;
}

int main() {
    // Test 1: Empty graph
    Graph g1;
    test_graph(g1, 0, "Empty Graph");

    // Test 2: Single node graph
    Graph g2;
    g2.add_edge(0, 0); // Self-loop to create the vertex
    test_graph(g2, 0, "Single Node Graph");

    // Test 3: Simple linear graph (small enough for sequential fallback)
    Graph g3;
    for (int i = 0; i < 10; ++i) {
        g3.add_edge(i, i + 1);
    }
    test_graph(g3, 0, "Small Linear Graph (Sequential Fallback)");

    // Test 4: Larger graph that should trigger parallel execution
    Graph g4;
    int large_graph_size = 2000;
    std::mt19937 rng(42); // Fixed seed for reproducibility
    for (int i = 0; i < large_graph_size; ++i) {
        int u = std::uniform_int_distribution<int>(0, large_graph_size - 1)(rng);
        int v = std::uniform_int_distribution<int>(0, large_graph_size - 1)(rng);
        if (u != v) {
            g4.add_edge(u, v);
        }
    }
     if (g4.vertices.find(0) == g4.vertices.end()) {
        g4.add_edge(0, 0); // Ensure start node 0 exists
    }
    test_graph(g4, 0, "Large Random Graph");

    // Test 5: Star graph
    Graph g5;
    int star_size = 1500;
    for (int i = 1; i < star_size; ++i) {
        g5.add_edge(0, i);
    }
    test_graph(g5, 0, "Star Graph");
    
    // Test 6: Disconnected components
    Graph g6;
    for (int i = 0; i < 500; ++i) g6.add_edge(i, i + 1);
    for (int i = 600; i < 1000; ++i) g6.add_edge(i, i + 1);
    test_graph(g6, 0, "Disconnected Graph (start in first component)");
    test_graph(g6, 600, "Disconnected Graph (start in second component)");

    // Test 7: Non-existent start vertex
    Graph g7;
    g7.add_edge(1, 2);
    test_graph(g7, 99, "Non-existent Start Vertex");

    std::cout << "All tests completed." << std::endl;

    return 0;
}
