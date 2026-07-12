// Swap the line below to switch between sequential and parallel implementations.
using Graph = SCC.Par.Graph;
// using Graph = SCC.Seq.Graph;

using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Text.Json;

namespace SCC
{

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

        double med = Median(perRepeatMs);
        double spread = IQR(perRepeatMs);

        string impl = Environment.GetEnvironmentVariable("IMPL") ?? "";
        WriteResult(filename, "sccs", "csharp", impl, perRepeatMs, med, spread, reps, iters);

        Console.WriteLine($"SCC ReduceEdges | graph_size={graphSize} | {med:F2} ms/run ± {spread:F2} IQR (n={reps})");
    }

    static double Median(List<double> values)
    {
        var s = new List<double>(values);
        s.Sort();
        int n = s.Count;
        return (n % 2 == 0) ? (s[n / 2 - 1] + s[n / 2]) / 2.0 : s[n / 2];
    }

    static double IQR(List<double> values)
    {
        var s = new List<double>(values);
        s.Sort();
        int n = s.Count;
        double q1 = s[(int)((n - 1) * 0.25)];
        double q3 = s[(int)((n - 1) * 0.75)];
        return q3 - q1;
    }

    static void WriteResult(string path, string algo, string lang, string impl,
                            List<double> elapsedMs, double med, double spread,
                            int reps, int itersPerRep)
    {
        if (string.IsNullOrEmpty(path)) return;
        var payload = new
        {
            algo, lang, impl,
            elapsed_ms = elapsedMs,
            median = med,
            iqr = spread,
            reps,
            iters_per_rep = itersPerRep,
        };
        try
        {
            string json = JsonSerializer.Serialize(payload, new JsonSerializerOptions { WriteIndented = true });
            File.WriteAllText(path, json);
        }
        catch (Exception ex)
        {
            Console.Error.WriteLine($"Error writing JSON to file: {path}\n{ex.Message}");
        }
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
