package sccs_test

import (
	"fmt"
	"math/rand"
	"strings"
	"testing"
	"time"

	benchutil "github.com/natnael340/llm-parallel-bench/tests/bench_utils/go"
	staging "github.com/natnael340/llm-parallel-bench/tests/sccs/go/staging"
)

// isSccStrong validates SCC reduction against the professor heuristic.
// For SCC of size k>1:
//   - at least (k-1) internal edges (forward spanning tree)
//   - at most 2*(k-1) internal edges (forward + reverse trees)
//   - every SCC node appears in at least one kept internal edge
func isSccStrong(sccNodes []int, edges []staging.Edge) bool {
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

func checkAllSCCs(sccs [][]int, edges []staging.Edge) bool {
	for _, scc := range sccs {
		if !isSccStrong(scc, edges) {
			return false
		}
	}
	return true
}

// Test 1: empty graph - should not panic
func TestEmptyGraph(t *testing.T) {
	g := staging.BenchNewGraph(0)
	_ = staging.BenchReduceEdges(g)
}

// Test 2: single node, no edges
func TestSingleNodeNoEdges(t *testing.T) {
	g := staging.BenchNewGraph(1)
	edges := staging.BenchReduceEdges(g)
	sccs := g.FindSCCs()
	if !checkAllSCCs(sccs, edges) {
		t.Fatal("single node no edges: SCC strong check failed")
	}
}

// Test 3: single node, self-loop
func TestSingleNodeSelfLoop(t *testing.T) {
	g := staging.BenchNewGraph(1)
	g.AddEdge(0, 0)
	edges := staging.BenchReduceEdges(g)
	sccs := g.FindSCCs()
	if !checkAllSCCs(sccs, edges) {
		t.Fatal("single node self-loop: SCC strong check failed")
	}
}

// Test 4: simple 3-cycle 0->1->2->0
func TestSimple3Cycle(t *testing.T) {
	g := staging.BenchNewGraph(3)
	g.AddEdge(0, 1)
	g.AddEdge(1, 2)
	g.AddEdge(2, 0)
	edges := staging.BenchReduceEdges(g)
	sccs := g.FindSCCs()
	if !checkAllSCCs(sccs, edges) {
		t.Fatalf("simple 3-cycle: SCC strong check failed\n  reduced edges: %v", edges)
	}
}

// Test 5: two-node mutual SCC
func Test2NodeMutualSCC(t *testing.T) {
	g := staging.BenchNewGraph(2)
	g.AddEdge(0, 1)
	g.AddEdge(1, 0)
	edges := staging.BenchReduceEdges(g)
	sccs := g.FindSCCs()
	if !checkAllSCCs(sccs, edges) {
		t.Fatal("2-node mutual SCC: SCC strong check failed")
	}
}

// Test 6: dense 3-node SCC (0->1->2->0 plus 0->2, 1->0, 2->1)
func TestDense3NodeSCC(t *testing.T) {
	g := staging.BenchNewGraph(3)
	g.AddEdge(0, 1)
	g.AddEdge(1, 2)
	g.AddEdge(2, 0)
	g.AddEdge(0, 2)
	g.AddEdge(1, 0)
	g.AddEdge(2, 1)
	edges := staging.BenchReduceEdges(g)
	sccs := g.FindSCCs()
	if !checkAllSCCs(sccs, edges) {
		t.Fatalf("dense 3-node SCC: SCC strong check failed\n  reduced edges: %v", edges)
	}
}

// Test 7: multiple SCCs
// SCC1: 0->1->2->0, SCC2: 3<->4, cross: 2->3
func TestMultipleSCCs(t *testing.T) {
	g := staging.BenchNewGraph(5)
	// SCC1
	g.AddEdge(0, 1)
	g.AddEdge(1, 2)
	g.AddEdge(2, 0)
	// SCC2
	g.AddEdge(3, 4)
	g.AddEdge(4, 3)
	// cross
	g.AddEdge(2, 3)
	edges := staging.BenchReduceEdges(g)
	sccs := g.FindSCCs()
	if !checkAllSCCs(sccs, edges) {
		t.Fatalf("multiple SCCs: SCC strong check failed\n  reduced edges: %v", edges)
	}
}

// Test 8: 7-node example graph
func Test7NodeGraph(t *testing.T) {
	g := staging.BenchNewGraph(7)
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
	edges := staging.BenchReduceEdges(g)
	sccs := g.FindSCCs()
	if !checkAllSCCs(sccs, edges) {
		t.Fatalf("7-node graph: SCC strong check failed\n  reduced edges: %v", edges)
	}
}

// Test 9: determinism - randomized large multi-SCC graph, output must be identical across runs
func TestDeterminism(t *testing.T) {
	numScc := 24
	sccSize := 40
	n := numScc * sccSize
	runs := 5

	buildTestGraph := func(seed int64) *staging.Graph {
		r := rand.New(rand.NewSource(seed))
		g := staging.BenchNewGraph(n)

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

	edgeSignature := func(edges []staging.Edge) string {
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
		edges := staging.BenchReduceEdges(g)

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
	}
}

// --- benchmark graph construction (shared with all languages) ---

func ringSCC(start, end int, g *staging.Graph) {
	for i := start; i < end; i++ {
		v := (i + 1) % end
		if v == 0 {
			v = start
		}
		if i == v {
			continue
		}
		g.AddEdge(i, v)
	}
}

func min(a, b int) int {
	if a < b {
		return a
	}
	return b
}

func buildBenchGraph(graphSize, clusterSize, noClusterInGroup int) *staging.Graph {
	rand.Seed(43)
	g := staging.BenchNewGraph(graphSize)

	for i := 0; i < graphSize; i += clusterSize {
		ringSCC(i, min(i+clusterSize, graphSize), g)

		currentCluster := i / clusterSize
		if currentCluster/noClusterInGroup == (currentCluster+1)/noClusterInGroup {
			if (i + clusterSize) < graphSize {
				endA := min(i+clusterSize, graphSize)
				endB := min(i+2*clusterSize, graphSize)
				u := i + rand.Intn(endA-i)
				v := endA + rand.Intn(endB-endA)
				g.AddEdge(u, v)
			}
		}
	}
	return g
}

func TestSCCSpeed(t *testing.T) {
	graphSize := 100000
	clusterSize := 300
	noClusterInGroup := 3

	g := buildBenchGraph(graphSize, clusterSize, noClusterInGroup)

	reps := benchutil.Reps(5)
	iters := benchutil.Iters(20)

	r := benchutil.RunBenchmark(func() { staging.BenchReduceEdges(g) }, reps, iters, 1)

	label := fmt.Sprintf("SCC ReduceEdges | graph_size=%d", graphSize)
	t.Log(benchutil.FormatResult(label, r))

	params := map[string]interface{}{
		"graph_size":          graphSize,
		"cluster_size":        clusterSize,
		"no_cluster_in_group": noClusterInGroup,
	}
	if err := benchutil.WriteResult(benchutil.Out(), r, "sccs", benchutil.Impl(), params); err != nil {
		t.Fatalf("failed to write result JSON: %v", err)
	}
}
