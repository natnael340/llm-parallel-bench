package main

import (
	"crypto/sha256"
	"fmt"
	"math/rand"
)

type TestCase struct {
	name  string
	graph Graph
	start int
}

func hashResult(result []int) string {
	h := sha256.New()
	for _, v := range result {
		h.Write([]byte(fmt.Sprintf("%d,", v)))
	}
	return fmt.Sprintf("%x", h.Sum(nil))
}

func resultsEqual(a, b []int) bool {
	if len(a) != len(b) {
		return false
	}
	for i := range a {
		if a[i] != b[i] {
			return false
		}
	}
	return true
}

func buildTestCases() []TestCase {
	cases := []TestCase{}

	// Edge case: empty graph
	cases = append(cases, TestCase{
		name:  "empty_graph",
		graph: Graph{Vertices: make(map[int][]int)},
		start: 0,
	})

	// Edge case: single vertex
	g1 := Graph{}
	g1.AddEdge(0, 0)
	cases = append(cases, TestCase{
		name:  "single_vertex",
		graph: g1,
		start: 0,
	})

	// Small: linear chain (1-2-3-4-5)
	g2 := Graph{}
	for i := 0; i < 4; i++ {
		g2.AddEdge(i, i+1)
	}
	cases = append(cases, TestCase{
		name:  "small_chain",
		graph: g2,
		start: 0,
	})

	// Small: star graph (center 0, spokes 1-9)
	g3 := Graph{}
	for i := 1; i <= 9; i++ {
		g3.AddEdge(0, i)
	}
	cases = append(cases, TestCase{
		name:  "small_star",
		graph: g3,
		start: 0,
	})

	// Medium: grid 10x10
	g4 := Graph{}
	for i := 0; i < 10; i++ {
		for j := 0; j < 10; j++ {
			node := i*10 + j
			if j < 9 {
				g4.AddEdge(node, node+1) // right
			}
			if i < 9 {
				g4.AddEdge(node, node+10) // down
			}
		}
	}
	cases = append(cases, TestCase{
		name:  "medium_grid_10x10",
		graph: g4,
		start: 0,
	})

	// Medium: complete graph K_50
	g5 := Graph{}
	for i := 0; i < 50; i++ {
		for j := i + 1; j < 50; j++ {
			g5.AddEdge(i, j)
		}
	}
	cases = append(cases, TestCase{
		name:  "medium_complete_50",
		graph: g5,
		start: 0,
	})

	// Large: grid 50x50 (2500 vertices)
	g6 := Graph{}
	for i := 0; i < 50; i++ {
		for j := 0; j < 50; j++ {
			node := i*50 + j
			if j < 49 {
				g6.AddEdge(node, node+1)
			}
			if i < 49 {
				g6.AddEdge(node, node+50)
			}
		}
	}
	cases = append(cases, TestCase{
		name:  "large_grid_50x50",
		graph: g6,
		start: 0,
	})

	// Large: random sparse graph (1000 vertices, ~3000 edges)
	g7 := Graph{}
	rng := rand.New(rand.NewSource(42))
	for i := 0; i < 1000; i++ {
		// Each vertex connects to 3-6 random others
		numEdges := 3 + rng.Intn(4)
		for e := 0; e < numEdges; e++ {
			target := rng.Intn(1000)
			if target != i {
				g7.AddEdge(i, target)
			}
		}
	}
	cases = append(cases, TestCase{
		name:  "large_random_sparse_1000",
		graph: g7,
		start: 0,
	})

	// Large: binary tree depth 10 (~1023 nodes)
	g8 := Graph{}
	for i := 0; i < 511; i++ {
		left := 2*i + 1
		right := 2*i + 2
		if left < 1023 {
			g8.AddEdge(i, left)
		}
		if right < 1023 {
			g8.AddEdge(i, right)
		}
	}
	cases = append(cases, TestCase{
		name:  "large_binary_tree_depth10",
		graph: g8,
		start: 0,
	})

	return cases
}

func runCorrectnessTests() (int, int, []string) {
	cases := buildTestCases()
	passed := 0
	failed := 0
	details := []string{}

	for _, tc := range cases {
		// Make copies to avoid mutation
		g1 := copyGraph(tc.graph)
		g2 := copyGraph(tc.graph)

		seqResult := BfsSequential(g1, tc.start)
		parResult := BfsParallel(g2, tc.start)

		if resultsEqual(seqResult, parResult) {
			passed++
			details = append(details, fmt.Sprintf("✓ %s: PASS (len=%d)", tc.name, len(seqResult)))
		} else {
			failed++
			details = append(details, fmt.Sprintf("✗ %s: FAIL (seq_len=%d, par_len=%d)", tc.name, len(seqResult), len(parResult)))
			if len(seqResult) <= 20 && len(parResult) <= 20 {
				details = append(details, fmt.Sprintf("  seq: %v", seqResult))
				details = append(details, fmt.Sprintf("  par: %v", parResult))
			}
		}
	}

	return passed, failed, details
}

func runDeterminismTests() (int, int, []string) {
	cases := buildTestCases()
	passed := 0
	failed := 0
	details := []string{}

	for _, tc := range cases {
		// Run parallel version 3 times
		g1 := copyGraph(tc.graph)
		g2 := copyGraph(tc.graph)
		g3 := copyGraph(tc.graph)

		run1 := BfsParallel(g1, tc.start)
		run2 := BfsParallel(g2, tc.start)
		run3 := BfsParallel(g3, tc.start)

		hash1 := hashResult(run1)
		hash2 := hashResult(run2)
		hash3 := hashResult(run3)

		if hash1 == hash2 && hash2 == hash3 {
			passed++
			details = append(details, fmt.Sprintf("✓ %s: DETERMINISTIC (hash=%s...)", tc.name, hash1[:16]))
		} else {
			failed++
			details = append(details, fmt.Sprintf("✗ %s: NON-DETERMINISTIC", tc.name))
			details = append(details, fmt.Sprintf("  hash1: %s", hash1[:16]))
			details = append(details, fmt.Sprintf("  hash2: %s", hash2[:16]))
			details = append(details, fmt.Sprintf("  hash3: %s", hash3[:16]))
		}
	}

	return passed, failed, details
}

func copyGraph(g Graph) Graph {
	newGraph := Graph{Vertices: make(map[int][]int)}
	for k, v := range g.Vertices {
		newGraph.Vertices[k] = append([]int{}, v...)
	}
	return newGraph
}
