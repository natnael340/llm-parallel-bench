package main

import (
	"crypto/sha256"
	"fmt"
	"os"
	"runtime"
	"sort"
	"sync"
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
	g.RevAdj[w] = append(g.RevAdj[w], v)
}

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

func (g *Graph) MinimizeEdgesInSCC(scc []int) []Edge {
	nodes := make(map[int]bool, len(scc))
	for _, n := range scc {
		nodes[n] = true
	}

	forwardTree := g.buildSpanningTree(scc[0], g.Adj, nodes)
	reverseTree := g.buildSpanningTree(scc[0], g.RevAdj, nodes)

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

// Sequential version
func (g *Graph) ReduceEdgesSeq() []Edge {
	sccs := g.FindSCCs()
	reduced := make([]Edge, 0)
	for _, scc := range sccs {
		minEdges := g.MinimizeEdgesInSCC(scc)
		reduced = append(reduced, minEdges...)
	}
	return reduced
}

// Parallel version
func (g *Graph) ReduceEdges() []Edge {
	sccs := g.FindSCCs()

	const threshold = 4
	if len(sccs) < threshold {
		reduced := make([]Edge, 0)
		for _, scc := range sccs {
			minEdges := g.MinimizeEdgesInSCC(scc)
			reduced = append(reduced, minEdges...)
		}
		return reduced
	}

	numWorkers := runtime.NumCPU()
	if numWorkers > len(sccs) {
		numWorkers = len(sccs)
	}

	type job struct {
		index int
		scc   []int
	}
	type result struct {
		index int
		edges []Edge
	}

	jobs := make(chan job, len(sccs))
	results := make(chan result, len(sccs))

	var wg sync.WaitGroup
	for w := 0; w < numWorkers; w++ {
		wg.Add(1)
		go func() {
			defer wg.Done()
			for j := range jobs {
				edges := g.MinimizeEdgesInSCC(j.scc)
				results <- result{index: j.index, edges: edges}
			}
		}()
	}

	for i, scc := range sccs {
		jobs <- job{index: i, scc: scc}
	}
	close(jobs)

	go func() {
		wg.Wait()
		close(results)
	}()

	resultMap := make(map[int][]Edge, len(sccs))
	for r := range results {
		resultMap[r.index] = r.edges
	}

	reduced := make([]Edge, 0)
	for i := 0; i < len(sccs); i++ {
		reduced = append(reduced, resultMap[i]...)
	}

	return reduced
}

// Test generators
func buildLinearChain(n int) *Graph {
	g := NewGraph(n)
	for i := 0; i < n-1; i++ {
		g.AddEdge(i, i+1)
	}
	return g
}

func buildCycle(n int) *Graph {
	g := NewGraph(n)
	for i := 0; i < n-1; i++ {
		g.AddEdge(i, i+1)
	}
	g.AddEdge(n-1, 0)
	return g
}

func buildMultipleSCCs(numSCCs, sccSize int) *Graph {
	totalNodes := numSCCs * sccSize
	g := NewGraph(totalNodes)
	for s := 0; s < numSCCs; s++ {
		base := s * sccSize
		for i := 0; i < sccSize-1; i++ {
			g.AddEdge(base+i, base+i+1)
		}
		g.AddEdge(base+sccSize-1, base)
	}
	for s := 0; s < numSCCs-1; s++ {
		g.AddEdge(s*sccSize, (s+1)*sccSize)
	}
	return g
}

func buildCompleteGraph(n int) *Graph {
	g := NewGraph(n)
	for i := 0; i < n; i++ {
		for j := 0; j < n; j++ {
			if i != j {
				g.AddEdge(i, j)
			}
		}
	}
	return g
}

func normalizeEdges(edges []Edge) []Edge {
	sorted := make([]Edge, len(edges))
	copy(sorted, edges)
	sort.Slice(sorted, func(i, j int) bool {
		if sorted[i].U != sorted[j].U {
			return sorted[i].U < sorted[j].U
		}
		return sorted[i].V < sorted[j].V
	})
	return sorted
}

func hashEdges(edges []Edge) string {
	normalized := normalizeEdges(edges)
	h := sha256.New()
	for _, e := range normalized {
		fmt.Fprintf(h, "%d->%d,", e.U, e.V)
	}
	return fmt.Sprintf("%x", h.Sum(nil))
}

func edgeSetsEqual(a, b []Edge) bool {
	if len(a) != len(b) {
		return false
	}
	normA := normalizeEdges(a)
	normB := normalizeEdges(b)
	for i := range normA {
		if normA[i] != normB[i] {
			return false
		}
	}
	return true
}

type TestCase struct {
	name      string
	buildFunc func() *Graph
	parallel  bool
}

func main() {
	testCases := []TestCase{
		{"Edge_Empty", func() *Graph { return NewGraph(0) }, false},
		{"Edge_Single", func() *Graph { return NewGraph(1) }, false},
		{"Small_Chain_5", func() *Graph { return buildLinearChain(5) }, false},
		{"Small_Cycle_5", func() *Graph { return buildCycle(5) }, false},
		{"Medium_4SCCs_10each", func() *Graph { return buildMultipleSCCs(4, 10) }, true},
		{"Medium_20SCCs_5each", func() *Graph { return buildMultipleSCCs(20, 5) }, true},
		{"Large_50SCCs_20each", func() *Graph { return buildMultipleSCCs(50, 20) }, true},
		{"Large_Complete_50", func() *Graph { return buildCompleteGraph(50) }, true},
	}

	passCount := 0
	failCount := 0
	evidence := ""

	os.MkdirAll("evidence", 0755)

	for _, tc := range testCases {
		fmt.Printf("\n=== Test: %s ===\n", tc.name)
		evidence += fmt.Sprintf("\n=== Test: %s ===\n", tc.name)

		gSeq := tc.buildFunc()
		gPar := tc.buildFunc()

		t0 := time.Now()
		seqResult := gSeq.ReduceEdgesSeq()
		seqDur := time.Since(t0)

		t1 := time.Now()
		parResult1 := gPar.ReduceEdges()
		parDur1 := time.Since(t1)

		gPar2 := tc.buildFunc()
		t2 := time.Now()
		parResult2 := gPar2.ReduceEdges()
		parDur2 := time.Since(t2)

		correctness := edgeSetsEqual(seqResult, parResult1)
		fmt.Printf("Correctness: %v (seq=%d edges, par=%d edges)\n", correctness, len(seqResult), len(parResult1))
		evidence += fmt.Sprintf("Correctness: %v (seq=%d edges, par=%d edges)\n", correctness, len(seqResult), len(parResult1))

		hash1 := hashEdges(parResult1)
		hash2 := hashEdges(parResult2)
		determinism := hash1 == hash2
		fmt.Printf("Determinism: %v\n", determinism)
		fmt.Printf("  Run1 hash: %s\n", hash1[:16])
		fmt.Printf("  Run2 hash: %s\n", hash2[:16])
		evidence += fmt.Sprintf("Determinism: %v\n", determinism)
		evidence += fmt.Sprintf("  Run1 hash: %s\n", hash1[:16])
		evidence += fmt.Sprintf("  Run2 hash: %s\n", hash2[:16])

		if tc.parallel {
			speedup := float64(seqDur) / float64(parDur1)
			fmt.Printf("Performance: seq=%v, par1=%v, par2=%v, speedup=%.2fx\n", seqDur, parDur1, parDur2, speedup)
			evidence += fmt.Sprintf("Performance: seq=%v, par1=%v, par2=%v, speedup=%.2fx\n", seqDur, parDur1, parDur2, speedup)
		} else {
			fmt.Printf("Performance: seq=%v, par1=%v (skipped: small N)\n", seqDur, parDur1)
			evidence += fmt.Sprintf("Performance: seq=%v, par1=%v (skipped: small N)\n", seqDur, parDur1)
		}

		passed := correctness && determinism
		if passed {
			fmt.Printf("✅ PASS\n")
			evidence += "✅ PASS\n"
			passCount++
		} else {
			fmt.Printf("❌ FAIL\n")
			evidence += "❌ FAIL\n"
			failCount++
		}
	}

	summary := fmt.Sprintf("\n=== SUMMARY ===\nTotal: %d | Pass: %d | Fail: %d\n", passCount+failCount, passCount, failCount)
	fmt.Println(summary)
	evidence += summary

	os.WriteFile("evidence/run_summary.txt", []byte(evidence), 0644)

	if failCount > 0 {
		os.Exit(1)
	}
}
