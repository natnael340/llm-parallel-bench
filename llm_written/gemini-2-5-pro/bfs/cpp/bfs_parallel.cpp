#include "bfs_parallel.hpp"
#include "bfs_seq.hpp"
#include "graph.h"
#include <vector>
#include <queue>
#include <unordered_map>
#include <omp.h>
#include <algorithm>
#include <iostream>

// Threshold for switching to sequential implementation
const int PARALLEL_THRESHOLD = 0;

std::vector<int> bfs_parallel(Graph& g, int start_vertex) {
    if (g.vertices.size() < PARALLEL_THRESHOLD) {
        return bfs(g, start_vertex);
    }

    std::vector<int> result;
    if (g.vertices.count(start_vertex) == 0) {
        return result;
    }

    std::unordered_map<int, bool> visited;
    for(auto const& [key, val] : g.vertices) {
        visited[key] = false;
    }

    std::vector<int> frontier;
    
    visited[start_vertex] = true;
    frontier.push_back(start_vertex);

    while (!frontier.empty()) {
        for (int node : frontier) {
            result.push_back(node);
        }

        int num_threads = omp_get_max_threads();
        std::vector<std::vector<int>> local_next_frontiers(num_threads);

        #pragma omp parallel for schedule(dynamic)
        for (size_t i = 0; i < frontier.size(); ++i) {
            int current = frontier[i];
            int thread_id = omp_get_thread_num();
            
            // To ensure deterministic neighbor traversal, we sort them first.
            std::vector<int> neighbors = g.vertices.at(current);
            std::sort(neighbors.begin(), neighbors.end());

            for (int neighbor : neighbors) {
                bool is_visited = false;
                #pragma omp critical(visited_check)
                {
                    is_visited = visited[neighbor];
                }
                
                if (!is_visited) {
                    bool set_by_this_thread = false;
                    #pragma omp critical(visited_update)
                    {
                        if (!visited[neighbor]) {
                            visited[neighbor] = true;
                            set_by_this_thread = true;
                        }
                    }
                    if (set_by_this_thread) {
                        local_next_frontiers[thread_id].push_back(neighbor);
                    }
                }
            }
        }

        std::vector<int> next_frontier;
        for (int i = 0; i < num_threads; ++i) {
            next_frontier.insert(next_frontier.end(), local_next_frontiers[i].begin(), local_next_frontiers[i].end());
        }
        
        // Sort to ensure deterministic traversal order across runs
        std::sort(next_frontier.begin(), next_frontier.end());
        frontier = next_frontier;
    }

    return result;
}
