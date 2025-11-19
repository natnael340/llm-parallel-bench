#include <iostream>
#include <vector>
#include <stack>
#include <algorithm>
#include <unordered_set>
#include <utility>

using namespace std;

// A simple hash for pairs to be used in unordered_set
struct PairHash_Seq {
    size_t operator()(const pair<int,int>& p) const noexcept {
        return (static_cast<size_t>(p.first) << 32) ^ static_cast<size_t>(p.second);
    }
};

class GraphSequential {
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

    unordered_set<pair<int,int>, PairHash_Seq>
    BuildSpanningTree(int start, const vector<vector<int>>& graph, const unordered_set<int>& nodes) {
        unordered_set<pair<int,int>, PairHash_Seq> spanningTree;
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
    GraphSequential(int v) : V(v), adj(v), revAdj(v) {}

    void AddEdge(int v, int w) {
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
        if (scc.empty()) {
            return {};
        }
        unordered_set<int> nodes(scc.begin(), scc.end());
        vector<pair<int,int>> essentialEdges;

        auto forwardTree = BuildSpanningTree(scc[0], adj, nodes);
        auto reverseTree = BuildSpanningTree(scc[0], revAdj, nodes);

        essentialEdges.reserve(forwardTree.size() + reverseTree.size());
        for (const auto& e : forwardTree) essentialEdges.push_back(e);
        for (const auto& e : reverseTree) essentialEdges.push_back(e);

        return essentialEdges;
    }

    vector<pair<int,int>> ReduceEdges() {
        auto SCCs = FindSCCs();
        vector<pair<int,int>> reducedEdges;
        for (const auto& scc : SCCs) {
            if (scc.size() > 1) {
                auto minEdges = MinimizeEdgesInSCC(scc);
                reducedEdges.insert(reducedEdges.end(), minEdges.begin(), minEdges.end());
            }
        }
        
        sort(reducedEdges.begin(), reducedEdges.end());
        return reducedEdges;
    }
};
