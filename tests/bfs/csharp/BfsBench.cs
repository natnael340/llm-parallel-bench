using System;
using System.Collections.Generic;
using System.Linq;

// Plain benchmark runner (no test SDK): correctness checks + perf, mirroring
// the Java/C++/Go BFS harnesses. The implementation under test is provided by
// the staged adapter class BenchImpl (see bench/manifests/bfs/csharp.json).
public class BfsBench
{
    private static int passed = 0;
    private static int failed = 0;

    public static int Main(string[] args)
    {
        Console.WriteLine("Running BFS Tests...\n");

        Test("Empty graph returns empty list", TestEmptyGraph);
        Test("Single node with self-loop returns single node", TestSingleNode);
        Test("Linear graph returns nodes in order", TestLinearGraph);
        Test("Complete graph returns correct BFS order", TestCompleteGraph);
        Test("Star graph returns center then leaves", TestStarGraph);
        Test("Cycle is handled correctly", TestCycle);
        Test("Tree structure returns level order", TestTreeStructure);
        Test("Complex graph returns correct order", TestComplexGraph);
        Test("Disconnected components only visits connected component", TestDisconnectedComponents);
        Test("Duplicate edges are handled correctly", TestDuplicateEdges);
        Test("Nonexistent start vertex returns empty list", TestNonexistentStart);
        Test("Order consistency is maintained across runs", TestOrderConsistency);
        Test("Unordered edge insertion produces correct BFS", TestReturnOrder);
        Test("Performance stress test with large linear graph", TestLargeLinearGraph);

        Console.WriteLine("\n========================================");
        Console.WriteLine($"Results: {passed} passed, {failed} failed, {passed + failed} total");
        Console.WriteLine("========================================");

        if (failed > 0)
        {
            Console.WriteLine($"{failed} test(s) failed — skipping benchmark");
            return 1;
        }

        PerformanceSpeedTest();
        return 0;
    }

    private static void Test(string name, Action testFn)
    {
        try
        {
            testFn();
            Console.WriteLine("[PASS] " + name);
            passed++;
        }
        catch (Exception e)
        {
            Console.WriteLine("[FAIL] " + name);
            Console.WriteLine("       " + e.Message);
            failed++;
        }
    }

    private static void AssertEqual(List<int> expected, List<int> actual)
    {
        if (!expected.SequenceEqual(actual))
        {
            throw new Exception($"Expected [{string.Join(", ", expected)}] but got [{string.Join(", ", actual)}]");
        }
    }

    private static void TestEmptyGraph()
    {
        var graph = new Graph();
        AssertEqual(new List<int>(), BenchImpl.Run(graph, 0));
    }

    private static void TestSingleNode()
    {
        var graph = new Graph();
        graph.AddEdge(1, 1);
        AssertEqual(new List<int> { 1 }, BenchImpl.Run(graph, 1));
    }

    private static void TestLinearGraph()
    {
        var graph = new Graph();
        graph.AddEdge(1, 2);
        graph.AddEdge(2, 3);
        graph.AddEdge(3, 4);
        AssertEqual(new List<int> { 1, 2, 3, 4 }, BenchImpl.Run(graph, 1));
    }

    private static void TestCompleteGraph()
    {
        var graph = new Graph();
        var nodes = new List<int> { 1, 2, 3, 4 };
        foreach (var i in nodes)
            foreach (var j in nodes)
                if (i != j)
                    graph.AddEdge(i, j);
        AssertEqual(new List<int> { 3, 1, 2, 4 }, BenchImpl.Run(graph, 3));
    }

    private static void TestStarGraph()
    {
        var graph = new Graph();
        int center = 1;
        var leaves = new List<int> { 2, 3, 4, 5 };
        foreach (var leaf in leaves)
            graph.AddEdge(center, leaf);
        var expected = new List<int> { center };
        expected.AddRange(leaves);
        AssertEqual(expected, BenchImpl.Run(graph, center));
    }

