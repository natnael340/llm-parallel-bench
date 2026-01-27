using System;
using System.Collections.Generic;
using System.Linq;
using System.Threading.Tasks;

namespace llm_written
{
    // Parallelized version with deterministic ordering and bounded resources
    public class Graph
    {
        private readonly int V;
        private readonly List<int>[] adj, revAdj;

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
            revAdj[w].Add(v);
        }

        // Tarjan’s SCC Algorithm (sequential, deterministic)
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

        // Minimal SCC Edge Reduction
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

        public List<(int, int)> MinimizeEdgesInSCC(List<int> scc)
        {
            HashSet<int> nodes = new HashSet<int>(scc);

            var forwardTree = BuildSpanningTree(scc[0], adj, nodes);
            var reverseTree = BuildSpanningTree(scc[0], revAdj, nodes);

            // Deterministic ordering: sort within each tree and then merge in fixed order
            var essentialEdges = new List<(int, int)>(forwardTree.Count + reverseTree.Count);
            foreach (var e in forwardTree.OrderBy(e => e.Item1).ThenBy(e => e.Item2)) essentialEdges.Add(e);
            foreach (var e in reverseTree.OrderBy(e => e.Item1).ThenBy(e => e.Item2)) essentialEdges.Add(e);
            return essentialEdges;
        }

        public List<(int, int)> ReduceEdges()
        {
            List<List<int>> SCCs = FindSCCs();

            // Early sequential fast path
            if (SCCs.Count <= 1)
            {
                List<(int, int)> sequential = new List<(int, int)>();
                foreach (var scc in SCCs)
                {
                    var minEdges = MinimizeEdgesInSCC(scc);
                    sequential.AddRange(minEdges);
                }
                return sequential;
            }

            int n = SCCs.Count;
            var perScc = new List<(int, int)>[n];

            var options = new ParallelOptions { MaxDegreeOfParallelism = Math.Max(1, Environment.ProcessorCount) };

            // Fixed index-based partitioning ensures determinism of split; each slot written once
            Parallel.For(0, n, options, i =>
            {
                perScc[i] = MinimizeEdgesInSCC(SCCs[i]);
            });

            // Deterministic ordered merge by SCC index
            List<(int, int)> reducedEdges = new List<(int, int)>();
            for (int i = 0; i < n; i++)
            {
                reducedEdges.AddRange(perScc[i]);
            }

            return reducedEdges;
        }
    }
}
