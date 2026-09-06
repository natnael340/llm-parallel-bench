package bfs_test

import (
	"fmt"
	"reflect"
	"testing"

	benchutil "github.com/natnael340/llm-parallel-bench/tests/bench_utils/go"
	staging "github.com/natnael340/llm-parallel-bench/tests/bfs/go/staging"
)

func TestBFSEmptyGraph(t *testing.T) {
	g := staging.Graph{}
	result := staging.BenchBfs(g, 1)
	if !reflect.DeepEqual(result, []int{}) {
		t.Errorf("Expected %v, but got %v", []int{}, result)
	}
}

func TestBFSSingleNode(t *testing.T) {
	g := staging.Graph{}
	g.AddEdge(1, 1)
	result := staging.BenchBfs(g, 1)
	expected := []int{1}
	if !reflect.DeepEqual(result, expected) {
		t.Errorf("Expected %v, but got %v", expected, result)
	}
}

func TestBFSLinearEdge(t *testing.T) {
	g := staging.Graph{}
	g.AddEdge(1, 2)
	g.AddEdge(2, 3)
	g.AddEdge(3, 4)
	result := staging.BenchBfs(g, 1)
	expected := []int{1, 2, 3, 4}
	if !reflect.DeepEqual(result, expected) {
		t.Errorf("Expected %v, but got %v", expected, result)
	}
}

func TestBFSCompleteGraph(t *testing.T) {
	g := staging.Graph{}
	nodes := []int{1, 2, 3, 4}
	for _, i := range nodes {
		for _, j := range nodes {
			if i != j {
				g.AddEdge(i, j)
			}
		}
	}
	result := staging.BenchBfs(g, 3)
	expected := []int{3, 1, 2, 4}
	if !reflect.DeepEqual(result, expected) {
		t.Errorf("Expected %v, but got %v", expected, result)
	}
}

func TestBFSStarGraph(t *testing.T) {
	g := staging.Graph{}
	center := 1
	leaves := []int{2, 3, 4, 5}
	for _, leaf := range leaves {
		g.AddEdge(center, leaf)
	}
	result := staging.BenchBfs(g, center)
	expected := append([]int{center}, leaves...)
	if !reflect.DeepEqual(result, expected) {
		t.Errorf("Expected %v, but got %v", expected, result)
	}
}

func TestBFSCycle(t *testing.T) {
	g := staging.Graph{}
	edges := [][2]int{{1, 2}, {2, 3}, {3, 4}, {4, 1}}
	for _, e := range edges {
		g.AddEdge(e[0], e[1])
	}
	result := staging.BenchBfs(g, 1)
	expected := []int{1, 2, 4, 3}
	if !reflect.DeepEqual(result, expected) {
		t.Errorf("Expected %v, but got %v", expected, result)
	}
}

func TestBFSTreeStructure(t *testing.T) {
	g := staging.Graph{}
	edges := [][2]int{{1, 2}, {1, 3}, {2, 4}, {2, 5}, {3, 6}, {3, 7}}
	for _, e := range edges {
		g.AddEdge(e[0], e[1])
	}
	result := staging.BenchBfs(g, 1)
	expected := []int{1, 2, 3, 4, 5, 6, 7}
	if !reflect.DeepEqual(result, expected) {
		t.Errorf("Expected %v, but got %v", expected, result)
	}
}

func TestBFSDisconnectedComponents(t *testing.T) {
	g := staging.Graph{}
	g.AddEdge(1, 2)
	g.AddEdge(2, 3)
	g.AddEdge(4, 5)
	g.AddEdge(4, 6)
	result := staging.BenchBfs(g, 1)
	expected := []int{1, 2, 3}
	if !reflect.DeepEqual(result, expected) {
		t.Errorf("Expected %v, but got %v", expected, result)
	}
	result2 := staging.BenchBfs(g, 4)
	expected2 := []int{4, 5, 6}
	if !reflect.DeepEqual(result2, expected2) {
		t.Errorf("Expected %v, but got %v", expected2, result2)
	}
}

