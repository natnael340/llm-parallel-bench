package llm_written

import (
	"runtime"
	"sync"
)

// Graph represents an undirected graph using adjacency lists.
type Graph struct {
	Vertices map[int][]int
}

// AddEdge adds an undirected edge between from and to.
func (g *Graph) AddEdge(from, to int) {
	if g.Vertices == nil {
		g.Vertices = make(map[int][]int)
	}
	g.Vertices[from] = append(g.Vertices[from], to)
	g.Vertices[to] = append(g.Vertices[to], from)
}

// BfsSequential is the baseline sequential BFS (preserves the given API behavior).
func BfsSequential(g Graph, startVertex int) []int {
	if _, exists := g.Vertices[startVertex]; !exists {
		return []int{}
	}

	visited := map[int]bool{startVertex: true}
	result := []int{}
	queue := []int{startVertex}

	for len(queue) > 0 {
		current := queue[0]
		queue = queue[1:]
		result = append(result, current)

		for _, neighbor := range g.Vertices[current] {
			if !visited[neighbor] {
				visited[neighbor] = true
				queue = append(queue, neighbor)
			}
		}
	}

	return result
}

// BfsParallel performs a deterministic, level-synchronous BFS with parallel frontier expansion.
// It preserves the order produced by BfsSequential for the same graph and start vertex.
// The implementation avoids per-level global scans and sorting, and does not copy the visited set.
func BfsParallel(g Graph, startVertex int) []int {
	if _, exists := g.Vertices[startVertex]; !exists {
		return []int{}
	}

	// Small-input fast path: avoid goroutine overhead when the graph is small.
	if len(g.Vertices) <= 16 {
		return BfsSequential(g, startVertex)
	}

	visited := make(map[int]bool)
	visited[startVertex] = true
	result := make([]int, 0, len(g.Vertices))
	frontier := []int{startVertex}

	for len(frontier) > 0 {
		// Append current level in order (matches dequeue order of sequential BFS)
		result = append(result, frontier...)

		workerCount := runtime.GOMAXPROCS(0)
		if workerCount > len(frontier) {
			workerCount = len(frontier)
		}
		if workerCount < 1 {
			workerCount = 1
		}

		// Partition the frontier into contiguous chunks. Each worker produces a local slice
		// of candidate neighbors in the exact order a sequential BFS would have enqueued
		// for that subrange (parent order, then neighbor order). No writes to shared state.
		chunks := workerCount
		local := make([][]int, chunks)
		var wg sync.WaitGroup
		wg.Add(chunks)
		chunkSize := (len(frontier) + chunks - 1) / chunks

		for w := 0; w < chunks; w++ {
			w := w
			start := w * chunkSize
			end := start + chunkSize
			if start > len(frontier) {
				wg.Done()
				continue
			}
			if end > len(frontier) {
				end = len(frontier)
			}
			go func() {
				defer wg.Done()
				if start >= end {
					return
				}
				// Rough capacity hint: average degree ~ len(neighbors) across this range
				buf := make([]int, 0, (end-start)*4)
				for pi := start; pi < end; pi++ {
					parent := frontier[pi]
					neighbors := g.Vertices[parent]
					for _, neighbor := range neighbors {
						// Safe concurrent read: visited is not written during this phase.
						if !visited[neighbor] {
							buf = append(buf, neighbor)
						}
					}
				}
				local[w] = buf
			}()
		}

		wg.Wait()

		// Merge deterministically in chunk index order, de-duplicating across chunks
		// and honoring the first occurrence semantics (earlier parent/neighbor wins).
		seenNext := make(map[int]struct{})
		nextFrontier := make([]int, 0)
		for w := 0; w < chunks; w++ {
			buf := local[w]
			for _, v := range buf {
				if _, seen := seenNext[v]; seen {
					continue
				}
				// Recheck visited against prior levels only; no current-level writes yet.
				if !visited[v] {
					seenNext[v] = struct{}{}
					nextFrontier = append(nextFrontier, v)
				}
			}
		}

		// Mark newly discovered nodes as visited and advance
		for _, v := range nextFrontier {
			visited[v] = true
		}
		frontier = nextFrontier
	}

	return result
}
