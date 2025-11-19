// tests_graph.cpp
#include <vector>
#include <utility>
#include <algorithm>
#include <random>
#include <cassert>
#include <iostream>
#include <set>

// Adjust if your header name differs:
#include "graph.cpp"

using std::pair;
using std::vector;

static vector<pair<int,int>> ring_scc(int start, int n, Graph& graph) {
    vector<pair<int,int>> reduced_sccs;
    for (int i = start; i < n; ++i) {
        int v = (i + 1) % n;
        v = (v != 0) ? v : start;

        if (i == v) continue;

        graph.AddEdge(i, v);

        if ((i + 1) != n - 1) {
            reduced_sccs.emplace_back(i, v);
        }
        if (i != start) {
            int u = (i - 1) % n;
            u = (u != 0) ? u : start;
            reduced_sccs.emplace_back(i, u);
        }
    }
    return reduced_sccs;
}

template <typename T>
static bool equal_nested(const vector<vector<T>>& a, const vector<vector<T>>& b) {
    return a == b;
}

static void sort_edges(vector<pair<int,int>>& v) {
    std::sort(v.begin(), v.end(), [](const auto& l, const auto& r){
        if (l.first != r.first) return l.first < r.first;
        return l.second < r.second;
    });
}
static void expect_same_multiset(std::vector<std::pair<int,int>> a,
                                 std::vector<std::pair<int,int>> b) {
    auto by_pair = [](const auto& l, const auto& r){
        if (l.first != r.first) return l.first < r.first;
        return l.second < r.second;
    };
    std::sort(a.begin(), a.end(), by_pair);
    std::sort(b.begin(), b.end(), by_pair);

    if (a != b) {
        std::cerr << "\n--- Multiset mismatch ---\n";
        std::cerr << "left (got)  size=" << a.size() << "\n";
        for (size_t i = 0; i < a.size(); ++i) {
            if (i < 20) std::cerr << "  " << a[i].first << "," << a[i].second << "\n";
            else { std::cerr << "  ...(" << (a.size()-20) << " more)\n"; break; }
        }
        std::cerr << "right (exp) size=" << b.size() << "\n";
        for (size_t i = 0; i < b.size(); ++i) {
            if (i < 20) std::cerr << "  " << b[i].first << "," << b[i].second << "\n";
            else { std::cerr << "  ...(" << (b.size()-20) << " more)\n"; break; }
        }
        // also print the first differing index if lengths match
        if (a.size() == b.size()) {
            for (size_t i = 0; i < a.size(); ++i) {
                if (a[i] != b[i]) {
                    std::cerr << "first diff at idx " << i
                              << " got=(" << a[i].first << "," << a[i].second << ")"
                              << " exp=(" << b[i].first << "," << b[i].second << ")\n";
                    break;
                }
            }
        }
        std::cerr << "-------------------------\n";
        assert(false && "multiset equality failed");
    }
}

static void test_empty_graph() {
    Graph g(0);
    auto sccs = g.FindSCCs();
    assert(sccs.empty());
    auto reduced = g.ReduceEdges();
    assert(reduced.empty());
}

static void test_singleton_no_edges() {
    Graph g(1);
    assert(equal_nested(g.FindSCCs(), {{0}}));
    assert(g.ReduceEdges().empty());
}

static void test_singleton_self_loop() {
    Graph g(1);
    g.AddEdge(0,0);
    assert(equal_nested(g.FindSCCs(), {{0}}));
    assert(g.ReduceEdges().empty());
}

static void test_simple_cycle_3() {
    Graph g(3);
    g.AddEdge(0,1);
    g.AddEdge(1,2);
    g.AddEdge(2,0);
    assert(equal_nested(g.FindSCCs(), {{2,1,0}}));
    vector<pair<int,int>> expected = {{2,0},{0,1},{1,2},{1,0}};
    expect_same_multiset(g.ReduceEdges(), expected);
}

static void test_two_node_mutual_scc() {
    Graph g(2);
    g.AddEdge(0,1);
    g.AddEdge(1,0);
    assert(equal_nested(g.FindSCCs(), {{1,0}}));
    vector<pair<int,int>> expected = {{1,0},{1,0}};
    expect_same_multiset(g.ReduceEdges(), expected);
}

static void test_dense_three_node_scc() {
    Graph g(3);
    for (auto [u,v] : vector<pair<int,int>>{{0,1},{1,2},{2,0},{0,2},{2,1},{1,0}}) {
        g.AddEdge(u,v);
    }
    assert(equal_nested(g.FindSCCs(), {{2,1,0}}));
    vector<pair<int,int>> expected = {{2,0},{2,1},{2,0},{2,1}};
    expect_same_multiset(g.ReduceEdges(), expected);
}

