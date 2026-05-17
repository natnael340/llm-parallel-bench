using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Linq;
using System.Security.Cryptography;
using System.Text;

public class TestRunner
{
    public static void Main(string[] args)
    {
        int numVertices = 5000;
        int numEdges = 20000;

        if (args.Length > 0 && int.TryParse(args[0], out int v))
        {
            numVertices = v;
        }
        if (args.Length > 1 && int.TryParse(args[1], out int e))
        {
            numEdges = e;
        }

        Console.WriteLine($"Testing with {numVertices} vertices and {numEdges} edges.");

        // Generate a graph with several dense SCCs
        var (graphSeq, graphPar) = GenerateGraph(numVertices, numEdges);
        var sccs = graphPar.FindSCCs();

        // --- Correctness Test ---
        Console.WriteLine("\n--- Correctness Test ---");
        var sw = Stopwatch.StartNew();
        var seqResult = graphSeq.ReduceEdges();
        sw.Stop();
        long seqTime = sw.ElapsedMilliseconds;

        sw.Restart();
        var parResult1 = graphPar.ReduceEdges();
        sw.Stop();
        long parTime1 = sw.ElapsedMilliseconds;

        var sortedSeq = seqResult.OrderBy(t => t.Item1).ThenBy(t => t.Item2).ToList();
        var sortedPar1 = parResult1.OrderBy(t => t.Item1).ThenBy(t => t.Item2).ToList();

        bool isCorrect = sortedSeq.SequenceEqual(sortedPar1);
        Console.WriteLine($"Correctness: {(isCorrect ? "PASS" : "FAIL")}");
        if (!isCorrect)
        {
            Console.WriteLine($"Sequential count: {sortedSeq.Count}, Parallel count: {sortedPar1.Count}");
            Environment.Exit(1);
        }

        // --- Determinism Test ---
        Console.WriteLine("\n--- Determinism Test ---");
        sw.Restart();
        var parResult2 = graphPar.ReduceEdges();
        sw.Stop();
        long parTime2 = sw.ElapsedMilliseconds;
        
        var sortedPar2 = parResult2.OrderBy(t => t.Item1).ThenBy(t => t.Item2).ToList();

        Console.WriteLine("\n--- Determinism Test ---");
        sw.Restart();
        var parResult3 = graphPar.ReduceEdges();
        sw.Stop();
        long parTime3 = sw.ElapsedMilliseconds;
        
        var sortedPar3 = parResult3.OrderBy(t => t.Item1).ThenBy(t => t.Item2).ToList();


        string hash1 = ComputeHash(sortedPar1);
        string hash2 = ComputeHash(sortedPar2);
        string hash3 = ComputeHash(sortedPar3);

        bool isDeterministic = hash1.Equals(hash2) && hash2.Equals(hash3);
        Console.WriteLine($"Determinism: {(isDeterministic ? "PASS" : "FAIL")}");
        Console.WriteLine($"Run 1 Hash: {hash1}");
        Console.WriteLine($"Run 2 Hash: {hash2}");
        Console.WriteLine($"Run 3 Hash: {hash3}");
        if (!isDeterministic)
        {
            Environment.Exit(1);
        }

        // --- Performance Test ---
        Console.WriteLine("\n--- Performance ---");
        Console.WriteLine($"Sequential Time: {seqTime} ms");
        Console.WriteLine($"Parallel Time (Run 1): {parTime1} ms");
        Console.WriteLine($"Parallel Time (Run 2): {parTime2} ms");

        if (parTime1 > 0 && seqTime > 0)
        {
            double speedup = (double)seqTime / parTime1;
            Console.WriteLine($"Speedup: {speedup:F2}x");
        }
        
        Console.WriteLine("\nAll tests passed!");
    }

    private static (Graph, GraphParallel) GenerateGraph(int numVertices, int numEdges)
    {
        var graphSeq = new Graph(numVertices);
        var graphPar = new GraphParallel(numVertices);
        var rand = new Random(42); // Seed for reproducibility

        // Create a few large, dense SCCs
        int numSccs = Math.Max(1, numVertices / 500);
        int sccSize = numVertices / numSccs;

        for (int i = 0; i < numSccs; i++)
        {
            int startNode = i * sccSize;
            int endNode = Math.Min((i + 1) * sccSize, numVertices);
            for (int u = startNode; u < endNode; u++)
            {
                for (int v = startNode; v < endNode; v++)
                {
                    if (u != v && rand.NextDouble() < 0.2)
                    {
                        graphSeq.AddEdge(u, v);
                        graphPar.AddEdge(u, v);
                    }
                }
            }
        }

        // Add random edges between SCCs to make the graph more complex
        int remainingEdges = numEdges - graphSeq.GetType().GetField("adj", System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Instance).GetValue(graphSeq).ToString().Length;
        for (int i = 0; i < remainingEdges; i++)
        {
            int u = rand.Next(numVertices);
            int v = rand.Next(numVertices);
            graphSeq.AddEdge(u, v);
            graphPar.AddEdge(u, v);
        }

        return (graphSeq, graphPar);
    }

    private static string ComputeHash(List<(int, int)> edges)
    {
        using (var sha256 = SHA256.Create())
        {
            var sb = new StringBuilder();
            foreach (var edge in edges)
            {
                sb.Append($"{edge.Item1},{edge.Item2};");
            }
            byte[] bytes = Encoding.UTF8.GetBytes(sb.ToString());
            byte[] hashBytes = sha256.ComputeHash(bytes);
            return BitConverter.ToString(hashBytes).Replace("-", "").ToLowerInvariant();
        }
    }
}
