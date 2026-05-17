package main

import (
	"fmt"
	"math/rand"
	"os"
	"strings"
	"testing"
	"time"

	graphpar "github.com/natnael340/llm-parallel-bench/scc/scssgo/par"
	graphseq "github.com/natnael340/llm-parallel-bench/scc/scssgo/seq"
)

// Edge is the local edge type used across all test helpers.
type Edge struct{ U, V int }

// sccGraph is the interface satisfied by both graphseq.Graph and graphpar.Graph.
type sccGraph interface {
	AddEdge(v, w int)
	FindSCCs() [][]int
}

// newGraph and reduceEdges are wired up in init() based on ALGO env var.
var (
	newGraph    func(int) sccGraph
	reduceEdges func(sccGraph) []Edge
)

func init() {
	algo := strings.ToLower(os.Getenv("ALGO"))
	if algo == "par" {
		newGraph = func(v int) sccGraph { return graphpar.NewGraph(v) }
		reduceEdges = func(g sccGraph) []Edge {
			raw := g.(*graphpar.Graph).ReduceEdges()
			out := make([]Edge, len(raw))
			for i, e := range raw {
				out[i] = Edge{e.U, e.V}
			}
			return out
		}
	} else {
		newGraph = func(v int) sccGraph { return graphseq.NewGraph(v) }
		reduceEdges = func(g sccGraph) []Edge {
			raw := g.(*graphseq.Graph).ReduceEdges()
			out := make([]Edge, len(raw))
			for i, e := range raw {
				out[i] = Edge{e.U, e.V}
			}
			return out
		}
	}
}

// isSccStrong validates SCC reduction against the professor heuristic.
// For SCC of size k>1:
//   - at least (k-1) internal edges (forward spanning tree)
//   - at most 2*(k-1) internal edges (forward + reverse trees)
//   - every SCC node appears in at least one kept internal edge
func isSccStrong(sccNodes []int, edges []Edge) bool {
	nodeSet := make(map[int]bool, len(sccNodes))
	for _, n := range sccNodes {
		nodeSet[n] = true
	}
	k := len(sccNodes)
	if k <= 1 {
		return true
	}

	internalEdges := 0
	touched := make(map[int]bool)
	for _, e := range edges {
		if nodeSet[e.U] && nodeSet[e.V] {
			internalEdges++
			touched[e.U] = true
			touched[e.V] = true
		}
	}

	if internalEdges < k-1 {
		return false
	}
	if internalEdges > 2*(k-1) {
		return false
	}
	if len(touched) < k {
		return false
	}
	return true
}

func checkAllSCCs(sccs [][]int, edges []Edge) bool {
	for _, scc := range sccs {
		if !isSccStrong(scc, edges) {
			return false
		}
	}
	return true
}

// Test 1: empty graph - should not panic
func TestEmptyGraph(t *testing.T) {
	g := newGraph(0)
	_ = reduceEdges(g)
}

// Test 2: single node, no edges
func TestSingleNodeNoEdges(t *testing.T) {
	g := newGraph(1)
	edges := reduceEdges(g)
	sccs := g.FindSCCs()
	if !checkAllSCCs(sccs, edges) {
		t.Fatal("single node no edges: SCC strong check failed")
	}
}

// Test 3: single node, self-loop
func TestSingleNodeSelfLoop(t *testing.T) {
	g := newGraph(1)
	g.AddEdge(0, 0)
	edges := reduceEdges(g)
	sccs := g.FindSCCs()
	if !checkAllSCCs(sccs, edges) {
		t.Fatal("single node self-loop: SCC strong check failed")
	}
}

// Test 4: simple 3-cycle 0->1->2->0
func TestSimple3Cycle(t *testing.T) {
	g := newGraph(3)
	g.AddEdge(0, 1)
	g.AddEdge(1, 2)
	g.AddEdge(2, 0)
	edges := reduceEdges(g)
	sccs := g.FindSCCs()
	if !checkAllSCCs(sccs, edges) {
		t.Fatalf("simple 3-cycle: SCC strong check failed\n  reduced edges: %v", edges)
	}
}

// Test 5: two-node mutual SCC
func Test2NodeMutualSCC(t *testing.T) {
	g := newGraph(2)
	g.AddEdge(0, 1)
	g.AddEdge(1, 0)
	edges := reduceEdges(g)
	sccs := g.FindSCCs()
	if !checkAllSCCs(sccs, edges) {
		t.Fatal("2-node mutual SCC: SCC strong check failed")
	}
}

// Test 6: dense 3-node SCC (0->1->2->0 plus 0->2, 1->0, 2->1)
func TestDense3NodeSCC(t *testing.T) {
	g := newGraph(3)
	g.AddEdge(0, 1)
	g.AddEdge(1, 2)
	g.AddEdge(2, 0)
	g.AddEdge(0, 2)
	g.AddEdge(1, 0)
	g.AddEdge(2, 1)
	edges := reduceEdges(g)
	sccs := g.FindSCCs()
	if !checkAllSCCs(sccs, edges) {
		t.Fatalf("dense 3-node SCC: SCC strong check failed\n  reduced edges: %v", edges)
	}
}

