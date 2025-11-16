package main

import (
	"encoding/json"
	"flag"
	"time"
	"fmt"
	"os"
	"math"
	"math/rand"
	// "github.com/natnael340/llm-parallel-bench/llm_written/gpt-5/go"
	//baseline "github.com/natnael340/llm-parallel-bench/scc/scssgo"
)

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


func ringSCC(start, end int, g *Graph) {
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

func buildGraph(graphSize, clusterSize, noClusterInGroup int) *Graph {
	g := NewGraph(graphSize)
	rand.Seed(43)

	for i := 0; i < graphSize; i += clusterSize {
		ringSCC(i, min(i + clusterSize, graphSize), g)

		currentCluster := (i / clusterSize) // 0, 1, 2, 3, ...
		if currentCluster / noClusterInGroup == (currentCluster + 1) / noClusterInGroup {
			if (i + clusterSize) < graphSize {
				endA := min(i + clusterSize, graphSize)
				endB := min(i + 2 * clusterSize, graphSize)
				u := i + rand.Intn(endA - i)
				v := endA + rand.Intn(endB - endA)
				g.AddEdge(u, v)
			}
		}
	}

	return g
}


func main() {
	outPath := flag.String("out", "", "Output JSON file path")
	iter := flag.Int("iter", 100, "# of iterations")

	flag.Parse()

	if *outPath == "" {
		fmt.Fprintln(os.Stderr, "Error: use --out <filename.json>")
		os.Exit(1)
	}

	graphSize := 100000
    clusterSize := 300
    noClusterInGroup := 3

	iterations := *iter
	warmups := 20

    graph := buildGraph(graphSize, clusterSize, noClusterInGroup)

    // Warm-up
    for i := 0; i < warmups; i++ {
        graph.FindSCCs()
    }


	durations := make([]float64, 0, 100)
	var totalMs float64 = 0.0

	for i := 0; i < iterations; i++ {
        start := time.Now()
        graph.FindSCCs()
        elapsed := float64(time.Since(start).Milliseconds()) // ms
        durations = append(durations, elapsed)
		totalMs += elapsed
    }
	
    mean := totalMs / float64(iterations)

    // Compute std dev
    var variance float64
    for _, d := range durations {
        variance += (d - mean) * (d - mean)
    }
    variance /= float64(iterations)
    stddev := math.Sqrt(variance)

	result := BenchmarkResult{
		ElapsedMS: durations,
		Mean: mean,
		StdDev: stddev,
		Iterations: iterations,
	}

	file, err := os.Create(*outPath)
	if err != nil {
		fmt.Fprintln(os.Stderr, "Failed to create a file: %v\n", err)
		os.Exit(1)
	}
	defer file.Close()

	encoder := json.NewEncoder(file)
	encoder.SetIndent("", " ")

	if err:=encoder.Encode(result); err != nil {
		fmt.Fprintf(os.Stderr, "Failed to write JSON: %v\n", err)
		os.Exit(1)
	}

    fmt.Printf("Mean: %.2f ms ± %.2f ms\n", mean, stddev)
}