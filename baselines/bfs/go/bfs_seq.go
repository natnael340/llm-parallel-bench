package bfsgo

type Graph struct {
	Vertices map[int][]int
}

func (g *Graph) AddEdge(from, to int){
	if g.Vertices == nil {
		g.Vertices = make(map[int][]int)
	}
	g.Vertices[from] = append(g.Vertices[from], to)
	g.Vertices[to] = append(g.Vertices[to], from)
}


func Bfs(g Graph, startVertex int) []int {
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