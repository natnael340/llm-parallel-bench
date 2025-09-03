package bfs_seq_test

import (
	"testing"
	"reflect"
	"time"
	"math"
	//"github.com/natnael340/llm-parallel-bench/BFS/bfsgo"
	bfsgo "github.com/natnael340/llm-parallel-bench/llm_written"
)

func TestBFSEmptyGraph(t *testing.T) {
	g := bfsgo.Graph{}
	result := bfsgo.Bfs(g, 1)
	if !reflect.DeepEqual(result, []int{}) {
		t.Errorf("Expected %v, but got %v", []int{}, result)
	}
}

func TestBFSSingleNode(t *testing.T) {
	g := bfsgo.Graph{}
	g.AddEdge(1, 1)
	result := bfsgo.Bfs(g, 1)
	expected := []int{1}
	if !reflect.DeepEqual(result, expected) {
		t.Errorf("Expected %v, but got %v", expected, result)
	}
}

func TestBFSLinearEdge(t *testing.T) {
	g := bfsgo.Graph{}
	g.AddEdge(1, 2)
	g.AddEdge(2, 3)
	g.AddEdge(3, 4)
	result := bfsgo.Bfs(g, 1)
	expected := []int{1, 2, 3, 4}
	if !reflect.DeepEqual(result, expected) {
		t.Errorf("Expected %v, but got %v", expected, result)
	}
}

func TestBFSCompleteGraph(t *testing.T) {
	g := bfsgo.Graph{}
	nodes := []int{1, 2, 3, 4}
	for _, i := range nodes {
		for _, j := range nodes {
			if i != j {
				g.AddEdge(i, j)
			}
		}
	}
	result := bfsgo.Bfs(g, 3)
	expected := []int{3, 1, 2, 4}
	if !reflect.DeepEqual(result, expected) {
		t.Errorf("Expected %v, but got %v", expected, result)
	}
}

func TestBFSStarGraph(t *testing.T) {
	g := bfsgo.Graph{}
	center := 1
	leaves := []int{2, 3, 4, 5}
	for _, leaf := range leaves {
		g.AddEdge(center, leaf)
	}
	result := bfsgo.Bfs(g, center)
	expected := append([]int{center}, leaves...)
	if !reflect.DeepEqual(result, expected) {
		t.Errorf("Expected %v, but got %v", expected, result)
	}
}

func TestBFSCycle(t *testing.T) {
	g := bfsgo.Graph{}
	edges := [][2]int{{1, 2}, {2, 3}, {3, 4}, {4, 1}}
	for _, e := range edges {
		g.AddEdge(e[0], e[1])
	}
	result := bfsgo.Bfs(g, 1)
	expected := []int{1, 2, 4, 3}
	if !reflect.DeepEqual(result, expected) {
		t.Errorf("Expected %v, but got %v", expected, result)
	}
}

func TestBFSTreeStructure(t *testing.T) {
	g := bfsgo.Graph{}
	edges := [][2]int{{1, 2}, {1, 3}, {2, 4}, {2, 5}, {3, 6}, {3, 7}}
	for _, e := range edges {
		g.AddEdge(e[0], e[1])
	}
	result := bfsgo.Bfs(g, 1)
	expected := []int{1, 2, 3, 4, 5, 6, 7}
	if !reflect.DeepEqual(result, expected) {
		t.Errorf("Expected %v, but got %v", expected, result)
	}
}

func TestBFSDisconnectedComponents(t *testing.T) {
	g := bfsgo.Graph{}
	g.AddEdge(1, 2)
	g.AddEdge(2, 3)
	g.AddEdge(4, 5)
	g.AddEdge(4, 6)
	result := bfsgo.Bfs(g, 1)
	expected := []int{1, 2, 3}
	if !reflect.DeepEqual(result, expected) {
		t.Errorf("Expected %v, but got %v", expected, result)
	}
	result2 := bfsgo.Bfs(g, 4)
	expected2 := []int{4, 5, 6}
	if !reflect.DeepEqual(result2, expected2) {
		t.Errorf("Expected %v, but got %v", expected2, result2)
	}
}

func TestBFSDuplicateEdges(t *testing.T) {
	g := bfsgo.Graph{}
	g.AddEdge(1, 2)
	g.AddEdge(1, 2) // Duplicate
	g.AddEdge(2, 3)
	result := bfsgo.Bfs(g, 1)
	expected := []int{1, 2, 3}
	if !reflect.DeepEqual(result, expected) {
		t.Errorf("Expected %v, but got %v", expected, result)
	}
}

func TestBFSNonexistentStartVertex(t *testing.T) {
	g := bfsgo.Graph{}
	g.AddEdge(1, 2)
	result := bfsgo.Bfs(g, 999)
	expected := []int{}
	if !reflect.DeepEqual(result, expected) {
		t.Errorf("Expected %v, but got %v", expected, result)
	}
}

func TestBFSComplexGraph(t *testing.T) {
	g := bfsgo.Graph{}
	edges := [][2]int{
		{1, 2}, {1, 3}, {2, 4}, {3, 4}, {4, 5},
		{5, 6}, {6, 7}, {5, 7}, {7, 8}, {3, 8},
	}
	for _, e := range edges {
		g.AddEdge(e[0], e[1])
	}
	result := bfsgo.Bfs(g, 1)
	expected := []int{1, 2, 3, 4, 8, 5, 7, 6}
	if !reflect.DeepEqual(result, expected) {
		t.Errorf("Expected %v, but got %v", expected, result)
	}
}

func TestBFSOrderConsistency(t *testing.T) {
	g := bfsgo.Graph{}
	g.AddEdge(1, 3)
	g.AddEdge(1, 2)
	var results [][]int
	for i := 0; i < 5; i++ {
		results = append(results, bfsgo.Bfs(g, 1))
	}
	for i := 1; i < len(results); i++ {
		if !reflect.DeepEqual(results[0], results[i]) {
			t.Errorf("Order inconsistent: %v vs %v", results[0], results[i])
		}
	}
}

func TestBFSPerformanceStressTest(t *testing.T) {
	g := bfsgo.Graph{}
	size := 1000
	for i := 1; i < size; i++ {
		g.AddEdge(i, i+1)
	}
	result := bfsgo.Bfs(g, 1)
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
	// Create a large graph for benchmarking

	g := bfsgo.Graph{}
	size := 100000
	for i := 1; i <= size; i++ {
		for j := 1; j <= 10; j++ {
			g.AddEdge(i, int(math.Min(float64(i+j), float64(size-i))))
		}
	}

	times := []int64{}

	for i := 0; i < 100; i++ {
		start := time.Now()
		bfsgo.Bfs(g, 1)
		duration := time.Since(start)
		times = append(times, duration.Milliseconds())
	}
	// calculate average
	var total float64
	for _, t := range times {
		total += float64(t)
	}
	
	t.Logf("BFS took %v ms.", total / 100.0)
}
