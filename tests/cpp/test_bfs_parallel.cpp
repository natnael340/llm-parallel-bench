#include <iostream>
#include "vector"
#include "math.h"
#include "chrono"
#include "../../llm_written/graph.h"
#include "../../llm_written/bfs_parallel.hpp"

using std::vector;


void assertEqual(vector<int>& result, const vector<int>& expected, std::string testName) {
    if (result == expected) {
        std::cout << testName << " passed" << std::endl;
    } else {
        std::cout << testName << " failed" << std::endl;
        std::cout <<"Expected: ";
        for(int v : expected) std::cout<< v << " ";
        std::cout << std::endl;
        std::cout<<"Got: ";
        for(int v : result) std::cout<< v << " ";
        std::cout << std::endl;
    }
}

void test_bfs_empty(){
    Graph g;
    vector<int> result = bfs_parallel(g, 1);

    assertEqual(result, {}, "test_bfs_empty");
}

void test_bfs_single_node(){
    Graph g;
    g.add_edge(1, 1);
    vector<int> result = bfs_parallel(g, 1);
    assertEqual(result, {1}, "test_bfs_single_node");
}

void test_bfs_linear_edge() {
    Graph g;
    g.add_edge(1, 2);
    g.add_edge(2, 3);
    g.add_edge(3, 4);

    vector<int> result = bfs_parallel(g, 1);
    assertEqual(result, {1, 2, 3, 4}, "test_bfs_linear_edge");
}

void test_bfs_complete_graph() {
    Graph g;
    vector<int> nodes = {1, 2, 3, 4};
    for (int i : nodes) {
        for (int j : nodes) {
            if (i != j) {
                g.add_edge(i, j);
            }
        }
    }
    vector<int> result = bfs_parallel(g, 3);
    assertEqual(result, {3, 1, 2, 4}, "test_bfs_complete_graph");
}

void test_bfs_star_graph() {
    Graph g;
    int center = 1;
    vector<int> leaves = {2, 3, 4, 5};
    for (int leaf : leaves) {
        g.add_edge(center, leaf);
    }
    vector<int> result = bfs_parallel(g, center);
    vector<int> expected = {center, 2, 3, 4, 5};
    assertEqual(result, expected, "test_bfs_star_graph");
}

void test_bfs_cycle() {
    Graph g;
    vector<vector<int>> edges = {{1, 2}, {2, 3}, {3, 4}, {4, 1}};
    for (vector<int> edge : edges) {
        
        g.add_edge(edge[0], edge[1]);
    }

    vector<int> result = bfs_parallel(g, 1);
    vector<int> expected = {1, 2, 4, 3};
    assertEqual(result, expected, "test_bfs_cycle");
}

void test_bfs_tree_structure() {
    Graph g;
    vector<std::pair<int, int>> edges = {{1, 2}, {1, 3}, {2, 4}, {2, 5}, {3, 6}, {3, 7}};
    for (auto& edge : edges) {
        g.add_edge(edge.first, edge.second);
    }
    vector<int> result = bfs_parallel(g, 1);
    vector<int> expected = {1, 2, 3, 4, 5, 6, 7};
    assertEqual(result, expected, "test_bfs_tree_structure");
}

void test_bfs_disconnected_components() {
    Graph g;
    // Component 1: 1-2-3
    g.add_edge(1, 2);
    g.add_edge(2, 3);
    // Component 2: 4-5, 4-6
    g.add_edge(4, 5);
    g.add_edge(4, 6);

    vector<int> result1 = bfs_parallel(g, 1);
    vector<int> expected1 = {1, 2, 3};
    assertEqual(result1, expected1, "test_bfs_disconnected_components_1");

    vector<int> result2 = bfs_parallel(g, 4);
    vector<int> expected2 = {4, 5, 6};
    assertEqual(result2, expected2, "test_bfs_disconnected_components_2");
}

void test_bfs_duplicate_edges() {
    Graph g;
    g.add_edge(1, 2);
    g.add_edge(1, 2); // Duplicate
    g.add_edge(2, 3);

    vector<int> result = bfs_parallel(g, 1);
    vector<int> expected = {1, 2, 3};
    assertEqual(result, expected, "test_bfs_duplicate_edges");
}

