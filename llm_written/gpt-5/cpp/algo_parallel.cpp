#include <bits/stdc++.h>
#include <omp.h>
using namespace std;

struct PairHash {
    size_t operator()(const pair<int,int>& p) const noexcept {
        return (static_cast<size_t>(p.first) << 32) ^ static_cast<size_t>(p.second);
    }
};

class Graph {
private:
    int V;
    vector<vector<int>> adj, revAdj;

    void TarjanDFS(
        int u,
        vector<int>& disc,
        vector<int>& low,
        vector<int>& stack,
        vector<bool>& inStack,
        int& timer,
        vector<vector<int>>& sccList
    ) {
        disc[u] = low[u] = ++timer;
        stack.push_back(u);
        inStack[u] = true;

        for (int v : adj[u]) {
            if (disc[v] == -1) {
                TarjanDFS(v, disc, low, stack, inStack, timer, sccList);
                low[u] = min(low[u], low[v]);
            } else if (inStack[v]) {
                low[u] = min(low[u], disc[v]);
            }
        }

        if (low[u] == disc[u]) {
            vector<int> scc;
            int w;
            do {
                w = stack.back();
                stack.pop_back();
                inStack[w] = false;
                scc.push_back(w);
            } while (w != u);
            sccList.push_back(move(scc));
        }
    }

    unordered_set<pair<int,int>, PairHash>
    BuildSpanningTree(int start, const vector<vector<int>>& graph, const unordered_set<int>& nodes) {
        unordered_set<pair<int,int>, PairHash> spanningTree;
        unordered_set<int> visited;
        vector<int> st;
        st.push_back(start);
        visited.insert(start);

        while (!st.empty()) {
            int node = st.back(); st.pop_back();
            for (int nb : graph[node]) {
                if (nodes.count(nb) && !visited.count(nb)) {
                    spanningTree.insert({node, nb});
                    visited.insert(nb);
                    st.push_back(nb);
                }
            }
        }
        return spanningTree;
    }

    // Return edges in deterministic sorted order
    static void sort_edges(vector<pair<int,int>>& edges) {
        sort(edges.begin(), edges.end(), [](const auto& a, const auto& b){
            if (a.first != b.first) return a.first < b.first;
            return a.second < b.second;
        });
    }

public:
    Graph(int v) : V(v), adj(v), revAdj(v) {}

    void AddEdge(int v, int w) {
        if (v < 0 || v >= V || w < 0 || w >= V) return;
        adj[v].push_back(w);
        revAdj[w].push_back(v);
    }

    vector<vector<int>> FindSCCs() {
        vector<int> disc(V, -1), low(V, -1);
        vector<bool> inStack(V, false);
        vector<int> stack;
        vector<vector<int>> sccList;
        int timer = 0;

        for (int i = 0; i < V; ++i) {
            if (disc[i] == -1) {
                TarjanDFS(i, disc, low, stack, inStack, timer, sccList);
            }
        }
        return sccList;
    }

    vector<pair<int,int>> MinimizeEdgesInSCC(const vector<int>& scc) {
        if (scc.empty()) return {};
        unordered_set<int> nodes(scc.begin(), scc.end());
        vector<pair<int,int>> essentialEdges;

        auto forwardTree = BuildSpanningTree(scc[0], adj, nodes);
        auto reverseTree = BuildSpanningTree(scc[0], revAdj, nodes);

        essentialEdges.reserve(forwardTree.size() + reverseTree.size());
        for (const auto& e : forwardTree) essentialEdges.push_back(e);
        for (const auto& e : reverseTree) essentialEdges.push_back(e);

        // Enforce deterministic order inside each SCC result
        sort_edges(essentialEdges);
        return essentialEdges;
    }

    // Original sequential reduction kept for baseline tests
    vector<pair<int,int>> ReduceEdgesSequential() {
        auto SCCs = FindSCCs();
        vector<pair<int,int>> reducedEdges;
        for (const auto& scc : SCCs) {
            auto minEdges = MinimizeEdgesInSCC(scc);
            reducedEdges.insert(reducedEdges.end(), minEdges.begin(), minEdges.end());
        }
        return reducedEdges;
    }

    // Parallel across SCCs with fixed partitioning and ordered merge
    vector<pair<int,int>> ReduceEdgesParallel(size_t small_threshold_scc = 3) {
        auto SCCs = FindSCCs();
        const size_t n = SCCs.size();
        if (n == 0) return {};

        // Small-N fallback or no parallelism available
        int max_threads = omp_get_max_threads();
        if (n <= small_threshold_scc || max_threads <= 1) {
            return ReduceEdgesSequential();
        }

        vector<vector<pair<int,int>>> perScc(n);

        // Fixed static schedule ensures determinism in work assignment
        #pragma omp parallel for schedule(static)
        for (long long i = 0; i < static_cast<long long>(n); ++i) {
            perScc[i] = MinimizeEdgesInSCC(SCCs[static_cast<size_t>(i)]);
        }

        // Deterministic ordered merge by index
        vector<pair<int,int>> reducedEdges;
        size_t total = 0;
        for (const auto& v : perScc) total += v.size();
        reducedEdges.reserve(total);
        for (size_t i = 0; i < n; ++i) {
            const auto& v = perScc[i];
            reducedEdges.insert(reducedEdges.end(), v.begin(), v.end());
        }
        return reducedEdges;
    }
};

// Expose a tiny CLI for manual runs (optional)
#ifdef BUILD_STANDALONE
int main(){
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int V, E; if(!(cin>>V>>E)) return 0;
    Graph g(V);
    for(int i=0;i<E;++i){int u,v;cin>>u>>v;g.AddEdge(u,v);} 
    auto a = g.ReduceEdgesSequential();
    auto b = g.ReduceEdgesParallel();
    cout << "seq=" << a.size() << " par=" << b.size() << "\n";
    return 0;
}
#endif
