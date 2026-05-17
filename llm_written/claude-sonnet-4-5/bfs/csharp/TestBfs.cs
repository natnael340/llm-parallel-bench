using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Linq;
using System.Security.Cryptography;
using System.Text;

public class TestBfs
{
    private static int testsPassed = 0;
    private static int testsFailed = 0;
    private static List<string> failureDetails = new List<string>();

    public static void Main(string[] args)
    {
        Console.WriteLine("=== BFS Differential Test Suite ===\n");

        // Edge cases
        TestEmptyGraph();
        TestSingleVertex();
        TestDisconnectedGraph();
        TestStartVertexNotInGraph();

        // Small cases
        TestLinearChain();
        TestSmallTree();
        TestSmallCycle();

        // Medium cases
        TestBinaryTree();
        TestGridGraph();

        // Large case
        TestLargeRandomGraph();

        // Determinism checks
        TestDeterminism();

        // Performance test
        TestPerformance();

        // Write summary
        WriteSummary();

        Console.WriteLine($"\n=== FINAL RESULTS ===");
        Console.WriteLine($"Passed: {testsPassed}");
        Console.WriteLine($"Failed: {testsFailed}");

        if (testsFailed > 0)
        {
            Console.WriteLine("\nFailure details:");
            foreach (var detail in failureDetails)
            {
                Console.WriteLine($"  - {detail}");
            }
            Environment.Exit(1);
        }
        else
        {
            Console.WriteLine("\n✓ All tests passed!");
            Environment.Exit(0);
        }
    }

    private static void TestEmptyGraph()
    {
        var graph = new Graph();
        RunTest("EmptyGraph", graph, 1, new List<int>());
    }

    private static void TestSingleVertex()
    {
        var graph = new Graph();
        graph.Vertices[1] = new List<int>();
        RunTest("SingleVertex", graph, 1, new List<int> { 1 });
    }

    private static void TestDisconnectedGraph()
    {
        var graph = new Graph();
        graph.AddEdge(1, 2);
        graph.AddEdge(3, 4);
        // Start from 1, should only reach 1 and 2
        var expected = new List<int> { 1, 2 };
        RunTest("DisconnectedGraph", graph, 1, expected);
    }

    private static void TestStartVertexNotInGraph()
    {
        var graph = new Graph();
        graph.AddEdge(1, 2);
        RunTest("StartVertexNotInGraph", graph, 99, new List<int>());
    }

    private static void TestLinearChain()
    {
        var graph = new Graph();
        // 1 - 2 - 3 - 4 - 5
        graph.AddEdge(1, 2);
        graph.AddEdge(2, 3);
        graph.AddEdge(3, 4);
        graph.AddEdge(4, 5);
        var expected = new List<int> { 1, 2, 3, 4, 5 };
        RunTest("LinearChain", graph, 1, expected);
    }

    private static void TestSmallTree()
    {
        var graph = new Graph();
        //     1
        //    /|\
        //   2 3 4
        graph.AddEdge(1, 2);
        graph.AddEdge(1, 3);
        graph.AddEdge(1, 4);
        var expected = new List<int> { 1, 2, 3, 4 };
        RunTest("SmallTree", graph, 1, expected);
    }

    private static void TestSmallCycle()
    {
        var graph = new Graph();
        // 1 - 2
        // |   |
        // 4 - 3
        graph.AddEdge(1, 2);
        graph.AddEdge(2, 3);
        graph.AddEdge(3, 4);
        graph.AddEdge(4, 1);
        var expected = new List<int> { 1, 2, 4, 3 };
        RunTest("SmallCycle", graph, 1, expected);
    }

    private static void TestBinaryTree()
    {
        var graph = new Graph();
        //       1
        //      / \
        //     2   3
        //    / \ / \
        //   4  5 6  7
        graph.AddEdge(1, 2);
        graph.AddEdge(1, 3);
        graph.AddEdge(2, 4);
        graph.AddEdge(2, 5);
        graph.AddEdge(3, 6);
        graph.AddEdge(3, 7);
        var expected = new List<int> { 1, 2, 3, 4, 5, 6, 7 };
        RunTest("BinaryTree", graph, 1, expected);
    }

    private static void TestGridGraph()
    {
        var graph = new Graph();
        // 5x5 grid
        for (int i = 0; i < 5; i++)
        {
            for (int j = 0; j < 5; j++)
            {
                int v = i * 5 + j;
                if (j < 4) graph.AddEdge(v, v + 1);      // horizontal
                if (i < 4) graph.AddEdge(v, v + 5);      // vertical
            }
        }
        var seqResult = BfsSequential.Run(graph, 0);
        RunTest("GridGraph_5x5", graph, 0, seqResult);
    }

    private static void TestLargeRandomGraph()
    {
        var graph = new Graph();
        int n = 5000;
        var rand = new Random(42); // Fixed seed for reproducibility
        
        // Create a connected graph with random edges
        for (int i = 0; i < n - 1; i++)
        {
            graph.AddEdge(i, i + 1);
        }
        
        // Add random edges
        for (int i = 0; i < n * 2; i++)
        {
            int u = rand.Next(n);
            int v = rand.Next(n);
            if (u != v)
            {
                graph.AddEdge(u, v);
            }
        }
        
        var seqResult = BfsSequential.Run(graph, 0);
        RunTest("LargeRandomGraph_5000", graph, 0, seqResult);
    }