    private static void TestCycle()
    {
        var graph = new Graph();
        foreach (var (u, v) in new[] { (1, 2), (2, 3), (3, 4), (4, 1) })
            graph.AddEdge(u, v);
        AssertEqual(new List<int> { 1, 2, 4, 3 }, BenchImpl.Run(graph, 1));
    }

    private static void TestTreeStructure()
    {
        var graph = new Graph();
        foreach (var (u, v) in new[] { (1, 2), (1, 3), (2, 4), (2, 5), (3, 6), (3, 7) })
            graph.AddEdge(u, v);
        AssertEqual(new List<int> { 1, 2, 3, 4, 5, 6, 7 }, BenchImpl.Run(graph, 1));
    }

    private static void TestComplexGraph()
    {
        var graph = new Graph();
        foreach (var (u, v) in new[] {
            (1, 2), (1, 3), (2, 4), (3, 4), (4, 5),
            (5, 6), (6, 7), (5, 7), (7, 8), (3, 8) })
            graph.AddEdge(u, v);
        AssertEqual(new List<int> { 1, 2, 3, 4, 8, 5, 7, 6 }, BenchImpl.Run(graph, 1));
    }

    private static void TestDisconnectedComponents()
    {
        var graph = new Graph();
        graph.AddEdge(1, 2);
        graph.AddEdge(2, 3);
        graph.AddEdge(4, 5);
        graph.AddEdge(4, 6);
        AssertEqual(new List<int> { 1, 2, 3 }, BenchImpl.Run(graph, 1));
        AssertEqual(new List<int> { 4, 5, 6 }, BenchImpl.Run(graph, 4));
    }

    private static void TestDuplicateEdges()
    {
        var graph = new Graph();
        graph.AddEdge(1, 2);
        graph.AddEdge(1, 2);
        graph.AddEdge(2, 3);
        AssertEqual(new List<int> { 1, 2, 3 }, BenchImpl.Run(graph, 1));
    }

    private static void TestNonexistentStart()
    {
        var graph = new Graph();
        graph.AddEdge(1, 2);
        AssertEqual(new List<int>(), BenchImpl.Run(graph, 999));
    }

    private static void TestOrderConsistency()
    {
        var graph = new Graph();
        graph.AddEdge(1, 3);
        graph.AddEdge(1, 2);
        var first = BenchImpl.Run(graph, 1);
        for (int i = 0; i < 5; i++)
            AssertEqual(first, BenchImpl.Run(graph, 1));
    }

    private static void TestReturnOrder()
    {
        var graph = new Graph();
        foreach (var (u, v) in new[] { (5, 6), (1, 4), (3, 5), (1, 2), (2, 3), (1, 3), (4, 5) })
            graph.AddEdge(u, v);
        AssertEqual(new List<int> { 1, 4, 2, 3, 5, 6 }, BenchImpl.Run(graph, 1));
    }

    private static void TestLargeLinearGraph()
    {
        var graph = new Graph();
        int size = 1000;
        for (int i = 1; i < size; i++)
            graph.AddEdge(i, i + 1);
        var result = BenchImpl.Run(graph, 1);
        if (result.Count != size || result[0] != 1 || result[^1] != size)
            throw new Exception($"Expected chain of {size} nodes, got {result.Count}");
    }

    private static void PerformanceSpeedTest()
    {
        var graph = new Graph();
        int size = 2000;
        for (int i = 1; i <= size; i++)
        {
            for (int j = i + 1; j <= size; j++)
            {
                graph.AddEdge(i, j);
                graph.AddEdge(j, i);
            }
        }

        int reps = Bench.Reps(5);
        int iters = Bench.Iters(20);

        var r = Bench.Run(() => BenchImpl.Run(graph, 1), reps, iters, 1);

        long directed = (long)size * (size - 1);
        string label = $"BFS complete graph | nodes={size}, undirected edges≈{directed / 2:N0} (directed≈{directed:N0})";
        Console.WriteLine(Bench.Format(label, r));

        var params_ = new Dictionary<string, object> { ["graph_size"] = size, ["graph_kind"] = "complete" };
        Bench.WriteResult(Bench.Out(), r, "bfs", Bench.Impl(), params_);
    }
}