func TestBFSDuplicateEdges(t *testing.T) {
	g := staging.Graph{}
	g.AddEdge(1, 2)
	g.AddEdge(1, 2) // Duplicate
	g.AddEdge(2, 3)
	result := staging.BenchBfs(g, 1)
	expected := []int{1, 2, 3}
	if !reflect.DeepEqual(result, expected) {
		t.Errorf("Expected %v, but got %v", expected, result)
	}
}

func TestBFSNonexistentStartVertex(t *testing.T) {
	g := staging.Graph{}
	g.AddEdge(1, 2)
	result := staging.BenchBfs(g, 999)
	expected := []int{}
	if !reflect.DeepEqual(result, expected) {
		t.Errorf("Expected %v, but got %v", expected, result)
	}
}

func TestBFSComplexGraph(t *testing.T) {
	g := staging.Graph{}
	edges := [][2]int{
		{1, 2}, {1, 3}, {2, 4}, {3, 4}, {4, 5},
		{5, 6}, {6, 7}, {5, 7}, {7, 8}, {3, 8},
	}
	for _, e := range edges {
		g.AddEdge(e[0], e[1])
	}
	result := staging.BenchBfs(g, 1)
	expected := []int{1, 2, 3, 4, 8, 5, 7, 6}
	if !reflect.DeepEqual(result, expected) {
		t.Errorf("Expected %v, but got %v", expected, result)
	}
}

func TestBFSOrderConsistency(t *testing.T) {
	g := staging.Graph{}
	g.AddEdge(1, 3)
	g.AddEdge(1, 2)
	var results [][]int
	for i := 0; i < 5; i++ {
		results = append(results, staging.BenchBfs(g, 1))
	}
	for i := 1; i < len(results); i++ {
		if !reflect.DeepEqual(results[0], results[i]) {
			t.Errorf("Order inconsistent: %v vs %v", results[0], results[i])
		}
	}
}

func TestUnorderedNeighbors(t *testing.T) {
	g := staging.Graph{}
	g.AddEdge(1, 3)
	g.AddEdge(1, 2)
	result := staging.BenchBfs(g, 1)
	expected := []int{1, 3, 2}
	if !reflect.DeepEqual(result, expected) {
		t.Errorf("Expected %v, but got %v", expected, result)
	}
}

func TestBFSPerformanceStressTest(t *testing.T) {
	g := staging.Graph{}
	size := 1000
	for i := 1; i < size; i++ {
		g.AddEdge(i, i+1)
	}
	result := staging.BenchBfs(g, 1)
	if len(result) != size {
		t.Errorf("Expected length %d, got %d", size, len(result))
	}
	if result[0] != 1 {
		t.Errorf("Expected first element 1, got %d", result[0])
	}
	if result[len(result)-1] != size {
		t.Errorf("Expected last element %d, got %d", size, result[len(result)-1])
	}
}

func TestBFSSpeed(t *testing.T) {
	g := staging.Graph{}
	size := 2000
	for i := 1; i <= size; i++ {
		for j := i + 1; j <= size; j++ {
			g.AddEdge(i, j)
			g.AddEdge(j, i)
		}
	}

	reps := benchutil.Reps(5)
	iters := benchutil.Iters(20)

	r := benchutil.RunBenchmark(func() { staging.BenchBfs(g, 1) }, reps, iters, 1)

	undirected := int64(size) * (int64(size) - 1) / 2
	directed := int64(size) * (int64(size) - 1)
	label := fmt.Sprintf("BFS complete graph | nodes=%d, undirected edges≈%d (directed≈%d)",
		size, undirected, directed)
	t.Log(benchutil.FormatResult(label, r))

	params := map[string]interface{}{"graph_size": size, "graph_kind": "complete"}
	if err := benchutil.WriteResult(benchutil.Out(), r, "bfs", benchutil.Impl(), params); err != nil {
		t.Fatalf("failed to write result JSON: %v", err)
	}
}
