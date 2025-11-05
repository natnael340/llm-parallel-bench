package main

import (
	"crypto/sha256"
	"encoding/hex"
	"fmt"
	"math/rand"
	"os"
	"runtime"
	"sort"
	"time"
)

type Edge struct {
	U, V int
}

type Graph struct {
	V      int
	Adj    [][]int
	RevAdj [][]int
}

func NewGraph(v int) *Graph {
	g := &Graph{
		V:      v,
		Adj:    make([][]int, v),
		RevAdj: make([][]int, v),
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
	*timeRef++
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

// MinimizeEdgesInSCC builds forward and reverse spanning trees within the SCC and
// returns a deterministic, sorted list of unique edges.
func (g *Graph) MinimizeEdgesInSCC(scc []int) []Edge {
	nodes := make(map[int]bool, len(scc))
	for _, n := range scc {
		nodes[n] = true
	}
	if len(scc) == 0 {
		return nil
	}

	// Step 1: forward spanning tree using DFS
	forwardTree := g.buildSpanningTree(scc[0], g.Adj, nodes)

	// Step 2: reverse spanning tree using DFS on reversed graph
	reverseTree := g.buildSpanningTree(scc[0], g.RevAdj, nodes)

	// Step 3: merge both trees (each edge appears at most twice), deterministic order
	set := make(map[Edge]struct{}, len(forwardTree)+len(reverseTree))
	for e := range forwardTree {
		set[e] = struct{}{}
	}
	for e := range reverseTree {
		set[e] = struct{}{}
	}
	out := make([]Edge, 0, len(set))
	for e := range set {
		out = append(out, e)
	}
	sort.Slice(out, func(i, j int) bool {
		if out[i].U == out[j].U {
			return out[i].V < out[j].V
		}
		return out[i].U < out[j].U
	})
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

// ReduceEdgesSequential keeps the original behavior (but returns edges in deterministic order per SCC).
func (g *Graph) ReduceEdgesSequential() []Edge {
	sccs := g.FindSCCs()
	reduced := make([]Edge, 0)
	for _, scc := range sccs {
		minEdges := g.MinimizeEdgesInSCC(scc)
		reduced = append(reduced, minEdges...)
	}
	return reduced
}

// ReduceEdgesParallel processes SCCs in parallel with a bounded worker pool.
// workers<=0 picks runtime.NumCPU(). Maintains deterministic output by fixed-order merge.
func (g *Graph) ReduceEdgesParallel(workers int) []Edge {
	sccs := g.FindSCCs()
	if len(sccs) == 0 {
		return nil
	}

	// Small-N fast path to avoid overhead
	if len(sccs) < 4 {
		return g.ReduceEdgesSequential()
	}

	if workers <= 0 {
		workers = runtime.NumCPU()
	}
	gomax := runtime.GOMAXPROCS(0)
	if workers > gomax {
		workers = gomax
	}
	if workers > len(sccs) {
		workers = len(sccs)
	}

	type job struct{ idx int; scc []int }
	type res struct{ idx int; edges []Edge }

	jobs := make(chan job, len(sccs))
	results := make(chan res, len(sccs))

	for w := 0; w < workers; w++ {
		go func() {
			for j := range jobs {
				edges := g.MinimizeEdgesInSCC(j.scc)
				results <- res{idx: j.idx, edges: edges}
			}
		}()
	}

	for i, scc := range sccs {
		jobs <- job{idx: i, scc: scc}
	}
	close(jobs)

	edgesBySCC := make([][]Edge, len(sccs))
	for i := 0; i < len(sccs); i++ {
		r := <-results
		edgesBySCC[r.idx] = r.edges
	}
	close(results)

	reduced := make([]Edge, 0)
	for i := 0; i < len(edgesBySCC); i++ {
		reduced = append(reduced, edgesBySCC[i]...)
	}
	return reduced
}

// ---------- Helper functions used by runner ----------

func hashEdges(es []Edge) string {
	// serialize edges
	b := make([]byte, 0, len(es)*8)
	for _, e := range es {
		b = append(b, byte(e.U>>24), byte(e.U>>16), byte(e.U>>8), byte(e.U))
		b = append(b, byte(e.V>>24), byte(e.V>>16), byte(e.V>>8), byte(e.V))
	}
	h := sha256.Sum256(b)
	return hex.EncodeToString(h[:])
}

// buildRandomGraph builds a random graph with cc components of size sz each;
// each component is made strongly connected by adding a cycle; then extra edges.
func buildRandomGraph(sz, cc, extra int, seed int64) *Graph {
	g := NewGraph(sz * cc)
	r := rand.New(rand.NewSource(seed))
	// build disjoint SCCs
	for c := 0; c < cc; c++ {
		base := c * sz
		// ring to ensure SCC
		for i := 0; i < sz; i++ {
			g.AddEdge(base+i, base+((i+1)%sz))
		}
		// extra edges inside the SCC
		for k := 0; k < extra; k++ {
			u := base + r.Intn(sz)
			v := base + r.Intn(sz)
			if u != v {
				g.AddEdge(u, v)
			}
		}
	}
	// sparse cross edges between components (do not affect SCCs structure)
	for k := 0; k < cc; k++ {
		if k+1 < cc {
			u := k*sz + r.Intn(sz)
			v := (k+1)*sz + r.Intn(sz)
			g.AddEdge(u, v)
		}
	}
	return g
}

// -------------- CLI Runner --------------

func main() {
	// Build several graphs and compare sequential vs parallel; check determinism; record perf on a larger case.
	if err := os.MkdirAll("evidence", 0o755); err != nil {
		fmt.Println("Failed to create evidence dir:", err)
		os.Exit(2)
	}
	var summary string
	fail := false

	cases := []struct{
		name string
		g    *Graph
	}{
		{"empty", NewGraph(0)},
		{"single_no_edges", NewGraph(1)},
		{"line3", func() *Graph { g := NewGraph(3); g.AddEdge(0,1); g.AddEdge(1,2); return g }()},
		{"one_scc5", func() *Graph { g := NewGraph(5); for i:=0;i<5;i++{ g.AddEdge(i,(i+1)%5) }; g.AddEdge(0,2); g.AddEdge(3,1); return g }()},
	}

	// Add a medium random case
	cases = append(cases, struct{ name string; g *Graph }{"rand_med", buildRandomGraph(20, 8, 40, 42)})

	for _, tc := range cases {
		seq := tc.g.ReduceEdgesSequential()
		par := tc.g.ReduceEdgesParallel(0)
		// Compare by content: both are deterministic already, but also sort to be safe
		if !sameEdges(seq, par) {
			summary += fmt.Sprintf("[FAIL] %s: seq vs par mismatch (|seq|=%d, |par|=%d)\n", tc.name, len(seq), len(par))
			fail = true
		} else {
			summary += fmt.Sprintf("[OK]   %s: outputs match (%d edges)\n", tc.name, len(seq))
		}
		// Determinism: run parallel twice
		par2 := tc.g.ReduceEdgesParallel(0)
		h1 := hashEdges(par)
		h2 := hashEdges(par2)
		if h1 != h2 {
			summary += fmt.Sprintf("[FAIL] %s: parallel determinism mismatch (%s vs %s)\n", tc.name, h1[:8], h2[:8])
			fail = true
		} else {
			summary += fmt.Sprintf("[OK]   %s: parallel deterministic (hash %s)\n", tc.name, h1[:8])
		}
	}

	// Performance smoke test on a larger case (does not fail the run)
	big := buildRandomGraph(300, 24, 900, 123)
	start := time.Now()
	_ = big.ReduceEdgesSequential()
	seqDur := time.Since(start)
	start = time.Now()
	_ = big.ReduceEdgesParallel(0)
	parDur := time.Since(start)
	spd := float64(seqDur) / float64(parDur)
	perfLine := fmt.Sprintf("LargeN: |V|=%d, SCCs=%d, t_seq=%v, t_par=%v, speedup=%.2fx, workers<=%d\n",
		big.V, len(big.FindSCCs()), seqDur, parDur, spd, runtime.GOMAXPROCS(0))

	_ = os.WriteFile("evidence/perf.txt", []byte(perfLine), 0o644)

	// Write summary and exit code
	if fail {
		summary = "RESULT: FAIL\n" + summary
		_ = os.WriteFile("evidence/run_summary.txt", []byte(summary), 0o644)
		fmt.Print(summary)
		os.Exit(1)
	}
	summary = "RESULT: OK\n" + summary
	_ = os.WriteFile("evidence/run_summary.txt", []byte(summary), 0o644)
	fmt.Print(summary)
}

func sameEdges(a, b []Edge) bool {
	if len(a) != len(b) {
		return false
	}
	aa := make([]Edge, len(a))
	bb := make([]Edge, len(b))
	copy(aa, a)
	copy(bb, b)
	sort.Slice(aa, func(i, j int) bool { if aa[i].U==aa[j].U { return aa[i].V<aa[j].V }; return aa[i].U<aa[j].U })
	sort.Slice(bb, func(i, j int) bool { if bb[i].U==bb[j].U { return bb[i].V<bb[j].V }; return bb[i].U<bb[j].U })
	for i := range aa {
		if aa[i] != bb[i] {
			return false
		}
	}
	return true
}