    private static void TestDeterminism()
    {
        Console.WriteLine("\n--- Determinism Tests ---");
        
        var graph = new Graph();
        int n = 1000;
        var rand = new Random(123);
        
        for (int i = 0; i < n - 1; i++)
        {
            graph.AddEdge(i, i + 1);
        }
        for (int i = 0; i < n; i++)
        {
            int u = rand.Next(n);
            int v = rand.Next(n);
            if (u != v) graph.AddEdge(u, v);
        }

        // Run parallel version 3 times
        var run1 = BfsParallel.Run(graph, 0);
        var run2 = BfsParallel.Run(graph, 0);
        var run3 = BfsParallel.Run(graph, 0);

        string hash1 = ComputeHash(run1);
        string hash2 = ComputeHash(run2);
        string hash3 = ComputeHash(run3);

        Console.WriteLine($"  Run 1 hash: {hash1}");
        Console.WriteLine($"  Run 2 hash: {hash2}");
        Console.WriteLine($"  Run 3 hash: {hash3}");

        if (hash1 == hash2 && hash2 == hash3)
        {
            Console.WriteLine("  ✓ Determinism check PASSED");
            testsPassed++;
        }
        else
        {
            Console.WriteLine("  ✗ Determinism check FAILED");
            testsFailed++;
            failureDetails.Add("Determinism: hashes differ across runs");
        }
    }

    private static void TestPerformance()
    {
        Console.WriteLine("\n--- Performance Test ---");
        
        var graph = new Graph();
        int n = 10000;
        var rand = new Random(999);
        
        // Create a connected graph
        for (int i = 0; i < n - 1; i++)
        {
            graph.AddEdge(i, i + 1);
        }
        
        // Add random edges for complexity
        for (int i = 0; i < n * 3; i++)
        {
            int u = rand.Next(n);
            int v = rand.Next(n);
            if (u != v) graph.AddEdge(u, v);
        }

        // Warm-up
        BfsSequential.Run(graph, 0);
        BfsParallel.Run(graph, 0);

        // Sequential timing
        var sw = Stopwatch.StartNew();
        var seqResult = BfsSequential.Run(graph, 0);
        sw.Stop();
        double seqTime = sw.Elapsed.TotalMilliseconds;

        // Parallel timing
        sw.Restart();
        var parResult = BfsParallel.Run(graph, 0);
        sw.Stop();
        double parTime = sw.Elapsed.TotalMilliseconds;

        double speedup = seqTime / parTime;
        int cores = Environment.ProcessorCount;
        double efficiency = speedup / cores;

        Console.WriteLine($"  Graph size: {n} vertices");
        Console.WriteLine($"  Sequential time: {seqTime:F2} ms");
        Console.WriteLine($"  Parallel time: {parTime:F2} ms");
        Console.WriteLine($"  Speedup: {speedup:F2}x");
        Console.WriteLine($"  Cores: {cores}");
        Console.WriteLine($"  Efficiency: {efficiency * 100:F1}%");

        // Write to perf.txt
        File.WriteAllText("perf.txt", 
            $"N={n}\n" +
            $"t_seq={seqTime:F2}ms\n" +
            $"t_par={parTime:F2}ms\n" +
            $"speedup={speedup:F2}x\n" +
            $"cores={cores}\n" +
            $"efficiency={efficiency * 100:F1}%\n");

        // Verify correctness
        if (ListsEqual(seqResult, parResult))
        {
            Console.WriteLine("  ✓ Performance test correctness PASSED");
            testsPassed++;
        }
        else
        {
            Console.WriteLine("  ✗ Performance test correctness FAILED");
            testsFailed++;
            failureDetails.Add("Performance test: outputs differ");
        }
    }

    private static void RunTest(string testName, Graph graph, int start, List<int> expected)
    {
        var seqResult = BfsSequential.Run(graph, start);
        var parResult = BfsParallel.Run(graph, start);

        bool seqMatch = ListsEqual(seqResult, expected);
        bool parMatch = ListsEqual(parResult, expected);

        Console.WriteLine($"{testName}:");
        Console.WriteLine($"  Expected: [{string.Join(", ", expected)}]");
        Console.WriteLine($"  Sequential: [{string.Join(", ", seqResult)}] - {(seqMatch ? "✓" : "✗")}");
        Console.WriteLine($"  Parallel: [{string.Join(", ", parResult)}] - {(parMatch ? "✓" : "✗")}");

        if (seqMatch && parMatch)
        {
            testsPassed++;
        }
        else
        {
            testsFailed++;
            failureDetails.Add($"{testName}: seq={seqMatch}, par={parMatch}");
        }
    }

    private static bool ListsEqual(List<int> a, List<int> b)
    {
        if (a.Count != b.Count) return false;
        for (int i = 0; i < a.Count; i++)
        {
            if (a[i] != b[i]) return false;
        }
        return true;
    }

    private static string ComputeHash(List<int> list)
    {
        using (var sha256 = SHA256.Create())
        {
            var bytes = Encoding.UTF8.GetBytes(string.Join(",", list));
            var hash = sha256.ComputeHash(bytes);
            return BitConverter.ToString(hash).Replace("-", "").ToLower();
        }
    }

    private static void WriteSummary()
    {
        var summary = new StringBuilder();
        summary.AppendLine("=== BFS Test Summary ===");
        summary.AppendLine($"Total tests: {testsPassed + testsFailed}");
        summary.AppendLine($"Passed: {testsPassed}");
        summary.AppendLine($"Failed: {testsFailed}");
        summary.AppendLine();
        
        if (testsFailed > 0)
        {
            summary.AppendLine("Failures:");
            foreach (var detail in failureDetails)
            {
                summary.AppendLine($"  - {detail}");
            }
        }
        else
        {
            summary.AppendLine("All tests passed!");
        }

        File.WriteAllText("run_summary.txt", summary.ToString());
    }
}
