#include "bfs_parallel.hpp"
#include "bfs_seq.hpp"
#include "graph.h"
#include <queue>
#include <unordered_map>
#include <vector>
#include <climits>
#include <cstddef>
#ifdef _OPENMP
#include <omp.h>
#endif

// Parallel, deterministic level-synchronous BFS.
// Strategy: For each level (frontier), gather adjacency lists of frontier nodes in parallel
// into per-index buckets. Then, in a single serial pass over the buckets in index order,
// filter with the global visited set and build the next frontier. This preserves the exact
// discovery order of a sequential BFS while still parallelizing neighbor enumeration.
std::vector<int> bfs(Graph& g, int start_vertex) {
    std::vector<int> result;
    if (g.vertices.count(start_vertex) == 0) {
        return result;
    }

    // Small-input fast path or lack of parallel resources: use sequential BFS directly.
#ifdef _OPENMP
    int max_threads = omp_get_max_threads();
#else
    int max_threads = 1;
#endif
    const std::size_t node_count = g.vertices.size();
    if (node_count < 50 || max_threads <= 1) {
        return bfs_seq(g, start_vertex);
    }

    std::unordered_map<int, bool> visited;
    visited.reserve(node_count * 2 + 1);

    std::vector<int> frontier;
    frontier.push_back(start_vertex);

    visited[start_vertex] = true;
    result.push_back(start_vertex);

    while (!frontier.empty()) {
        const std::size_t F = frontier.size();
        // Small frontier: do the simple serial inner step to avoid overhead.
        if (F < 32) {
            std::vector<int> next_frontier;
            next_frontier.reserve(F * 2);
            for (std::size_t i = 0; i < F; ++i) {
                int u = frontier[i];
                const auto &nbrs = g.vertices.at(u);
                for (int v : nbrs) {
                    if (!visited[v]) {
                        visited[v] = true;
                        next_frontier.push_back(v);
                    }
                }
            }
            if (!next_frontier.empty()) {
                // Append in precise discovery order (already ordered)
                result.insert(result.end(), next_frontier.begin(), next_frontier.end());
                frontier.swap(next_frontier);
            } else {
                frontier.clear();
            }
            continue;
        }

        // Parallel neighbor gathering
        std::vector<std::vector<int>> buckets(F);

        // Reserve approximate capacities for buckets to reduce reallocations; heuristic
        for (std::size_t i = 0; i < F; ++i) {
            int u = frontier[i];
            const auto &nbrs = g.vertices.at(u);
            buckets[i].reserve(nbrs.size());
        }

        // Parallel for over frontier indices to copy adjacency lists into buckets
#ifdef _OPENMP
#pragma omp parallel for schedule(static)
#endif
        for (long long i = 0; i < static_cast<long long>(F); ++i) {
            int u = frontier[static_cast<std::size_t>(i)];
            const auto &nbrs = g.vertices.at(u);
            // Copy neighbors as candidates; filtering happens serially to preserve order
            buckets[static_cast<std::size_t>(i)].insert(buckets[static_cast<std::size_t>(i)].end(), nbrs.begin(), nbrs.end());
        }

        // Serial, deterministic merge with global visited filter
        std::vector<int> next_frontier;
        // Heuristic reserve: assume average degree ~ buckets total / F
        std::size_t total_candidates = 0;
        for (const auto &b : buckets) total_candidates += b.size();
        next_frontier.reserve(total_candidates / 2 + 1);

        for (std::size_t i = 0; i < F; ++i) {
            for (int v : buckets[i]) {
                if (!visited[v]) {
                    visited[v] = true;
                    next_frontier.push_back(v);
                }
            }
        }

        if (!next_frontier.empty()) {
            result.insert(result.end(), next_frontier.begin(), next_frontier.end());
            frontier.swap(next_frontier);
        } else {
            frontier.clear();
        }
    }

    return result;
}
