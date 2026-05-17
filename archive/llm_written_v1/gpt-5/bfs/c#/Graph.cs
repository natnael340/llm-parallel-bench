using System.Collections.Generic;

public class Graph
{
    public Dictionary<int, List<int>> Vertices { get; } = new Dictionary<int, List<int>>();

    public void AddEdge(int fromVertex, int toVertex)
    {
        if (!Vertices.ContainsKey(fromVertex))
            Vertices[fromVertex] = new List<int>();
        if (!Vertices.ContainsKey(toVertex))
            Vertices[toVertex] = new List<int>();
        
        Vertices[fromVertex].Add(toVertex);
        Vertices[toVertex].Add(fromVertex);
    }
}