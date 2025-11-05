// How to Truly Minimize Edges in an SCC?

// We need to remove redundant edges but still keep every node reachable in both directions (to maintain strong connectivity). A good way to do this is:

// Approach: Construct a Strongly Connected Spanning Subgraph (SCSS)

// Instead of keeping all edges, we should:

// 1.	Find a spanning tree inside the SCC (using DFS/BFS).

// 2.	Add reverse edges to ensure strong connectivity.

// 3.	Ensure minimality by keeping only necessary edges.

// ________________________________________

// Improved Algorithm
// Find a spanning tree of the SCC using DFS/BFS
// Compute the reverse spanning tree for strong connectivity
// Merge both trees to keep only essential edges


// ________________________________________

// C# Implementation

using System;

using System.Collections.Generic;
 
namespace LLMParallelBench
{
class Graph

{

    private int V;

    private List<int>[] adj, revAdj;
 
    public Graph(int v)

    {

        V = v;

        adj = new List<int>[v];

        revAdj = new List<int>[v];
 
        for (int i = 0; i < v; i++)

        {

            adj[i] = new List<int>();

            revAdj[i] = new List<int>();

        }

    }
 
    public void AddEdge(int v, int w)

    {

        adj[v].Add(w);

        revAdj[w].Add(v);  // Reverse graph for later use

    }
 
    // Tarjan’s SCC Algorithm (O(V + E))

    private void TarjanDFS(int u, int[] disc, int[] low, Stack<int> stack, bool[] inStack, ref int time, List<List<int>> sccList)

    {

        disc[u] = low[u] = ++time;

        stack.Push(u);

        inStack[u] = true;
 
        foreach (int v in adj[u])

        {

            if (disc[v] == -1)

            {

                TarjanDFS(v, disc, low, stack, inStack, ref time, sccList);

                low[u] = Math.Min(low[u], low[v]);

            }

            else if (inStack[v])

            {

                low[u] = Math.Min(low[u], disc[v]);

            }

        }
 
        if (low[u] == disc[u])

        {

            List<int> scc = new List<int>();

            int w;

            do

            {

                w = stack.Pop();

                inStack[w] = false;

                scc.Add(w);

            } while (w != u);

            sccList.Add(scc);

            

        }
        
    }
 
    public List<List<int>> FindSCCs()

    {

        int[] disc = new int[V], low = new int[V];

        bool[] inStack = new bool[V];

        Stack<int> stack = new Stack<int>();

        List<List<int>> sccList = new List<List<int>>();

        int time = 0;
 
        Array.Fill(disc, -1);

        Array.Fill(low, -1);
 
        for (int i = 0; i < V; i++)

            if (disc[i] == -1)

                TarjanDFS(i, disc, low, stack, inStack, ref time, sccList);
        
        return sccList;

    }
 
    // Minimal SCC Edge Reduction (O(V + E))

    public List<(int, int)> MinimizeEdgesInSCC(List<int> scc)

    {

        HashSet<int> nodes = new HashSet<int>(scc);

        List<(int, int)> essentialEdges = new List<(int, int)>();
 
        // Step 1: Find a forward spanning tree using DFS

        HashSet<(int, int)> forwardTree = BuildSpanningTree(scc[0], adj, nodes);
 
        // Step 2: Find a reverse spanning tree using DFS on the reversed graph

        HashSet<(int, int)> reverseTree = BuildSpanningTree(scc[0], revAdj, nodes);
 
        // Step 3: Merge both trees (each edge appears at most twice)

        essentialEdges.AddRange(forwardTree);

        essentialEdges.AddRange(reverseTree);
 
        return essentialEdges;

    }
 
    private HashSet<(int, int)> BuildSpanningTree(int start, List<int>[] graph, HashSet<int> nodes)

    {

        HashSet<(int, int)> spanningTree = new HashSet<(int, int)>();

        HashSet<int> visited = new HashSet<int>();

        Stack<int> stack = new Stack<int>();

        stack.Push(start);

        visited.Add(start);
 
        while (stack.Count > 0)

        {

            int node = stack.Pop();
 
            foreach (int neighbor in graph[node])

            {

                if (nodes.Contains(neighbor) && !visited.Contains(neighbor))

                {

                    spanningTree.Add((node, neighbor));

                    visited.Add(neighbor);

                    stack.Push(neighbor);

                }

            }

        }
 
        return spanningTree;

    }
 
    public List<(int, int)> ReduceEdges()

    {

        List<List<int>> SCCs = FindSCCs();

        Console.WriteLine($"Found {SCCs.Count} SCC(s).");
 
        List<(int, int)> reducedEdges = new List<(int, int)>();
 
        foreach (var scc in SCCs)

        {

            var minEdges = MinimizeEdgesInSCC(scc);

            reducedEdges.AddRange(minEdges);

        }

 
        Console.WriteLine($"Reduced SCC edges: {reducedEdges.Count}");

        return reducedEdges;


    }

}
 
// **Test Case**

class Program

{

    static void Main()

    {

        Graph g = new Graph(7);

        g.AddEdge(0, 1);

        g.AddEdge(1, 2);

        g.AddEdge(1, 3);

        g.AddEdge(1, 4);

        g.AddEdge(2, 0);

        g.AddEdge(2, 3);

        g.AddEdge(3, 5);

        g.AddEdge(5, 3);

        g.AddEdge(5, 4);

        g.AddEdge(5, 6);

        g.AddEdge(6, 4);

        g.AddEdge(4, 6);

        //Tests.GraphAllTests.RunAll();
        foreach (var (from, to) in g.ReduceEdges())
        {
            Console.WriteLine($"{from} -> {to}");
        }
        

    }

}

}