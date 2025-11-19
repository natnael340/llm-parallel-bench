using System;
using System.Collections.Concurrent;
using System.Collections.Generic;
using System.Linq;
using System.Threading.Tasks;

public class GraphParallel
{
    private int V;
    private List<int>[] adj, revAdj;
    private const int PARALLEL_THRESHOLD = 1; 

    public GraphParallel(int v)
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
        revAdj[w].Add(v);
    }

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

    public List<(int, int)> MinimizeEdgesInSCC(List<int> scc)
    {
        if (scc == null || scc.Count == 0)
            return new List<(int, int)>();

        HashSet<int> nodes = new HashSet<int>(scc);
        List<(int, int)> essentialEdges = new List<(int, int)>();

        HashSet<(int, int)> forwardTree = BuildSpanningTree(scc[0], adj, nodes);
        HashSet<(int, int)> reverseTree = BuildSpanningTree(scc[0], revAdj, nodes);

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

        if (SCCs.Count < PARALLEL_THRESHOLD)
        {
            List<(int, int)> reducedEdgesSeq = new List<(int, int)>();
            foreach (var scc in SCCs)
            {
                var minEdges = MinimizeEdgesInSCC(scc);
                reducedEdgesSeq.AddRange(minEdges);
            }
            return reducedEdgesSeq;
        }

        var reducedEdges = new ConcurrentBag<List<(int, int)>>();
        Parallel.ForEach(SCCs, scc =>
        {
            var minEdges = MinimizeEdgesInSCC(scc);
            reducedEdges.Add(minEdges);
        });

        return reducedEdges.SelectMany(list => list).ToList();
    }
}
