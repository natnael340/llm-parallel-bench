package llm_written

// BfsSequential performs a standard, sequential Breadth-First Search.
func BfsSequential(g Graph, startVertex int) []int {
	// Check if the start vertex exists in the graph.
	if _, exists := g.Vertices[startVertex]; !exists {
		return []int{}
	}

	visited := map[int]bool{startVertex: true}
	// The result slice also implicitly tracks the visit order.
	result := []int{}
	queue := []int{startVertex}

	for len(queue) > 0 {
		// Dequeue the current vertex.
		current := queue[0]
		queue = queue[1:]
		result = append(result, current)

		// Explore its neighbors.
		for _, neighbor := range g.Vertices[current] {
			if !visited[neighbor] {
				visited[neighbor] = true
				queue = append(queue, neighbor)
			}
		}
	}

	return result
}
