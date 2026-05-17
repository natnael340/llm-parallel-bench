#include "bfs_parallel.hpp"
#include <omp.h>
#include <vector>
#include <unordered_set>
#include <algorithm>

std::vector<int> bfs_parallel(Graph& g, int start_vertex) {
    std::vector<int> result;
    
    // Edge case: start vertex not in graph
    if (g.vertices.count(start_vertex) == 0) {
        return result;
    }
    
    // Small graph fallback: use sequential for graphs < 100 vertices
    if (g.vertices.size() < 100) {
        // Sequential BFS
        std::unordered_set<int> visited;
        std::vector<int> current_frontier = {start_vertex};
        visited.insert(start_vertex);
        
        while (!current_frontier.empty()) {
            std::vector<int> next_frontier;
            
            for (int v : current_frontier) {
                result.push_back(v);
                
                for (int neighbor : g.vertices.at(v)) {
                    if (visited.find(neighbor) == visited.end()) {
                        visited.insert(neighbor);
                        next_frontier.push_back(neighbor);
                    }
                }
            }
            
            current_frontier = std::move(next_frontier);
        }
        
        return result;
    }
    
    // Parallel BFS with level synchronization
    // Key: maintain exact sequential order by processing frontier in order
    // but parallelizing the neighbor collection for each vertex
    
    std::unordered_set<int> visited;
    std::vector<int> current_frontier = {start_vertex};
    visited.insert(start_vertex);
    
    int num_threads = omp_get_max_threads();
    
    while (!current_frontier.empty()) {
        // Add current frontier to result (in order)
        result.insert(result.end(), current_frontier.begin(), current_frontier.end());
        
        // For each vertex in frontier, collect its neighbors
        // Store them in per-vertex lists to maintain order
        std::vector<std::vector<int>> per_vertex_neighbors(current_frontier.size());
        
        // Process each vertex in parallel to find its neighbors
        // Use dynamic scheduling with chunk size 1 for better load balancing
        #pragma omp parallel for num_threads(num_threads) schedule(dynamic, 1)
        for (size_t i = 0; i < current_frontier.size(); i++) {
            int current = current_frontier[i];
            const std::vector<int>& neighbors = g.vertices.at(current);
            
            // Collect all neighbors (we'll deduplicate later)
            per_vertex_neighbors[i] = neighbors;
        }
        
        // Sequentially merge and deduplicate to maintain exact order
        std::vector<int> next_frontier;
        
        for (size_t i = 0; i < current_frontier.size(); i++) {
            for (int neighbor : per_vertex_neighbors[i]) {
                if (visited.find(neighbor) == visited.end()) {
                    visited.insert(neighbor);
                    next_frontier.push_back(neighbor);
                }
            }
        }
        
        current_frontier = std::move(next_frontier);
    }
    
    return result;
}
