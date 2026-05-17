// Swap the line below to switch between sequential and parallel implementations.
using Graph = SCC.Par.Graph;
// using Graph = SCC.Par.Graph;

using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Text.Json;
using System.Text.Json.Serialization;

namespace SCC
{

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
    static void RingSCC(int start, int end, Graph g)
    {
        for (int i = start; i < end; i++)
        {
            int v = (i + 1) % end;
            if (v == 0) v = start;
            if (i == v) continue;
            g.AddEdge(i, v);
        }
    }

    static Graph BuildGraph(int graphSize, int clusterSize, int noClusterInGroup)
    {
        Graph g = new Graph(graphSize);
        Random rand = new Random(43);

        for (int i = 0; i < graphSize; i += clusterSize)
        {
            RingSCC(i, Math.Min(i + clusterSize, graphSize), g);

            int currentCluster = i / clusterSize;
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

    static void BenchmarkReduceEdges(string filename)
    {
        int graphSize = 100000;
        int clusterSize = 300;
        int noClusterInGroup = 3;

        Graph g = BuildGraph(graphSize, clusterSize, noClusterInGroup);

        const int reps = 5;
        const int iters = 20;

        // warmup
        g.ReduceEdges();

        List<double> perRepeatMs = new List<double>(reps);

        for (int r = 0; r < reps; r++)
        {
            Stopwatch sw = Stopwatch.StartNew();
            for (int i = 0; i < iters; i++)
                g.ReduceEdges();
            sw.Stop();
            perRepeatMs.Add(sw.Elapsed.TotalMilliseconds / iters);
        }

        double mean = 0.0;
        foreach (double t in perRepeatMs) mean += t;
        mean /= reps;

        double sqSum = 0.0;
        foreach (double t in perRepeatMs) sqSum += (t - mean) * (t - mean);
        double stddev = Math.Sqrt(sqSum / reps);

        var result = new BenchmarkResult
        {
            ElapsedMilliseconds = perRepeatMs,
            Mean = mean,
            StdDev = stddev,
            Iterations = reps
        };

        try
        {
            string json = JsonSerializer.Serialize(result, new JsonSerializerOptions { WriteIndented = true });
            File.WriteAllText(filename, json);
        }
        catch (Exception ex)
        {
            Console.Error.WriteLine($"Error writing JSON to file: {filename}\n{ex.Message}");
        }

        Console.WriteLine($"SCC ReduceEdges | graph_size={graphSize} | {mean:F2} ms/run ± {stddev:F2} (n={reps})");
    }

    static Dictionary<string, string> ParseArgs(string[] args)
    {
        var dict = new Dictionary<string, string>();
        for (int i = 0; i < args.Length - 1; i++)
        {
            if (args[i].StartsWith("--"))
            {
                dict[args[i].Substring(2)] = args[i + 1];
                i++;
            }
        }
        return dict;
    }

    static void Main(string[] args)
    {
        var argDict = ParseArgs(args);

        if (argDict.ContainsKey("test") && argDict["test"] == "all")
        {
            SCC.Tests.GraphAllTests.RunAll();
            return;
        }

        if (!argDict.ContainsKey("out"))
        {
            Console.Error.WriteLine("Error: Output file not specified. Use --out <filename>");
            return;
        }

        Console.WriteLine("Starting BenchmarkReduceEdges...");
        BenchmarkReduceEdges(argDict["out"]);
    }
}
}