void test_bfs_nonexistent_start_vertex() {
    Graph g;
    g.add_edge(1, 2);

    vector<int> result = bfs_parallel(g, 999);
    vector<int> expected = {};
    assertEqual(result, expected, "test_bfs_nonexistent_start_vertex");
}

void test_bfs_complex_graph() {
    Graph g;
    vector<std::pair<int, int>> edges = {
        {1, 2}, {1, 3}, {2, 4}, {3, 4}, {4, 5},
        {5, 6}, {6, 7}, {5, 7}, {7, 8}, {3, 8}
    };
    for (auto& edge : edges) {
        g.add_edge(edge.first, edge.second);
    }
    vector<int> result = bfs_parallel(g, 1);
    vector<int> expected = {1, 2, 3, 4, 8, 5, 7, 6};
    assertEqual(result, expected, "test_bfs_complex_graph");
}

void test_bfs_order_consistency() {
    Graph g;
    g.add_edge(1, 3);
    g.add_edge(1, 2); // Added after 3

    vector<int> first_result = bfs_parallel(g, 1);
    bool consistent = true;
    for (int i = 0; i < 5; ++i) {
        vector<int> result = bfs_parallel(g, 1);
        if (result != first_result) {
            consistent = false;
            break;
        }
    }
    if (consistent) {
        std::cout << "test_bfs_order_consistency passed" << std::endl;
    } else {
        std::cout << "test_bfs_order_consistency failed" << std::endl;
    }
}

void test_bfs_performance_stress_test() {
    Graph g;
    int size = 1000;
    for (int i = 1; i < size; ++i) {
        g.add_edge(i, i + 1);
    }
    vector<int> result = bfs_parallel(g, 1);
    bool passed = (result.size() == size) && (result[0] == 1) && (result[size - 1] == size);
    if (passed) {
        std::cout << "test_bfs_performance_stress_test passed" << std::endl;
    } else {
        std::cout << "test_bfs_performance_stress_test failed" << std::endl;
    }
}

void test_bfs_performance_speed_test(){
    Graph g;
    int size = 2000;
    for (int i = 1; i <= size; ++i) {
        for (int j=i + 1; j<=size; j++){
            g.add_edge(i,j);
            g.add_edge(j,i);
        }
    }
    
    // warm-up
    bfs_parallel(g, 1);

    int reps =5, iters = 20;

    vector<double> per_run_ms;

    for(int i = 0; i < reps; i++){
        auto start = std::chrono::high_resolution_clock::now();
        for (int k=0; k<iters; k++) bfs_parallel(g, 1);
        auto end = std::chrono::high_resolution_clock::now();
        double total_ns = std::chrono::duration_cast<std::chrono::nanoseconds>(end - start).count();
        per_run_ms.push_back((total_ns / 1e6) / double(iters));
    }
    
    double mean = 0.0;
    for (double val : per_run_ms) mean+=val;
    mean /= double(reps);

    double sumsq = 0.0;
    for (double val : per_run_ms) {
        double d = val - mean;
        sumsq += d*d;
    }
    double sd = std::sqrt(sumsq / double(reps));
    
    long long undirected = 1LL * size * (size - 1) / 2;
    long long directed   = 1LL * size * (size - 1);

    
    std::cout << "BFS complete graph | nodes=" << size
         << ", undirected edges≈" << undirected
         << " (directed≈" << directed << ") | "
         << std::fixed<< mean << " ms/run ± "
         << std::fixed<< sd << " (n=" << reps << ")"
         << std::endl;

}


int main() {
    test_bfs_empty();
    test_bfs_single_node();
    test_bfs_linear_edge();
    test_bfs_complete_graph();
    test_bfs_star_graph();
    test_bfs_cycle();
    test_bfs_tree_structure();
    test_bfs_disconnected_components();
    test_bfs_duplicate_edges();
    test_bfs_nonexistent_start_vertex();
    test_bfs_complex_graph();
    test_bfs_order_consistency();
    test_bfs_performance_stress_test();
    test_bfs_performance_speed_test();

    return 0;
}
