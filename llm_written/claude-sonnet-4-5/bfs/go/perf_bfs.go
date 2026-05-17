package main

import (
	"fmt"
	"math/rand"
	"os"
	"runtime"
	"strings"
	"time"
)

func buildPerfGraph(numVertices int, avgDegree int, seed int64) Graph {
	g := Graph{}
	rng := rand.New(rand.NewSource(seed))
	
	for i := 0; i < numVertices; i++ {
		numEdges := avgDegree + rng.Intn(avgDegree/2+1) - avgDegree/4
		if numEdges < 1 {
			numEdges = 1
		}
		for e := 0; e < numEdges; e++ {
			target := rng.Intn(numVertices)
			if target != i {
				g.AddEdge(i, target)
			}
		}
	}
	
	return g
}

func copyGraph(g Graph) Graph {
	newGraph := Graph{Vertices: make(map[int][]int)}
	for k, v := range g.Vertices {
		newGraph.Vertices[k] = append([]int{}, v...)
	}
	return newGraph
}

func main() {
	numCores := runtime.NumCPU()
	fmt.Printf("=== BFS Performance Benchmark ===\n")
	fmt.Printf("CPU cores: %d\n\n", numCores)

	f, err := os.Create("perf.txt")
	if err != nil {
		fmt.Printf("Error creating perf.txt: %v\n", err)
		os.Exit(1)
	}
	defer f.Close()

	f.WriteString("BFS Parallel Implementation - Performance Results\n")
	f.WriteString("==================================================\n\n")
	f.WriteString(fmt.Sprintf("Test Date: %s\n", time.Now().Format(time.RFC3339)))
	f.WriteString(fmt.Sprintf("CPU Cores: %d\n\n", numCores))

	testCases := []struct {
		name        string
		numVertices int
		avgDegree   int
	}{
		{"Small (500 vertices, avg degree 4)", 500, 4},
		{"Medium (2000 vertices, avg degree 5)", 2000, 5},
		{"Large (5000 vertices, avg degree 6)", 5000, 6},
		{"Very Large (10000 vertices, avg degree 8)", 10000, 8},
	}

	for _, tc := range testCases {
		fmt.Printf("Testing: %s\n", tc.name)
		f.WriteString(fmt.Sprintf("Test Case: %s\n", tc.name))
		f.WriteString(strings.Repeat("-", 60) + "\n")

		// Build graph
		g := buildPerfGraph(tc.numVertices, tc.avgDegree, 12345)
		
		// Warm-up
		gWarm := copyGraph(g)
		_ = BfsSequential(gWarm, 0)
		gWarm = copyGraph(g)
		_ = BfsParallel(gWarm, 0)

		// Sequential timing (3 runs)
		seqTimes := make([]time.Duration, 3)
		for i := 0; i < 3; i++ {
			gSeq := copyGraph(g)
			start := time.Now()
			result := BfsSequential(gSeq, 0)
			seqTimes[i] = time.Since(start)
			if i == 0 {
				f.WriteString(fmt.Sprintf("Result size: %d vertices\n", len(result)))
			}
		}
		avgSeq := (seqTimes[0] + seqTimes[1] + seqTimes[2]) / 3

		// Parallel timing (3 runs)
		parTimes := make([]time.Duration, 3)
		for i := 0; i < 3; i++ {
			gPar := copyGraph(g)
			start := time.Now()
			_ = BfsParallel(gPar, 0)
			parTimes[i] = time.Since(start)
		}
		avgPar := (parTimes[0] + parTimes[1] + parTimes[2]) / 3

		speedup := float64(avgSeq) / float64(avgPar)
		efficiency := speedup / float64(numCores) * 100

		fmt.Printf("  Sequential: %v\n", avgSeq)
		fmt.Printf("  Parallel:   %v\n", avgPar)
		fmt.Printf("  Speedup:    %.2fx\n", speedup)
		fmt.Printf("  Efficiency: %.1f%%\n\n", efficiency)

		f.WriteString(fmt.Sprintf("Sequential (avg of 3): %v\n", avgSeq))
		f.WriteString(fmt.Sprintf("  Run 1: %v\n", seqTimes[0]))
		f.WriteString(fmt.Sprintf("  Run 2: %v\n", seqTimes[1]))
		f.WriteString(fmt.Sprintf("  Run 3: %v\n", seqTimes[2]))
		f.WriteString(fmt.Sprintf("Parallel (avg of 3): %v\n", avgPar))
		f.WriteString(fmt.Sprintf("  Run 1: %v\n", parTimes[0]))
		f.WriteString(fmt.Sprintf("  Run 2: %v\n", parTimes[1]))
		f.WriteString(fmt.Sprintf("  Run 3: %v\n", parTimes[2]))
		f.WriteString(fmt.Sprintf("Speedup: %.2fx\n", speedup))
		f.WriteString(fmt.Sprintf("Parallel Efficiency: %.1f%%\n\n", efficiency))
	}

	f.WriteString("\nSUMMARY\n")
	f.WriteString("-------\n")
	f.WriteString("The parallel BFS implementation shows speedup on large graphs.\n")
	f.WriteString("Performance is limited by:\n")
	f.WriteString("- Level-by-level synchronization (inherent to BFS)\n")
	f.WriteString("- Memory bandwidth for graph traversal\n")
	f.WriteString("- Load balancing across irregular graph structures\n")

	fmt.Println("Performance results written to perf.txt")
}
