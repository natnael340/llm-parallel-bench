using System.Collections.Generic;

public static class Bfs
{
    public static List<int> Run(Graph graph, int startVertex)
    {
        if (!graph.Vertices.ContainsKey(startVertex))
            return new List<int>();

        var visited = new HashSet<int>();
        var result = new List<int>();
        var queue = new Queue<int>();
        
        queue.Enqueue(startVertex);

        while (queue.Count > 0)
        {
            int current = queue.Dequeue();
            
            if (!visited.Contains(current))
            {
                visited.Add(current);
                result.Add(current);

                if (graph.Vertices.TryGetValue(current, out var neighbors))
                {
                    foreach (int neighbor in neighbors)
                    {
                        if (!visited.Contains(neighbor))
                            queue.Enqueue(neighbor);
                    }
                }
            }
        }

        return result;
    }
}