static void test_multiple_sccs_with_cross() {
    // SCC1: 0->1->2->0; SCC2: 3<->4; cross 2->3
    Graph g(5);
    g.AddEdge(0,1);
    g.AddEdge(1,2);
    g.AddEdge(2,0);
    g.AddEdge(3,4);
    g.AddEdge(4,3);
    g.AddEdge(2,3);

    vector<vector<int>> expected_sccs = {{4,3},{2,1,0}};
    assert(equal_nested(g.FindSCCs(), expected_sccs));

    vector<pair<int,int>> expected = {{4,3},{4,3},{2,0},{0,1},{2,1},{1,0}};
    auto reduced = g.ReduceEdges();
    assert(reduced.size() == expected.size());
    expect_same_multiset(reduced, expected);
}

static void test_disconnected_with_dag_component() {
    // SCC: 0,1,2 ; DAG piece: 3->4->5
    Graph g(6);
    g.AddEdge(0,1);
    g.AddEdge(1,2);
    g.AddEdge(2,0);
    g.AddEdge(3,4);
    g.AddEdge(4,5);

    vector<vector<int>> expected_sccs = {{2,1,0},{5},{4},{3}};
    assert(equal_nested(g.FindSCCs(), expected_sccs));

    vector<pair<int,int>> expected = {{2,0},{0,1},{2,1},{1,0}};
    auto reduced = g.ReduceEdges();
    assert(reduced.size() == expected.size());
    expect_same_multiset(reduced, expected);
}

static void test_star_like_scc() {
    // 0 connected both ways with leaves => single SCC
    int n = 7;
    Graph g(n);
    for (int i = 1; i < n; ++i) {
        g.AddEdge(0,i);
        g.AddEdge(i,0);
    }
    vector<int> scc(n);
    for (int i = 0; i < n; ++i) scc[i] = n - 1 - i;
    assert(equal_nested(g.FindSCCs(), {scc}));

    vector<pair<int,int>> expected = {
        {6,0},{6,0},{0,1},{0,2},{0,3},{0,4},{0,5},
        {0,1},{0,2},{0,3},{0,4},{0,5}
    };
    auto reduced = g.ReduceEdges();
    assert(reduced.size() == expected.size());
    expect_same_multiset(reduced, expected);
}

static void test_large_ring_scc() {
    int n = 300;
    Graph g(n);
    vector<pair<int,int>> expected;

    for (int i = 0; i < n; ++i) {
        g.AddEdge(i, (i + 1) % n);
        if ((i + 1) != n - 1) expected.emplace_back(i, (i + 1) % n);
        if (i != 0) expected.emplace_back(i, (i - 1) % n);
    }

    vector<int> scc(n);
    for (int i = 0; i < n; ++i) scc[i] = n - 1 - i;
    assert(equal_nested(g.FindSCCs(), {scc}));

    auto reduced = g.ReduceEdges();
    assert(reduced.size() == expected.size());
    expect_same_multiset(reduced, expected);
}

static void test_random_sccs() {
    for (int trial = 0; trial < 5; ++trial) {
        int n = 80;
        Graph g(n);
        vector<pair<int,int>> expected;
        for (int i = 0; i < n; ++i) {
            g.AddEdge(i, (i + 1) % n);
            if ((i + 1) != n - 1) expected.emplace_back(i, (i + 1) % n);
            if (i != 0) expected.emplace_back(i, (i - 1) % n);
        }

        std::mt19937 rng(2025u + trial);
        std::uniform_int_distribution<int> dist(0, n - 1);
        for (int k = 0; k < n * 2; ++k) {
            int u = dist(rng), v = dist(rng);
            if (u != v) g.AddEdge(u, v);
        }

        vector<int> scc(n);
        for (int i = 0; i < n; ++i) scc[i] = n - 1 - i;
        assert(equal_nested(g.FindSCCs(), {scc}));

        auto reduced = g.ReduceEdges();
        assert(reduced.size() == expected.size());
    }
}

int main() {
    test_empty_graph();
    test_singleton_no_edges();
    test_singleton_self_loop();
    test_simple_cycle_3();
    test_two_node_mutual_scc();
    test_dense_three_node_scc();
    test_multiple_sccs_with_cross();
    test_disconnected_with_dag_component();
    test_star_like_scc();
    test_large_ring_scc();
    test_random_sccs();
    std::cout << "All tests passed.\n";
    return 0;
}
