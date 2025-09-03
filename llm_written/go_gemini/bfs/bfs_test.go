package llm_written

import (
	"math/rand"
	"reflect"
	"sort"
	"testing"
)

// Helper to create a random graph for testing.
func createRandomGraph(numVertices int, edgeFactor float64) Graph {
	g := Graph{Vertices: make(map[int][]int)}
	// Use a fixed seed for reproducibility
	r := rand.New(rand.NewSource(42))

	if numVertices == 0 {
		return g
	}

	// Ensure all vertices from 0 to numVertices-1 exist
	for i := 0; i < numVertices; i++ {
		if _, ok := g.Vertices[i]; !ok {
			g.Vertices[i] = []int{}
		}
	}

	numEdges := int(float64(numVertices) * edgeFactor)
	for i := 0; i < numEdges; i++ {
		from := r.Intn(numVertices)
		to := r.Intn(numVertices)
		if from != to {
			// Avoid self-loops for simplicity
			exists := false
			for _, neighbor := range g.Vertices[from] {
				if neighbor == to {
					exists = true
					break
				}
			}
			if !exists {
				g.AddEdge(from, to)
			}
		}
	}
	return g
}

func TestBfs(t *testing.T) {
	testCases := []struct {
		name        string
		graph       Graph
		startVertex int
	}{
		{
			name:        "Empty Graph",
			graph:       Graph{Vertices: make(map[int][]int)},
			startVertex: 0,
		},
		{
			name:        "Single Node Graph",
			graph:       Graph{Vertices: map[int][]int{0: {}}},
			startVertex: 0,
		},
		{
			name:        "Start node not in graph",
			graph:       Graph{Vertices: map[int][]int{1: {2}, 2: {1}}},
			startVertex: 0,
		},
		{
			name:        "Disconnected Start Node",
			graph:       Graph{Vertices: map[int][]int{0: {}, 1: {2}, 2: {1}}},
			startVertex: 0,
		},
		{
			name: "Line Graph",
			graph: func() Graph {
				g := Graph{}
				g.AddEdge(0, 1)
				g.AddEdge(1, 2)
				g.AddEdge(2, 3)
				return g
			}(),
			startVertex: 0,
		},
		{
			name: "Simple Cycle",
			graph: func() Graph {
				g := Graph{}
				g.AddEdge(0, 1)
				g.AddEdge(1, 2)
				g.AddEdge(2, 0)
				return g
			}(),
			startVertex: 0,
		},
		{
			name: "Complete Graph K4",
			graph: func() Graph {
				g := Graph{}
				g.AddEdge(0, 1)
				g.AddEdge(0, 2)
				g.AddEdge(0, 3)
				g.AddEdge(1, 2)
				g.AddEdge(1, 3)
				g.AddEdge(2, 3)
				return g
			}(),
			startVertex: 0,
		},
		{
			name:        "Small Graph (below threshold)",
			graph:       createRandomGraph(100, 2.5),
			startVertex: 42,
		},
		{
			name:        "Medium Random Graph (above threshold)",
			graph:       createRandomGraph(200, 2.5),
			startVertex: 0,
		},
		{
			name:        "Large Random Graph",
			graph:       createRandomGraph(1000, 4.0),
			startVertex: 123,
		},
	}

	for _, tc := range testCases {
		t.Run(tc.name, func(t *testing.T) {
			// Run sequential version as the baseline
			seqResult := BfsSequential(tc.graph, tc.startVertex)

			// Run parallel version
			parResult1 := Bfs(tc.graph, tc.startVertex)

			// Run parallel version again to check for determinism
			parResult2 := Bfs(tc.graph, tc.startVertex)

			// 1. Check for determinism
			if !reflect.DeepEqual(parResult1, parResult2) {
				t.Fatalf("Parallel implementation is not deterministic!\nRun 1: %v\nRun 2: %v", parResult1, parResult2)
			}

			// 2. Check for correctness (same set of visited nodes)
			// To compare sets, we sort both result slices.
			sortedSeq := make([]int, len(seqResult))
			copy(sortedSeq, seqResult)
			sort.Ints(sortedSeq)

			sortedPar := make([]int, len(parResult1))
			copy(sortedPar, parResult1)
			sort.Ints(sortedPar)

			if !reflect.DeepEqual(sortedSeq, sortedPar) {
				t.Errorf("The set of visited nodes differs.\n  Sequential (sorted): %v\n  Parallel (sorted):   %v", sortedSeq, sortedPar)
			}
		})
	}
}
