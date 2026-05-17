package main

import "sort"

// Graph represents an undirected graph using an adjacency list
type Graph struct {
	Vertices map[int][]int
}

// AddEdge adds an undirected edge between two vertices
func (g *Graph) AddEdge(from, to int) {
	if g.Vertices == nil {
		g.Vertices = make(map[int][]int)
	}
	g.Vertices[from] = append(g.Vertices[from], to)
	g.Vertices[to] = append(g.Vertices[to], from)
}

// Normalize ensures deterministic iteration by sorting all adjacency lists
func (g *Graph) Normalize() {
	for vertex := range g.Vertices {
		sort.Ints(g.Vertices[vertex])
	}
}
