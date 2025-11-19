#include "bfs_seq.hpp"
#include "graph.h"
#include <queue>
#include <unordered_map>
#include <vector>

std::vector<int> bfs_seq(Graph& g, int start_vertex) {
    std::vector<int> result;

    if (g.vertices.count(start_vertex) == 0) {
        return result;
    }

    std::unordered_map<int, bool> visited;
    std::queue<int> q;

    visited[start_vertex] = true;
    q.push(start_vertex);

    while (!q.empty()) {
        int current = q.front();
        q.pop();
        result.push_back(current);

        for (int neighbor : g.vertices.at(current)) {
            if (!visited[neighbor]) {
                visited[neighbor] = true;
                q.push(neighbor);
            }
        }
    }

    return result;
}
