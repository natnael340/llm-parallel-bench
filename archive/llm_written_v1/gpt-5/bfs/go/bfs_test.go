package llm_written_test

import (
	"math"
	"math/rand"
	"testing"
	"time"

	bfs "github.com/natnael340/llm-parallel-bench/llm_written"
)

func equal(a, b []int) bool {
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

func buildRandomGraph(n, m int, seed int64) bfs.Graph {
	rng := rand.New(rand.NewSource(seed))
	g := bfs.Graph{Vertices: make(map[int][]int)}
	for i := 0; i < m; i++ {
		u := rng.Intn(n)
		v := rng.Intn(n)
		if u == v { continue }
		g.AddEdge(u, v)
	}
	return g
}

func TestParityAndDeterminism(t *testing.T) {
	seeds := []int64{1, 2, 3, 123456789, 987654321}
	for _, seed := range seeds {
		g := buildRandomGraph(200, 800, seed)
		p1 := bfs.BfsParallel(g, 0)
		s := bfs.BfsSequential(g, 0)
		p2 := bfs.BfsParallel(g, 0)
		if !equal(p1, s) {
			t.Fatalf("parallel result differs from sequential for seed %d", seed)
		}
		if !equal(p1, p2) {
			t.Fatalf("parallel run nondeterministic for seed %d", seed)
		}
	}
}

func TestEdgeCases(t *testing.T) {
	// empty graph
	{
		g := bfs.Graph{Vertices: map[int][]int{}}
		if r := bfs.BfsParallel(g, 0); len(r) != 0 { t.Fatalf("expected empty, got %v", r) }
		if r := bfs.BfsSequential(g, 0); len(r) != 0 { t.Fatalf("expected empty, got %v", r) }
	}
	// start not present
	{
		g := bfs.Graph{Vertices: make(map[int][]int)}
		g.AddEdge(1, 2)
		if r := bfs.BfsParallel(g, 42); len(r) != 0 { t.Fatalf("expected empty, got %v", r) }
		if r := bfs.BfsSequential(g, 42); len(r) != 0 { t.Fatalf("expected empty, got %v", r) }
	}
	// simple line
	{
		g := bfs.Graph{Vertices: make(map[int][]int)}
		for i := 0; i < 10; i++ {
			g.AddEdge(i, i+1)
		}
		p := bfs.BfsParallel(g, 0)
		s := bfs.BfsSequential(g, 0)
		if !equal(p, s) { t.Fatalf("line graph mismatch") }
	}
}

func TestBFSSpeed(t *testing.T) {
	g := bfs.Graph{}
	size := 20000
	for i := 1; i <= size; i++ {
		for j := 1; j <= 10; j++ {
			to := int(math.Min(float64(i+j), float64(size)))
			g.AddEdge(i, to)
		}
	}

	times := []int64{}
	for i := 0; i < 10; i++ {
		start := time.Now()
		_ = bfs.BfsParallel(g, 1)
		duration := time.Since(start)
		times = append(times, duration.Milliseconds())
	}
	var total int64
	for _, tt := range times { total += tt }
	t.Logf("BFS took %v ms avg over %d runs", float64(total)/float64(len(times)), len(times))
}
