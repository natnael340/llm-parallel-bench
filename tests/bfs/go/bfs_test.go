package bfs_seq_test

import (
	"encoding/json"
	"fmt"
	"os"
	"reflect"
	"sort"
	"testing"
	"time"

	//bfsgo "github.com/natnael340/llm-parallel-bench/BFS/bfsgo"
	bfsgo "github.com/natnael340/llm-parallel-bench/llm_written/gpt-5/bfs/go"
)

func medianF(vals []float64) float64 {
	s := make([]float64, len(vals))
	copy(s, vals)
	sort.Float64s(s)
	n := len(s)
	if n%2 == 0 {
		return (s[n/2-1] + s[n/2]) / 2.0
	}
	return s[n/2]
}

func iqrF(vals []float64) float64 {
	s := make([]float64, len(vals))
	copy(s, vals)
	sort.Float64s(s)
	n := len(s)
	q1 := s[int(float64(n-1)*0.25)]
	q3 := s[int(float64(n-1)*0.75)]
	return q3 - q1
}

func TestBFSEmptyGraph(t *testing.T) {
	g := bfsgo.Graph{}
	result := bfsgo.BfsParallel(g, 1)
	if !reflect.DeepEqual(result, []int{}) {
		t.Errorf("Expected %v, but got %v", []int{}, result)
	}
}

func TestBFSSingleNode(t *testing.T) {
	g := bfsgo.Graph{}
	g.AddEdge(1, 1)
	result := bfsgo.BfsParallel(g, 1)
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
	result := bfsgo.BfsParallel(g, 1)
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
	result := bfsgo.BfsParallel(g, 3)
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
	result := bfsgo.BfsParallel(g, center)
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
	result := bfsgo.BfsParallel(g, 1)
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
	result := bfsgo.BfsParallel(g, 1)
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
	result := bfsgo.BfsParallel(g, 1)
	expected := []int{1, 2, 3}
	if !reflect.DeepEqual(result, expected) {
		t.Errorf("Expected %v, but got %v", expected, result)
	}
	result2 := bfsgo.BfsParallel(g, 4)
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
	result := bfsgo.BfsParallel(g, 1)
	expected := []int{1, 2, 3}
	if !reflect.DeepEqual(result, expected) {
		t.Errorf("Expected %v, but got %v", expected, result)
	}
}

func TestBFSNonexistentStartVertex(t *testing.T) {
	g := bfsgo.Graph{}
	g.AddEdge(1, 2)
	result := bfsgo.BfsParallel(g, 999)
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
	result := bfsgo.BfsParallel(g, 1)
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
		results = append(results, bfsgo.BfsParallel(g, 1))
	}
	for i := 1; i < len(results); i++ {
		if !reflect.DeepEqual(results[0], results[i]) {
			t.Errorf("Order inconsistent: %v vs %v", results[0], results[i])
		}
	}
}

func TestUnorderedNeighbors(t *testing.T) {
	// build the graph from the remaining lines
	g := bfsgo.Graph{}
	g.AddEdge(1, 3)
	g.AddEdge(1, 2)
	result := bfsgo.BfsParallel(g, 1)
	expected := []int{1, 3, 2}
	if !reflect.DeepEqual(result, expected) {
		t.Errorf("Expected %v, but got %v", expected, result)
	}
}

func TestBFSPerformanceStressTest(t *testing.T) {
	g := bfsgo.Graph{}
	size := 1000
	for i := 1; i < size; i++ {
		g.AddEdge(i, i+1)
	}
	result := bfsgo.BfsParallel(g, 1)
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
	g := bfsgo.Graph{}
	size := 2000
	for i := 1; i <= size; i++ {
		for j := i + 1; j <= size; j++ {
			g.AddEdge(i, j)
			g.AddEdge(j, i)
		}
	}

	// warmup
	for i := 0; i < 1; i++ {
		bfsgo.BfsParallel(g, 1)
	}

	reps := 5
	iters := 20

	perRunMs := make([]float64, reps)
	for r := 0; r < reps; r++ {
		start := time.Now()
		for k := 0; k < iters; k++ {
			bfsgo.BfsParallel(g, 1)
		}
		total := time.Since(start)
		perRunMs[r] = (float64(total.Nanoseconds()) / 1e6) / float64(iters)
	}

	med := medianF(perRunMs)
	spread := iqrF(perRunMs)

	undirected := int64(size) * (int64(size) - 1) / 2
	directed := int64(size) * (int64(size) - 1)

	msg := fmt.Sprintf(
		"BFS complete graph | nodes=%d, undirected edges≈%d (directed≈%d) | %.2f ms/run ± %.2f IQR (n=%d)",
		size, undirected, directed, med, spread, reps,
	)
	t.Logf(msg)

	if out := os.Getenv("BENCH_OUT"); out != "" {
		impl := os.Getenv("IMPL")
		if impl == "" {
			impl = "par"
		}
		result := map[string]interface{}{
			"algo":         "bfs",
			"lang":         "go",
			"impl":         impl,
			"elapsed_ms":   perRunMs,
			"median":       med,
			"iqr":          spread,
			"reps":         reps,
			"iters_per_rep": iters,
		}
		data, _ := json.MarshalIndent(result, "", "  ")
		os.WriteFile(out, data, 0644)
	}
}
