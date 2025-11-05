#include <bits/stdc++.h>
using namespace std;

struct PairHash {
    size_t operator()(const pair<int,int>& p) const noexcept {
        // simple hash combine
        return (static_cast<size_t>(p.first) << 32) ^ static_cast<size_t>(p.second);
    }
};

class Graph {
private:
    int V;
    vector<vector<int>> adj, revAdj;

    // Tarjan’s SCC DFS
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

    // Build a DFS spanning tree over 'graph' restricted to 'nodes'
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

public:
    Graph(int v) : V(v), adj(v), revAdj(v) {}

    void AddEdge(int v, int w) {
        adj[v].push_back(w);
        revAdj[w].push_back(v); // reverse graph for later use
    }

    // Tarjan’s SCC (O(V+E))
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

    // Minimal SCC Edge Reduction (O(V+E))
    vector<pair<int,int>> MinimizeEdgesInSCC(const vector<int>& scc) {
        unordered_set<int> nodes(scc.begin(), scc.end());
        vector<pair<int,int>> essentialEdges;

        // Step 1: forward spanning tree using DFS
        auto forwardTree = BuildSpanningTree(scc[0], adj, nodes);

        // Step 2: reverse spanning tree using DFS on the reversed graph
        auto reverseTree = BuildSpanningTree(scc[0], revAdj, nodes);

        // Step 3: Merge both trees (each edge appears at most twice)
        essentialEdges.reserve(forwardTree.size() + reverseTree.size());
        for (const auto& e : forwardTree) essentialEdges.push_back(e);
        for (const auto& e : reverseTree) essentialEdges.push_back(e);

        return essentialEdges;
    }

    vector<pair<int,int>> ReduceEdges() {
        auto SCCs = FindSCCs();
        cout << "Found " << SCCs.size() << " SCC(s)." << '\n';

        vector<pair<int,int>> reducedEdges;
        for (const auto& scc : SCCs) {
            auto minEdges = MinimizeEdgesInSCC(scc);
            reducedEdges.insert(reducedEdges.end(), minEdges.begin(), minEdges.end());
        }

        cout << "Reduced SCC edges: " << reducedEdges.size() << '\n';
        return reducedEdges;
    }
};

// ------------------------
// Example usage
// ------------------------
int main() {
    Graph g(7);
    g.AddEdge(0, 1);
    g.AddEdge(1, 2);
    g.AddEdge(1, 3);
    g.AddEdge(1, 4);
    g.AddEdge(2, 0);
    g.AddEdge(2, 3);
    g.AddEdge(3, 5);
    g.AddEdge(5, 3);
    g.AddEdge(5, 4);
    g.AddEdge(5, 6);
    g.AddEdge(6, 4);
    g.AddEdge(4, 6);

    auto edges = g.ReduceEdges();
    for (auto& e : edges) {
        cout << e.first << " -> " << e.second << '\n';
    }
    return 0;
}
