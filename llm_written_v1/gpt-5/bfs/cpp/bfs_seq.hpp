#ifndef BFS_SEQ_HPP
#define BFS_SEQ_HPP

#include <vector>
#include "graph.h"

// Sequential BFS baseline used for testing equality and determinism
std::vector<int> bfs_seq(Graph& g, int start_vertex);

#endif