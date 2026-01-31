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
        bool allTestsPassed = true;

        if (args.Length > 0 && args[0] == "--perf")
        {
            Console.WriteLine("--- Running Performance Test ---");
            var (graph, startNode) = CreateLargeGraphForPerf();
            
            var stopwatch = Stopwatch.StartNew();
            var sequentialResult = Bfs.Run(graph, startNode);
            stopwatch.Stop();
            long sequentialTime = stopwatch.ElapsedMilliseconds;
            Console.WriteLine($"Sequential execution time: {sequentialTime} ms");

            stopwatch.Restart();
            var parallelResult = BfsParallel.Run(graph, startNode);
            stopwatch.Stop();
            long parallelTime = stopwatch.ElapsedMilliseconds;
            Console.WriteLine($"Parallel execution time: {parallelTime} ms");

            double speedup = sequentialTime > 0 ? (double)sequentialTime / parallelTime : (parallelTime == 0 ? 1.0 : double.PositiveInfinity);
            Console.WriteLine($"Speedup: {speedup:F2}x");

            string perfResults = $"Sequential Time (ms): {sequentialTime}\n" +
                                 $"Parallel Time (ms): {parallelTime}\n" +
                                 $"Speedup: {speedup:F2}x\n" +
                                 $"Cores: {Environment.ProcessorCount}";
            System.IO.File.WriteAllText("perf.txt", perfResults);
        }
        else
        {
            allTestsPassed &= RunTest("Empty Graph", CreateEmptyGraph(), 0);
            allTestsPassed &= RunTest("Single Node Graph", CreateSingleNodeGraph(), 0);
            allTestsPassed &= RunTest("Small Linear Graph", CreateSmallLinearGraph(), 0);
            allTestsPassed &= RunTest("Small Star Graph", CreateSmallStarGraph(), 0);
            allTestsPassed &= RunTest("Medium Random Graph", CreateRandomGraph(2000, 10000), 0);
            allTestsPassed &= RunTest("Large Random Graph", CreateRandomGraph(10000, 50000), 0);
            
            Console.WriteLine(allTestsPassed ? "All tests passed." : "Some tests failed.");
            
            if (!allTestsPassed)
            {
                Environment.Exit(1);
            }
        }
    }

    private static bool RunTest(string testName, Graph graph, int startNode)
    {
        Console.WriteLine($"--- Running Test: {testName} ---");
        StringBuilder summary = new StringBuilder();
        summary.AppendLine($"Test Case: {testName}");

        try
        {
            var sequentialResult = Bfs.Run(graph, startNode);
            var parallelResult1 = BfsParallel.Run(graph, startNode);
            var parallelResult2 = BfsParallel.Run(graph, startNode);

            bool correctnessCheck = sequentialResult.SequenceEqual(parallelResult1);
            bool determinismCheck = parallelResult1.SequenceEqual(parallelResult2);

            string sequentialHash = ComputeHash(sequentialResult);
            string parallelHash1 = ComputeHash(parallelResult1);
            string parallelHash2 = ComputeHash(parallelResult2);
            
            summary.AppendLine($"Sequential Hash: {sequentialHash}");
            summary.AppendLine($"Parallel Hash 1: {parallelHash1}");
            summary.AppendLine($"Parallel Hash 2: {parallelHash2}");
            
            if (correctnessCheck && determinismCheck)
            {
                summary.AppendLine("Result: PASSED (Correctness and Determinism)");
                Console.WriteLine("✅ Test Passed.");
                System.IO.File.AppendAllText("run_summary.txt", summary.ToString() + "\n");
                return true;
            }
            else
            {
                summary.AppendLine("Result: FAILED");
                if (!correctnessCheck) summary.AppendLine("  - Failure: Parallel result does not match sequential result.");
                if (!determinismCheck) summary.AppendLine("  - Failure: Parallel runs produced different results.");
                Console.WriteLine("❌ Test Failed.");
                System.IO.File.AppendAllText("run_summary.txt", summary.ToString() + "\n");
                return false;
            }
        }
        catch (Exception ex)
        {
            summary.AppendLine($"Result: FAILED with exception: {ex.Message}");
            Console.WriteLine($"❌ Test Failed with exception: {ex.Message}");
            System.IO.File.AppendAllText("run_summary.txt", summary.ToString() + "\n");
            return false;
        }
    }

    private static string ComputeHash(List<int> list)
    {
        if (list == null || list.Count == 0) return "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"; // SHA256 of empty string
        using (var sha256 = SHA256.Create())
        {
            var data = Encoding.UTF8.GetBytes(string.Join(",", list));
            var hashBytes = sha256.ComputeHash(data);
            return BitConverter.ToString(hashBytes).Replace("-", "").ToLowerInvariant();
        }
    }

    // Graph generation methods
    private static Graph CreateEmptyGraph() => new Graph();
    private static Graph CreateSingleNodeGraph()
    {
        var graph = new Graph();
        graph.AddEdge(0, 0);
        return graph;
    }
    private static Graph CreateSmallLinearGraph()
    {
        var graph = new Graph();
        for (int i = 0; i < 10; i++)
        {
            graph.AddEdge(i, i + 1);
        }
        return graph;
    }
    private static Graph CreateSmallStarGraph()
    {
        var graph = new Graph();
        for (int i = 1; i <= 10; i++)
        {
            graph.AddEdge(0, i);
        }
        return graph;
    }
    private static Graph CreateRandomGraph(int numVertices, int numEdges)
    {
        var graph = new Graph();
        var rand = new Random(42);
        for (int i = 0; i < numEdges; i++)
        {
            int v1 = rand.Next(numVertices);
            int v2 = rand.Next(numVertices);
            graph.AddEdge(v1, v2);
        }
        return graph;
    }
    
    private static (Graph, int) CreateLargeGraphForPerf()
    {
        int numVertices = 50000;
        int numEdges = 200000;
        var graph = new Graph();
        var rand = new Random(123);
        for (int i = 0; i < numEdges; i++)
        {
            int v1 = rand.Next(numVertices);
            int v2 = rand.Next(numVertices);
            graph.AddEdge(v1, v2);
        }
        return (graph, 0);
    }
}