// Test 7: multiple SCCs
// SCC1: 0->1->2->0, SCC2: 3<->4, cross: 2->3
func TestMultipleSCCs(t *testing.T) {
	g := newGraph(5)
	// SCC1
	g.AddEdge(0, 1)
	g.AddEdge(1, 2)
	g.AddEdge(2, 0)
	// SCC2
	g.AddEdge(3, 4)
	g.AddEdge(4, 3)
	// cross
	g.AddEdge(2, 3)
	edges := reduceEdges(g)
	sccs := g.FindSCCs()
	if !checkAllSCCs(sccs, edges) {
		t.Fatalf("multiple SCCs: SCC strong check failed\n  reduced edges: %v", edges)
	}
}

// Test 8: 7-node example graph
func Test7NodeGraph(t *testing.T) {
	g := newGraph(7)
	g.AddEdge(0, 1)
	g.AddEdge(1, 2)
	g.AddEdge(1, 3)
	g.AddEdge(1, 4)
	g.AddEdge(2, 0)
	g.AddEdge(2, 3)
	g.AddEdge(3, 5)
	g.AddEdge(5, 3)
	g.AddEdge(5, 4)
	g.AddEdge(5, 6)
	g.AddEdge(6, 4)
	g.AddEdge(4, 6)
	edges := reduceEdges(g)
	sccs := g.FindSCCs()
	if !checkAllSCCs(sccs, edges) {
		t.Fatalf("7-node graph: SCC strong check failed\n  reduced edges: %v", edges)
	}
}

// Test 9: stress + performance (n=2000, ring + jump edges, 5 runs)
func TestStressPerformance(t *testing.T) {
	n := 2000
	runs := 5
	var totalMs int64

	for r := 0; r < runs; r++ {
		g := newGraph(n)
		for i := 0; i < n; i++ {
			g.AddEdge(i, (i+1)%n)
			g.AddEdge(i, (i+13)%n)
		}

		start := time.Now()
		edges := reduceEdges(g)
		elapsed := time.Since(start).Milliseconds()
		totalMs += elapsed

		if len(edges) == 0 {
			t.Errorf("stress run %d: no edges returned", r)
			continue
		}
		t.Logf("stress run %d: edges kept: %d, time: %d ms", r, len(edges), elapsed)

		sccs := g.FindSCCs()
		if !checkAllSCCs(sccs, edges) {
			t.Errorf("stress run %d: reduced edges broke SCC", r)
		}
	}
	t.Logf("average time over %d runs (n=%d): %.3f ms", runs, n, float64(totalMs)/float64(runs))
}

// Test 10: determinism - randomized large multi-SCC graph, output must be identical across runs
func TestDeterminism(t *testing.T) {
	numScc := 24
	sccSize := 40
	n := numScc * sccSize
	runs := 5

	buildTestGraph := func(seed int64) sccGraph {
		r := rand.New(rand.NewSource(seed))
		g := newGraph(n)

		for s := 0; s < numScc; s++ {
			start := s * sccSize
			// Ring backbone to guarantee SCC
			for u := start; u < start+sccSize; u++ {
				next := start + (u-start+1)%sccSize
				g.AddEdge(u, next)
			}
			// Random intra-SCC edges
			for i := 0; i < sccSize*3; i++ {
				u := start + r.Intn(sccSize)
				v := start + r.Intn(sccSize)
				if u != v {
					g.AddEdge(u, v)
				}
			}
		}

		// Forward-only cross-SCC edges
		for s := 0; s < numScc-1; s++ {
			a0 := s * sccSize
			b0 := (s + 1) * sccSize
			for i := 0; i < 6; i++ {
				u := a0 + r.Intn(sccSize)
				v := b0 + r.Intn(sccSize)
				g.AddEdge(u, v)
			}
		}

		return g
	}

	edgeSignature := func(edges []Edge) string {
		parts := make([]string, len(edges))
		for i, e := range edges {
			parts[i] = fmt.Sprintf("%d,%d", e.U, e.V)
		}
		return strings.Join(parts, ";")
	}

	seed := rand.New(rand.NewSource(time.Now().UnixNano())).Int63()
	g := buildTestGraph(seed)
	sccs := g.FindSCCs()

	baseline := ""
	baselineCount := -1
	for r := 0; r < runs; r++ {
		start := time.Now()
		edges := reduceEdges(g)
		elapsed := time.Since(start).Milliseconds()

		if !checkAllSCCs(sccs, edges) {
			t.Errorf("determinism run %d: reduced edges broke SCC", r)
		}

		sig := edgeSignature(edges)
		if r == 0 {
			baseline = sig
			baselineCount = len(edges)
		} else if sig != baseline {
			t.Errorf("determinism run %d: output differs from run 0 (baseline count=%d, this count=%d)", r, baselineCount, len(edges))
		}

		t.Logf("det run %d: seed: %d, SCCs: %d, edges kept: %d, time: %d ms", r, seed, len(sccs), len(edges), elapsed)
	}
}
