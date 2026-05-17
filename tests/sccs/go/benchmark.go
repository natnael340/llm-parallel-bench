package main

import (
	"encoding/json"
	"flag"
	"fmt"
	"math"
	"math/rand"
	"os"
	"strings"
	"time"

	graphpar "github.com/natnael340/llm-parallel-bench/scc/scssgo/par"
	graphseq "github.com/natnael340/llm-parallel-bench/scc/scssgo/seq"
)

// Graph is the interface satisfied by both graphseq.Graph and graphpar.Graph.
type Graph interface {
	AddEdge(v, w int)
}

type BenchmarkResult struct {
	ElapsedMS  []float64 `json:"elapsed_ms"`
	Mean       float64   `json:"mean"`
	StdDev     float64   `json:"sd"`
	Iterations int       `json:"iterations"`
}


func min(a, b int) int {
	if a < b {
		return a
	}
	return b
}


func ringSCC(start, end int, g Graph) {
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

func populateGraph(graphSize, clusterSize, noClusterInGroup int, g Graph) {
	rand.Seed(43)

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
}


func main() {
	outPath := flag.String("out", "", "Output JSON file path")

	flag.Parse()

	if *outPath == "" {
		fmt.Fprintln(os.Stderr, "Error: use --out <filename.json>")
		os.Exit(1)
	}

	graphSize := 100000
	clusterSize := 300
	noClusterInGroup := 3

	reps := 5
	iters := 20

	algo := strings.ToLower(os.Getenv("ALGO"))
	var run func()
	if algo == "par" {
		g := graphpar.NewGraph(graphSize)
		populateGraph(graphSize, clusterSize, noClusterInGroup, g)
		run = func() { g.ReduceEdges() }
	} else {
		g := graphseq.NewGraph(graphSize)
		populateGraph(graphSize, clusterSize, noClusterInGroup, g)
		run = func() { g.ReduceEdges() }
	}

	// Warm-up
	run()

	perRepeatMs := make([]float64, 0, reps)

	for r := 0; r < reps; r++ {
		start := time.Now()
		for i := 0; i < iters; i++ {
			run()
		}
		elapsed := time.Since(start).Seconds() * 1000 // total ms for iters runs
		perRepeatMs = append(perRepeatMs, elapsed/float64(iters))
	}

	var sum float64
	for _, v := range perRepeatMs {
		sum += v
	}
	mean := sum / float64(reps)

	var variance float64
	for _, v := range perRepeatMs {
		variance += (v - mean) * (v - mean)
	}
	variance /= float64(reps)
	stddev := math.Sqrt(variance)

	result := BenchmarkResult{
		ElapsedMS:  perRepeatMs,
		Mean:       mean,
		StdDev:     stddev,
		Iterations: reps,
	}

	file, err := os.Create(*outPath)
	if err != nil {
		fmt.Fprintf(os.Stderr, "Failed to create a file: %v\n", err)
		os.Exit(1)
	}
	defer file.Close()

	encoder := json.NewEncoder(file)
	encoder.SetIndent("", " ")

	if err := encoder.Encode(result); err != nil {
		fmt.Fprintf(os.Stderr, "Failed to write JSON: %v\n", err)
		os.Exit(1)
	}

	fmt.Printf("SCC ReduceEdges | graph_size=%d | %.2f ms/run ± %.2f (n=%d)\n", graphSize, mean, stddev, reps)
}