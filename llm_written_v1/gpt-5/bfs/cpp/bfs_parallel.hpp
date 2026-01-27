#ifndef BFS_PARALLEL_HPP
#define BFS_PARALLEL_HPP

#include <vector>
#include "graph.h"

// Parallel, deterministic BFS with the same public API name
// Returns the list of vertices visited in BFS order starting from start_vertex.
std::vector<int> bfs(Graph& g, int start_vertex);

#endif