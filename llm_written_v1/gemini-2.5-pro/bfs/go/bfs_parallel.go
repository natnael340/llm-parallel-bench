package llm_written

import (
	"runtime"
	"sort"
	"sync"
)

// PARALLEL_BFS_THRESHOLD is the number of vertices below which the sequential version is used.
const PARALLEL_BFS_THRESHOLD = 128

// Bfs is the public API that performs a parallel Breadth-First Search.
// It uses a level-synchronous approach, parallelizing the exploration of each level's frontier.
// It dispatches to a sequential implementation for small graphs to avoid overhead.
func Bfs(g Graph, startVertex int) []int {
	if len(g.Vertices) < PARALLEL_BFS_THRESHOLD {
		return BfsSequential(g, startVertex)
	}

	if _, exists := g.Vertices[startVertex]; !exists {
		return []int{}
	}

	// visited is a sync.Map to allow for concurrent, lock-free reads and writes.
	var visited sync.Map
	visited.Store(startVertex, true)

	result := []int{startVertex}
	frontier := []int{startVertex}

	for len(frontier) > 0 {
		numWorkers := runtime.NumCPU()
		if len(frontier) < numWorkers {
			numWorkers = len(frontier)
		}

		// Channel to collect newly discovered nodes from all workers for the next frontier.
		nextFrontierChan := make(chan []int, numWorkers)
		var wg sync.WaitGroup

		// Create a channel of tasks (nodes to visit in the current frontier).
		tasks := make(chan int, len(frontier))
		for _, node := range frontier {
			tasks <- node
		}
		close(tasks)

		// Start a bounded pool of workers.
		wg.Add(numWorkers)
		for i := 0; i < numWorkers; i++ {
			go func() {
				defer wg.Done()
				localNextFrontier := []int{}
				// Each worker pulls nodes from the tasks channel until it's empty.
				for node := range tasks {
					neighbors := g.Vertices[node]
					for _, neighbor := range neighbors {
						// LoadOrStore is an atomic operation.
						// If loaded is false, it means we successfully stored the key,
						// indicating this is the first time we've seen this node.
						if _, loaded := visited.LoadOrStore(neighbor, true); !loaded {
							localNextFrontier = append(localNextFrontier, neighbor)
						}
					}
				}
				nextFrontierChan <- localNextFrontier
			}()
		}

		// Wait for all workers to finish processing the current frontier.
		wg.Wait()
		close(nextFrontierChan)

		// Merge the results from all workers into a single slice for the next frontier.
		nextFrontier := []int{}
		for partialFrontier := range nextFrontierChan {
			nextFrontier = append(nextFrontier, partialFrontier...)
		}
		
		// If no new nodes were discovered, the traversal is complete.
		if len(nextFrontier) == 0 {
			break
		}

		// Crucially, sort the next frontier. This ensures that the traversal order
		// is deterministic across multiple runs, which is essential for testing and predictability.
		sort.Ints(nextFrontier)

		result = append(result, nextFrontier...)
		frontier = nextFrontier
	}

	return result
}
