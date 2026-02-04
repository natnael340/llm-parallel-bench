package main

// BfsSequential performs sequential BFS traversal
func BfsSequential(g Graph, startVertex int) []int {
	if _, exists := g.Vertices[startVertex]; !exists {
		return []int{}
	}

	// Normalize for deterministic iteration
	g.Normalize()

	visited := map[int]bool{startVertex: true}
	result := []int{}
	queue := []int{startVertex}

	for len(queue) > 0 {
		current := queue[0]
		queue = queue[1:]
		result = append(result, current)

		neighbors := g.Vertices[current]
		for _, neighbor := range neighbors {
			if !visited[neighbor] {
				visited[neighbor] = true
				queue = append(queue, neighbor)
			}
		}
	}

	return result
}
