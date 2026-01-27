#include <bits/stdc++.h>
#include <omp.h>
using namespace std;

#include "algo_parallel.cpp" // include implementation for simplicity in this harness

static string hash_edges(const vector<pair<int,int>>& edges){
    // produce a stable textual representation then hash via std::hash
    vector<pair<int,int>> e = edges;
    sort(e.begin(), e.end());
    string s; s.reserve(e.size()*9);
    for (auto &p: e){
        s.append(to_string(p.first)); s.push_back(','); s.append(to_string(p.second)); s.push_back(';');
    }
    return to_string(std::hash<string>{}(s));
}

// Build a random but reproducible graph with SCC structure
static Graph make_graph(int V, int E, uint32_t seed){
    Graph g(V);
    std::mt19937 rng(seed);
    std::uniform_int_distribution<int> dist(0, V-1);
    for (int i=0;i<E;++i){
        int u = dist(rng), v = dist(rng);
        if (u==v) { v = (v+1)%V; }
        g.AddEdge(u,v);
    }
    return g;
}

static void small_edge_cases(){
    // empty graph
    {
        Graph g(0);
        auto s = g.ReduceEdgesSequential();
        auto p = g.ReduceEdgesParallel();
        if (s != p) { cerr << "Mismatch on empty graph\n"; exit(1);}    }
    // single node
    {
        Graph g(1);
        auto s = g.ReduceEdgesSequential();
        auto p = g.ReduceEdgesParallel();
        if (s != p) { cerr << "Mismatch on single node\n"; exit(1);}    }
    // simple cycle 0->1->2->0
    {
        Graph g(3);
        g.AddEdge(0,1); g.AddEdge(1,2); g.AddEdge(2,0);
        auto s = g.ReduceEdgesSequential();
        auto p = g.ReduceEdgesParallel();
        if (s != p) { cerr << "Mismatch on simple cycle\n"; exit(1);}    }
}

static void differential_tests(){
    vector<pair<int,int>> sizes = {
        {10, 20}, {100, 300}, {1000, 4000}
    };
    for (auto [V,E] : sizes){
        Graph g = make_graph(V, E, /*seed*/ 12345 + V + E);
        auto s = g.ReduceEdgesSequential();
        auto p1 = g.ReduceEdgesParallel();
        auto p2 = g.ReduceEdgesParallel(); // determinism check

        if (s != p1) {
            cerr << "Parity fail at V="<<V<<" E="<<E<<"\n"; exit(2);
        }
        if (p1 != p2) {
            cerr << "Determinism fail at V="<<V<<" E="<<E<<"\n"; exit(3);
        }
        cerr << "OK V="<<V<<" E="<<E<<" edges="<<s.size()
             << " hash="<< hash_edges(s) <<"\n";
    }
}

static void perf_test(){
    const int V = 20000; const int E = 80000; // large-ish
    Graph g = make_graph(V, E, 777);

    auto t0 = chrono::high_resolution_clock::now();
    auto s = g.ReduceEdgesSequential();
    auto t1 = chrono::high_resolution_clock::now();
    auto p = g.ReduceEdgesParallel();
    auto t2 = chrono::high_resolution_clock::now();

    double ts = chrono::duration<double>(t1-t0).count();
    double tp = chrono::duration<double>(t2-t1).count();

    cerr.setf(std::ios::fixed); cerr<<setprecision(3);
    cerr << "PERF seq="<<ts<<"s par="<<tp<<"s speedup="<<(ts/tp) <<" threads="<< omp_get_max_threads() <<"\n";
}

int main(){
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    small_edge_cases();
    differential_tests();
    perf_test();
    return 0;
}
