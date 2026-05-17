// Package main provides a parallel implementation of Breadth-First Search (BFS)
// with deterministic output guarantees.
package main

import (
	"runtime"
	"sort"
	"sync"
)

const (
	// MinVerticesForParallel is the threshold below which sequential BFS is used
	MinVerticesForParallel = 100
	// MinFrontierForParallel is the minimum frontier size for parallel processing
	MinFrontierForParallel = 20
)

// BfsParallel performs level-synchronous parallel BFS
// Returns vertices in BFS order, matching the sequential baseline
func BfsParallel(g Graph, startVertex int) []int {
	if _, exists := g.Vertices[startVertex]; !exists {
		return []int{}
	}

	// Normalize for deterministic iteration
	g.Normalize()

	// Small graph fallback to sequential
	if len(g.Vertices) < MinVerticesForParallel {
		return BfsSequential(g, startVertex)
	}

	visited := &sync.Map{}
	visited.Store(startVertex, true)
	result := []int{}
	currentLevel := []int{startVertex}

	numWorkers := runtime.NumCPU()

	for len(currentLevel) > 0 {
		// Add current level to result
		result = append(result, currentLevel...)

		// Process current level to find next level
		var nextLevel []int
		if len(currentLevel) < MinFrontierForParallel {
			// Sequential processing for small frontiers
			nextLevel = processLevelSequential(g, currentLevel, visited)
		} else {
			// Parallel processing for large frontiers
			nextLevel = processLevelParallel(g, currentLevel, visited, numWorkers)
		}

		// Preserve discovery order (no sorting needed - merge order is deterministic)
		currentLevel = nextLevel
	}

	return result
}

// processLevelSequential processes a BFS level sequentially
func processLevelSequential(g Graph, level []int, visited *sync.Map) []int {
	nextLevel := []int{}
	localVisited := make(map[int]bool)

	for _, vertex := range level {
		neighbors := g.Vertices[vertex]
		for _, neighbor := range neighbors {
			if _, alreadyVisited := visited.Load(neighbor); alreadyVisited {
				continue
			}
			if localVisited[neighbor] {
				continue
			}
			localVisited[neighbor] = true
			visited.Store(neighbor, true)
			nextLevel = append(nextLevel, neighbor)
		}
	}

	return nextLevel
}

// processLevelParallel processes a BFS level in parallel using a worker pool
func processLevelParallel(g Graph, level []int, visited *sync.Map, numWorkers int) []int {
	// Divide work into chunks
	chunkSize := (len(level) + numWorkers - 1) / numWorkers
	if chunkSize < 1 {
		chunkSize = 1
	}

	type chunkResult struct {
		index     int
		neighbors []int
	}

	resultChan := make(chan chunkResult, numWorkers)
	var wg sync.WaitGroup

	// Launch workers to process chunks in parallel
	for i := 0; i < numWorkers; i++ {
		start := i * chunkSize
		if start >= len(level) {
			break
		}
		end := start + chunkSize
		if end > len(level) {
			end = len(level)
		}

		wg.Add(1)
		go func(workerID int, chunk []int) {
			defer wg.Done()

			// Process chunk and collect neighbors in discovery order
			localNext := []int{}
			localVisited := make(map[int]bool)

			for _, vertex := range chunk {
				neighbors := g.Vertices[vertex]
				for _, neighbor := range neighbors {
					if _, alreadyVisited := visited.Load(neighbor); alreadyVisited {
						continue
					}
					if localVisited[neighbor] {
						continue
					}
					localVisited[neighbor] = true
					localNext = append(localNext, neighbor)
				}
			}

			resultChan <- chunkResult{index: workerID, neighbors: localNext}
		}(i, level[start:end])
	}

	// Wait for all workers
	go func() {
		wg.Wait()
		close(resultChan)
	}()

	// Collect results
	results := make([]chunkResult, 0, numWorkers)
	for res := range resultChan {
		results = append(results, res)
	}

	// Sort by worker index for deterministic merge order
	sort.Slice(results, func(i, j int) bool {
		return results[i].index < results[j].index
	})

	// Merge results with global deduplication, preserving discovery order
	globalVisited := make(map[int]bool)
	nextLevel := []int{}

	for _, res := range results {
		for _, neighbor := range res.neighbors {
			if globalVisited[neighbor] {
				continue
			}
			if _, alreadyVisited := visited.Load(neighbor); alreadyVisited {
				continue
			}
			globalVisited[neighbor] = true
			visited.Store(neighbor, true)
			nextLevel = append(nextLevel, neighbor)
		}
	}

	return nextLevel
}
