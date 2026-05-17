#include "bfs_seq.hpp"
#include "graph.h"
#include <vector>
#include <unordered_map>
#include <algorithm>

std::vector<int> bfs(Graph& g, int start_vertex) {
    std::vector<int> result;
    if (g.vertices.find(start_vertex) == g.vertices.end()) {
        return result;
    }

    std::unordered_map<int, bool> visited;
    for (auto const& [vertex, _] : g.vertices) {
        visited[vertex] = false;
    }

    std::vector<int> frontier;
    frontier.push_back(start_vertex);
    visited[start_vertex] = true;

    while (!frontier.empty()) {
        std::sort(frontier.begin(), frontier.end());
        result.insert(result.end(), frontier.begin(), frontier.end());

        std::vector<int> next_frontier;
        for (int current_node : frontier) {
            std::vector<int> neighbors = g.vertices.at(current_node);
            std::sort(neighbors.begin(), neighbors.end());
            for (int neighbor : neighbors) {
                if (!visited[neighbor]) {
                    visited[neighbor] = true;
                    next_frontier.push_back(neighbor);
                }
            }
        }
        frontier = next_frontier;
    }
    return result;
}
