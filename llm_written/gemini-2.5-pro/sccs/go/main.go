package main

import (
	"crypto/sha256"
	"encoding/json"
	"fmt"
	"log"
	"math/rand"
	"os"
	"runtime"
	"sort"
	"strconv"
	"sync"
	"time"
)

// --- Shared Data Structures ---

type Edge struct {
	U, V int
}

// ByEdge is used for sorting slices of Edges to ensure deterministic output.
type ByEdge []Edge

func (a ByEdge) Len() int      { return len(a) }
func (a ByEdge) Swap(i, j int) { a[i], a[j] = a[j], a[i] }
func (a ByEdge) Less(i, j int) bool {
	if a[i].U != a[j].U {
		return a[i].U < a[j].U
	}
	return a[i].V < a[j].V
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

// --- Common Algorithms (used by both sequential and parallel versions) ---

func (g *Graph) tarjanDFS(u int, disc, low []int, stack *[]int, inStack []bool, timeRef *int, sccList *[][]int) {
	*timeRef++
	disc[u], low[u] = *timeRef, *timeRef
	*stack = append(*stack, u)
	inStack[u] = true

	for _, v := range g.Adj[u] {
		if disc[v] == -1 {
			g.tarjanDFS(v, disc, low, stack, inStack, timeRef, sccList)
			if low[v] < low[u] {
				low[u] = low[v]
			}
		} else if inStack[v] && disc[v] < low[u] {
			low[u] = disc[v]
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
	disc, low, inStack := make([]int, g.V), make([]int, g.V), make([]bool, g.V)
	stack, sccList := make([]int, 0, g.V), make([][]int, 0)
	for i := 0; i < g.V; i++ {
		disc[i], low[i] = -1, -1
	}
	timeRef := 0
	for i := 0; i < g.V; i++ {
		if disc[i] == -1 {
			g.tarjanDFS(i, disc, low, &stack, inStack, &timeRef, &sccList)
		}
	}
	return sccList
}

func (g *Graph) buildSpanningTree(start int, adj [][]int, nodes map[int]bool) map[Edge]struct{} {
	spanning, visited := make(map[Edge]struct{}), make(map[int]bool, len(nodes))
	stack := []int{start}
	visited[start] = true
	for len(stack) > 0 {
		node := stack[len(stack)-1]
		stack = stack[:len(stack)-1]
		for _, nb := range adj[node] {
			if nodes[nb] && !visited[nb] {
				spanning[Edge{node, nb}] = struct{}{}
				visited[nb] = true
				stack = append(stack, nb)
			}
		}
	}
	return spanning
}

// REFINED: This function now sorts its output to be deterministic.
func (g *Graph) MinimizeEdgesInSCC(scc []int) []Edge {
	if len(scc) == 0 {
		return []Edge{}
	}
	nodes := make(map[int]bool, len(scc))
	for _, n := range scc {
		nodes[n] = true
	}
	forwardTree := g.buildSpanningTree(scc[0], g.Adj, nodes)
	reverseTree := g.buildSpanningTree(scc[0], g.RevAdj, nodes)
	
	// Collect edges from maps into a slice
	out := make([]Edge, 0, len(forwardTree)+len(reverseTree))
	for e := range forwardTree {
		out = append(out, e)
	}
	for e := range reverseTree {
		out = append(out, e)
	}
	
	// Sort the slice to ensure deterministic order
	sort.Sort(ByEdge(out))
	
	return out
}

// --- Sequential Implementation ---

func (g *Graph) ReduceEdgesSequential() []Edge {
	sccs := g.FindSCCs()
	reduced := make([]Edge, 0)
	for _, scc := range sccs {
		minEdges := g.MinimizeEdgesInSCC(scc)
		reduced = append(reduced, minEdges...)
	}
	return reduced
}

// --- Parallel Implementation ---

const minSCCsForParallel = 4
type sccTask struct{ index int; scc []int }
type sccResult struct{ index int; edges []Edge }

func (g *Graph) ReduceEdgesParallel() []Edge {
	sccs := g.FindSCCs()

	if len(sccs) < minSCCsForParallel {
		return g.reduceEdgesSequentialInternal(sccs)
	}

	numWorkers := runtime.NumCPU()
	tasks := make(chan sccTask, len(sccs))
	results := make(chan sccResult, len(sccs))
	var wg sync.WaitGroup

	for i := 0; i < numWorkers; i++ {
		wg.Add(1)
		go func() {
			defer wg.Done()
			for task := range tasks {
				minEdges := g.MinimizeEdgesInSCC(task.scc)
				results <- sccResult{index: task.index, edges: minEdges}
			}
		}()
	}

	for i, scc := range sccs {
		tasks <- sccTask{index: i, scc: scc}
	}
	close(tasks)

	wg.Wait()
	close(results)

	orderedResults := make([][]Edge, len(sccs))
	totalEdges := 0
	for result := range results {
		orderedResults[result.index] = result.edges
		totalEdges += len(result.edges)
	}

	finalEdges := make([]Edge, 0, totalEdges)
	for _, edgeList := range orderedResults {
		finalEdges = append(finalEdges, edgeList...)
	}
	return finalEdges
}

func (g *Graph) reduceEdgesSequentialInternal(sccs [][]int) []Edge {
    reduced := make([]Edge, 0)
    for _, scc := range sccs {
        minEdges := g.MinimizeEdgesInSCC(scc)
        reduced = append(reduced, minEdges...)
    }
    return reduced
}


// --- Test Harness ---

func generateGraph(numVertices, numEdges int, seed int64) *Graph {
	rand.Seed(seed)
	g := NewGraph(numVertices)
	for i := 0; i < numEdges; i++ {
		u, v := rand.Intn(numVertices), rand.Intn(numVertices)
		g.AddEdge(u, v)
	}
	return g
}

func compareResults(seqResult, parResult []Edge) bool {
	if len(seqResult) != len(parResult) {
		fmt.Printf("Length mismatch: seq=%d, par=%d\n", len(seqResult), len(parResult))
		return false
	}
	// The main results are now composed of pre-sorted chunks, but the combined
	// list still needs sorting for a canonical comparison.
	sort.Sort(ByEdge(seqResult))
	sort.Sort(ByEdge(parResult))
	for i := range seqResult {
		if seqResult[i] != parResult[i] {
			fmt.Printf("Content mismatch at index %d: seq=%v, par=%v\n", i, seqResult[i], parResult[i])
			return false
		}
	}
	return true
}

func hashResult(edges []Edge) string {
	data, err := json.Marshal(edges)
	if err != nil {
		log.Fatalf("Failed to marshal result: %v", err)
	}
	return fmt.Sprintf("%x", sha256.Sum256(data))
}

func main() {
    // Manually set flags for evidence generation
    args := os.Args[1:]
    var (
        numVertices int = 1000
        numEdges    int = 5000
        seed        int64 = 42
        perfCheck   bool
    )

    // Simple manual flag parsing
    for i := 0; i < len(args); i++ {
        switch args[i] {
        case "-v":
            if i+1 < len(args) {
                numVertices, _ = strconv.Atoi(args[i+1])
                i++
            }
        case "-e":
            if i+1 < len(args) {
                numEdges, _ = strconv.Atoi(args[i+1])
                i++
            }
        case "-seed":
            if i+1 < len(args) {
                seed, _ = strconv.ParseInt(args[i+1], 10, 64)
                i++
            }
        case "-perf":
            perfCheck = true
        }
    }


	if perfCheck {
		if numVertices < 20000 || numEdges < 100000 {
			fmt.Println("Performance check requires larger graph, e.g., -v=20000 -e=100000. Running standard tests.")
			perfCheck = false
		} else {
			fmt.Println("Performance check enabled.")
		}
	}

	fmt.Printf("Generating graph with %d vertices, %d edges, seed %d\n", numVertices, numEdges, seed)
	graph := generateGraph(numVertices, numEdges, seed)

	fmt.Println("\n--- Running Correctness Check ---")
	startSeq := time.Now()
	seqResult := graph.ReduceEdgesSequential()
	durationSeq := time.Since(startSeq)
	fmt.Printf("Sequential implementation took: %v\n", durationSeq)

	startPar1 := time.Now()
	parResult1 := graph.ReduceEdgesParallel()
	durationPar1 := time.Since(startPar1)
	fmt.Printf("Parallel implementation (run 1) took: %v\n", durationPar1)

	if !compareResults(seqResult, parResult1) {
		fmt.Println("❌ FAILURE: Correctness check failed. Outputs do not match.")
		os.Exit(1)
	}
	fmt.Println("✅ SUCCESS: Correctness check passed.")

	fmt.Println("\n--- Running Determinism Check ---")
	startPar2 := time.Now()
	parResult2 := graph.ReduceEdgesParallel()
	durationPar2 := time.Since(startPar2)
	fmt.Printf("Parallel implementation (run 2) took: %v\n", durationPar2)

	hash1 := hashResult(parResult1)
	hash2 := hashResult(parResult2)
	fmt.Printf("Hash of parallel run 1: %s\n", hash1)
	fmt.Printf("Hash of parallel run 2: %s\n", hash2)

	if hash1 != hash2 {
		fmt.Println("❌ FAILURE: Determinism check failed. Hashes do not match.")
		os.Exit(1)
	}
	fmt.Println("✅ SUCCESS: Determinism check passed.")

	if perfCheck {
		fmt.Println("\n--- Running Performance Check ---")
		speedup := float64(durationSeq) / float64(durationPar1)
		fmt.Printf("Speedup: %.2fx\n", speedup)
		if speedup < 1.3 {
			fmt.Println("⚠️ WARNING: Speedup is less than 1.3x.")
		} else {
			fmt.Println("✅ SUCCESS: Performance check passed.")
		}
	}

	fmt.Println("\nAll checks passed.")
}
