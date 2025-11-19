using System;
using System.Collections.Generic;
using System.Collections.Concurrent;
using System.Text.Json;
using System.Text.Json.Serialization;
using System.Diagnostics;
using System.IO;
using System.Linq;
using System.Threading.Tasks;


// You'll need to include your Graph class implementation here
// using YourNamespace;

namespace LLMParallelBenchGpt5
{

// Parallelized version with deterministic ordering and bounded resources

public class GraphParallel
{
    private int V;
    private List<int>[] adj, revAdj;

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
        revAdj[w].Add(v);  // Reverse graph for later use
    }

    // Tarjan's SCC Algorithm (O(V + E)) - SEQUENTIAL (required for correctness)
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

    // PARALLEL version: Process SCCs in parallel with bounded concurrency
    public List<(int, int)> ReduceEdges()
    {
        List<List<int>> SCCs = FindSCCs();
        //Console.WriteLine($"Found {SCCs.Count} SCC(s).");

        // Sequential fallback for small SCC counts
        if (SCCs.Count < 4)
        {
            List<(int, int)> reducedEdges = new List<(int, int)>();
            foreach (var scc in SCCs)
            {
                var minEdges = MinimizeEdgesInSCC(scc);
                reducedEdges.AddRange(minEdges);
            }
            //Console.WriteLine($"Reduced SCC edges: {reducedEdges.Count}");
            return reducedEdges;
        }

        // Parallel processing: each SCC is independent
        // Use indexed array to maintain deterministic order
        var edgeResults = new List<(int, int)>[SCCs.Count];
        
        // Bounded parallelism: use at most Environment.ProcessorCount workers
        var options = new ParallelOptions 
        { 
            MaxDegreeOfParallelism = Environment.ProcessorCount 
        };

        // Process SCCs in parallel, storing results at fixed indices
        Parallel.For(0, SCCs.Count, options, i =>
        {
            var minEdges = MinimizeEdgesInSCC(SCCs[i]);
            edgeResults[i] = minEdges;
        });

        // Merge results in deterministic order (same order as SCCs)
        List<(int, int)> allReducedEdges = new List<(int, int)>();
        for (int i = 0; i < SCCs.Count; i++)
        {
            allReducedEdges.AddRange(edgeResults[i]);
        }

        //Console.WriteLine($"Reduced SCC edges: {allReducedEdges.Count}");
        return allReducedEdges;
    }
}
// End of Graph class

public class BenchmarkResult {
    [JsonPropertyName("elapsed_ms")]
    public List<double> ElapsedMilliseconds { get; set; } = new List<double>();

    [JsonPropertyName("mean")]
    public double Mean { get; set; }

    [JsonPropertyName("sd")]
    public double StdDev { get; set; }

    [JsonPropertyName("iterations")]
    public int Iterations { get; set; }
}

class Program
{
    static void RingSCC(int start, int end, GraphParallel g)
    {
        for (int i = start; i < end; i++)
        {
            int v = (i + 1) % end;
            if (v == 0)
            {
                v = start;
            }
            if (i == v)
            {
                continue;
            }
            g.AddEdge(i, v);
        }
    }

    static GraphParallel BuildGraph(int graphSize, int clusterSize, int noClusterInGroup)
    {
        GraphParallel g = new GraphParallel(graphSize);
        Random rand = new Random(43);
        
        for (int i = 0; i < graphSize; i += clusterSize)
        {
            // Create a ring SCC
            RingSCC(i, Math.Min(i + clusterSize, graphSize), g);
            
            int currentCluster = (i / clusterSize); 
            if (currentCluster / noClusterInGroup == (currentCluster + 1) / noClusterInGroup)
            {
                if ((i + clusterSize) < graphSize)
                {
                    int endA = Math.Min(i + clusterSize, graphSize);
                    int endB = Math.Min(i + 2 * clusterSize, graphSize);
                    
                    int u = i + rand.Next(endA - i);
                    int v = endA + rand.Next(endB - endA);
                    g.AddEdge(u, v);
                }
            }
        }
        return g;
    }

    static void BenchmarkReduceEdges(int iterations, int warmups, string filename)
    {
        int graphSize = 100000;
        int clusterSize = 300;
        int noClusterInGroup = 3;
        
        GraphParallel g = BuildGraph(graphSize, clusterSize, noClusterInGroup);
        List<double> batchTimes = new List<double>(iterations);
        
        // Sanity run
        // List<(int, int)> reduced = g.ReduceEdges();
        // Console.WriteLine($"Sanity check - Reduced edges: {reduced.Count}");

        // warmup runs
        for (int i = 0; i < warmups; i++)
        {
            g.ReduceEdges();
        }

        double total_ms = 0.0;
        
        for (int i = 0; i < iterations; i++)
        {
            Stopwatch sw = Stopwatch.StartNew();
            
            g.ReduceEdges();
            
            sw.Stop();
            batchTimes.Add(sw.Elapsed.TotalMilliseconds);
            total_ms += sw.Elapsed.TotalMilliseconds;
        }
        
        // Compute mean and standard deviation
        double mean = total_ms / iterations;
        
        double sqSum = 0;
        foreach (double t in batchTimes)
        {
            sqSum += (t - mean) * (t - mean);
        }
        double stddev = Math.Sqrt(sqSum / iterations);
        
        var result = new BenchmarkResult
        {
            ElapsedMilliseconds = batchTimes,
            Mean = mean,
            StdDev = stddev,
            Iterations = iterations
        };
        var jsonOptions = new JsonSerializerOptions
        {
            WriteIndented = true
        };
        // Write results to file
        try
        {
            string json = JsonSerializer.Serialize(result, jsonOptions);
            File.WriteAllText(filename, json);
        }
        catch (Exception ex)
        {
            Console.Error.WriteLine($"Error writing JSON to file: {filename}\n{ex.Message}");
        }
        
        Console.WriteLine($"Mean: {mean} ms ± {stddev} ms.");
    }
    
    static Dictionary<string, string> ParseArgs(string[] args)
    {
        var dict = new Dictionary<string, string>();
        for (int i = 0; i < args.Length - 1; i++)
        {
            if (args[i].StartsWith("--"))
            {
                string key = args[i].Substring(2);
                string value = args[i + 1];
                dict[key] = value;
                i++; // skip value
            }
        }
        return dict;
    }


    static void Main(string[] args)
    {   
        var argDict = ParseArgs(args);

        int iterations = 100;
        int warmups = 5;
        string filename = "";

        if (argDict.ContainsKey("iterations"))
        {
            int.TryParse(argDict["iterations"], out iterations);
        }
        if (argDict.ContainsKey("warmups"))
        {
            int.TryParse(argDict["warmups"], out warmups);
        }

        if (argDict.ContainsKey("out"))
        {
            filename = argDict["out"];
        }
        else
        {
            Console.Error.WriteLine("Error: Output file not specified. Use --out <filename>");
            return;
        }

        
        Console.WriteLine("Starting BenchmarkReduceEdges...");
        BenchmarkReduceEdges(iterations, warmups, filename);
    }
}
}