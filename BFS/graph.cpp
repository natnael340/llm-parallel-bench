#include "graph.h"

void Graph::add_edge(int u, int v) {
    if(vertices.count(u) == 0) vertices[u] = {};
    if(vertices.count(v) == 0) vertices[v] = {};

    vertices[u].push_back(v);
    vertices[v].push_back(u);
}
