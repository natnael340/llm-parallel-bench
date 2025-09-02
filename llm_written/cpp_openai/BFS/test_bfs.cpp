#include <iostream>
#include <random>
#include <algorithm>
#include <cassert>
#include <unordered_set>

#include "graph.h"
#include "bfs_seq.hpp"
#include "bfs_parallel.hpp"

static Graph make_line_graph(int n) {
    Graph g;
    for (int i = 0; i < n - 1; ++i) {
        g.add_edge(i, i + 1);
    }
    return g;
}

static Graph make_star_graph(int center, int spokes) {
    Graph g;
    for (int i = 1; i <= spokes; ++i) {
        g.add_edge(center, center + i);
    }
    return g;
}

static Graph make_grid_graph(int rows, int cols) {
    Graph g;
    auto id = [cols](int r, int c) { return r * cols + c; };
    for (int r = 0; r < rows; ++r) {
        for (int c = 0; c < cols; ++c) {
            if (r + 1 < rows) g.add_edge(id(r, c), id(r + 1, c));
            if (c + 1 < cols) g.add_edge(id(r, c), id(r, c + 1));
        }
    }
    return g;
}

static Graph make_random_graph(int n, int m, uint32_t seed) {
    Graph g;
    std::mt19937 rng(seed);
    std::uniform_int_distribution<int> dist(0, n - 1);
    for (int i = 0; i < m; ++i) {
        int u = dist(rng);
        int v = dist(rng);
        if (u != v) g.add_edge(u, v);
    }
    return g;
}

static void compare_runs(Graph &g, int start) {
    auto seq = bfs_seq(g, start);
    auto par = bfs(g, start);
    if (seq != par) {
        std::cerr << "Mismatch!\nSeq: ";
        for (int x : seq) std::cerr << x << ' ';
        std::cerr << "\nPar: ";
        for (int x : par) std::cerr << x << ' ';
        std::cerr << "\n";
        assert(false && "Parallel BFS output differs from sequential BFS");
    }
}

int main() {
    int passed = 0;

    // Edge cases
    {
        Graph g; // empty
        compare_runs(g, 0);
        ++passed;
    }

    {
        Graph g; // single vertex no edges
        g.add_edge(0, 0); // will create a self-loop pair but our add_edge adds both ways; ensure vertex exists
        // Remove duplicate by constructing directly
        g.vertices.clear();
        g.vertices[0] = {};
        compare_runs(g, 0);
        ++passed;
    }

    // Simple structures
    {
        auto g = make_line_graph(10);
        compare_runs(g, 0);
        ++passed;
    }
    {
        auto g = make_star_graph(0, 50);
        compare_runs(g, 0);
        ++passed;
    }
    {
        auto g = make_grid_graph(8, 8);
        compare_runs(g, 0);
        ++passed;
    }

    // Random graphs with fixed seeds
    for (int n : {10, 50, 200}) {
        for (int density = 1; density <= 5; ++density) {
            int m = n * density; // number of edges
            for (uint32_t seed : {1u, 42u, 123456u}) {
                auto g = make_random_graph(n, m, seed);
                compare_runs(g, 0);
                ++passed;
            }
        }
    }

    // Determinism check: run parallel twice and compare
    {
        auto g = make_random_graph(100, 300, 777u);
        auto r1 = bfs(g, 0);
        auto r2 = bfs(g, 0);
        assert(r1 == r2 && "Parallel BFS produced non-deterministic results");
        ++passed;
    }

    std::cout << "All tests passed: " << passed << " cases\n";
    return 0;
}
