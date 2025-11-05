from SCSS.python.graph import Graph

if __name__ == "__main__":
    # Example usage
    g = Graph(7)

    g.add_edge(0, 1)
    g.add_edge(1, 2)
    g.add_edge(1, 3)
    g.add_edge(1, 4)
    g.add_edge(2, 0)
    g.add_edge(2, 3)
    g.add_edge(3, 5)
    g.add_edge(5, 3)
    g.add_edge(5, 4)
    g.add_edge(5, 6)
    g.add_edge(6, 4)
    g.add_edge(4, 6)

    reduced_edges = g.reduce_edges()

    print("\nReduced Edges:")
    for v, w in reduced_edges:
        print(f"{v} -> {w}")