#ifndef GRAPH_HPP
#define GRAPH_HPP

#include <unordered_map>
#include <vector>

class Graph {
public:
    std::unordered_map<int, std::vector<int>> vertices;
    void add_edge(int u, int v);
};

#endif 