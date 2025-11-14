package main

import (
	"fmt"
)

// Edge represents a directed edge u -> v.
type Edge struct {
	U, V int
}

type Graph struct {
	V      int
	Adj    [][]int
	RevAdj [][]int
	Verbose bool
}

func NewGraph(v int) *Graph {
	g := &Graph{
		V:      v,
		Adj:    make([][]int, v),
		RevAdj: make([][]int, v),
		Verbose: false,
	}
	for i := 0; i < v; i++ {
		g.Adj[i] = []int{}
		g.RevAdj[i] = []int{}
	}
	return g
}

func (g *Graph) AddEdge(v, w int) {
	g.Adj[v] = append(g.Adj[v], w)
	g.RevAdj[w] = append(g.RevAdj[w], v) // reverse graph for later use
}

// ---------- Tarjan’s SCC (O(V+E)) ----------

func (g *Graph) tarjanDFS(
	u int,
	disc []int,
	low []int,
	stack *[]int,
	inStack []bool,
	timeRef *int,
	sccList *[][]int,
) {
	*timeRef += 1
	disc[u] = *timeRef
	low[u] = *timeRef
	*stack = append(*stack, u)
	inStack[u] = true

	for _, v := range g.Adj[u] {
		if disc[v] == -1 {
			g.tarjanDFS(v, disc, low, stack, inStack, timeRef, sccList)
			if low[v] < low[u] {
				low[u] = low[v]
			}
		} else if inStack[v] {
			if disc[v] < low[u] {
				low[u] = disc[v]
			}
		}
	}

	if low[u] == disc[u] {
		var scc []int
		for {
			w := (*stack)[len(*stack)-1]
			*stack = (*stack)[:len(*stack)-1]
			inStack[w] = false
			scc = append(scc, w)
			if w == u {
				break
			}
		}
		*sccList = append(*sccList, scc)
	}
}

func (g *Graph) FindSCCs() [][]int {
	disc := make([]int, g.V)
	low := make([]int, g.V)
	inStack := make([]bool, g.V)
	stack := make([]int, 0, g.V)
	sccList := make([][]int, 0)

	for i := 0; i < g.V; i++ {
		disc[i] = -1
		low[i] = -1
	}
	timeRef := 0

	for i := 0; i < g.V; i++ {
		if disc[i] == -1 {
			g.tarjanDFS(i, disc, low, &stack, inStack, &timeRef, &sccList)
		}
	}
	return sccList
}

// ---------- Minimal SCC Edge Reduction ----------

func (g *Graph) MinimizeEdgesInSCC(scc []int) []Edge {
	nodes := make(map[int]bool, len(scc))
	for _, n := range scc {
		nodes[n] = true
	}

	// Step 1: forward spanning tree using DFS
	forwardTree := g.buildSpanningTree(scc[0], g.Adj, nodes)

	// Step 2: reverse spanning tree using DFS on reversed graph
	reverseTree := g.buildSpanningTree(scc[0], g.RevAdj, nodes)

	// Step 3: merge both trees (each edge appears at most twice)
	out := make([]Edge, 0, len(forwardTree)+len(reverseTree))
	for e := range forwardTree {
		out = append(out, e)
	}
	for e := range reverseTree {
		out = append(out, e)
	}
	return out
}

func (g *Graph) buildSpanningTree(start int, graph [][]int, nodes map[int]bool) map[Edge]struct{} {
	spanning := make(map[Edge]struct{})
	visited := make(map[int]bool, len(nodes))
	stack := []int{start}
	visited[start] = true

	for len(stack) > 0 {
		// pop
		node := stack[len(stack)-1]
		stack = stack[:len(stack)-1]

		for _, nb := range graph[node] {
			if nodes[nb] && !visited[nb] {
				spanning[Edge{node, nb}] = struct{}{}
				visited[nb] = true
				stack = append(stack, nb)
			}
		}
	}
	return spanning
}

func (g *Graph) ReduceEdges() []Edge {
	sccs := g.FindSCCs()
	if g.Verbose {
		fmt.Printf("Found %d SCC(s).\n", len(sccs))
	}

	reduced := make([]Edge, 0)
	for _, scc := range sccs {
		minEdges := g.MinimizeEdgesInSCC(scc)
		reduced = append(reduced, minEdges...)
	}

	if g.Verbose {
		fmt.Printf("Reduced SCC edges: %d\n", len(reduced))
	}
	return reduced
}