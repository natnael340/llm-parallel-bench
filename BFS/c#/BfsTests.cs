using System;
using System.Collections.Generic;
using System.Diagnostics;
using Xunit;
using Xunit.Abstractions;

using Bfs = BfsSequential;

public class BfsTests
{
    private readonly ITestOutputHelper _output;
    private Graph _graph;

    public BfsTests(ITestOutputHelper output)
    {
        _output = output;
        _graph = new Graph();
    }

    [Fact]
    public void Bfs_EmptyGraph_ReturnsEmptyList()
    {
        var result = Bfs.Run(_graph, 0);
        Assert.Equal(new List<int>(), result);
    }

    [Fact]
    public void Bfs_SingleNode_ReturnsSingleNode()
    {
        _graph.AddEdge(1, 1);
        var result = Bfs.Run(_graph, 1);
        Assert.Equal(new List<int> { 1 }, result);
    }

    [Fact]
    public void Bfs_LinearEdge_ReturnsNodesInOrder()
    {
        _graph.AddEdge(1, 2);
        _graph.AddEdge(2, 3);
        _graph.AddEdge(3, 4);

        var result = Bfs.Run(_graph, 1);
        Assert.Equal(new List<int> { 1, 2, 3, 4 }, result);
    }

    [Fact]
    public void Bfs_CompleteGraph_ReturnsCorrectOrder()
    {
        var nodes = new List<int> { 1, 2, 3, 4 };
        foreach (var i in nodes)
        {
            foreach (var j in nodes)
            {
                if (i != j)
                    _graph.AddEdge(i, j);
            }
        }

        var result = Bfs.Run(_graph, 3);
        Assert.Equal(new List<int> { 3, 1, 2, 4 }, result);
    }

    [Fact]
    public void Bfs_StarGraph_ReturnsCenterThenLeaves()
    {
        int center = 1;
        var leaves = new List<int> { 2, 3, 4, 5 };
        foreach (var leaf in leaves)
        {
            _graph.AddEdge(center, leaf);
        }

        var result = Bfs.Run(_graph, center);
        var expected = new List<int> { center };
        expected.AddRange(leaves);
        Assert.Equal(expected, result);
    }

    [Fact]
    public void Bfs_Cycle_HandlesCorrectly()
    {
        var edges = new List<(int, int)> { (1, 2), (2, 3), (3, 4), (4, 1) };
        foreach (var (fromV, toV) in edges)
        {
            _graph.AddEdge(fromV, toV);
        }

        var result = Bfs.Run(_graph, 1);
        Assert.Equal(new List<int> { 1, 2, 4, 3 }, result);
    }

    [Fact]
    public void Bfs_TreeStructure_ReturnsLevelOrder()
    {
        var edges = new List<(int, int)> { (1, 2), (1, 3), (2, 4), (2, 5), (3, 6), (3, 7) };
        foreach (var (fromV, toV) in edges)
        {
            _graph.AddEdge(fromV, toV);
        }

        var result = Bfs.Run(_graph, 1);
        Assert.Equal(new List<int> { 1, 2, 3, 4, 5, 6, 7 }, result);
    }

    [Fact]
    public void Bfs_DisconnectedComponents_OnlyVisitsConnectedComponent()
    {
        // Component 1: 1-2-3
        _graph.AddEdge(1, 2);
        _graph.AddEdge(2, 3);
        // Component 2: 4-5-6
        _graph.AddEdge(4, 5);
        _graph.AddEdge(4, 6);

        var result1 = Bfs.Run(_graph, 1);
        Assert.Equal(new List<int> { 1, 2, 3 }, result1);

        var result2 = Bfs.Run(_graph, 4);
        Assert.Equal(new List<int> { 4, 5, 6 }, result2);
    }

    [Fact]
    public void Bfs_DuplicateEdges_HandlesCorrectly()
    {
        _graph.AddEdge(1, 2);
        _graph.AddEdge(1, 2); // Duplicate
        _graph.AddEdge(2, 3);

        var result = Bfs.Run(_graph, 1);
        Assert.Equal(new List<int> { 1, 2, 3 }, result);
    }

    [Fact]
    public void Bfs_NonexistentStartVertex_ReturnsEmptyList()
    {
        _graph.AddEdge(1, 2);

        var result = Bfs.Run(_graph, 999);
        Assert.Equal(new List<int>(), result);
    }

    [Fact]
    public void Bfs_ComplexGraph_ReturnsCorrectOrder()
    {
        var edges = new List<(int, int)>
        {
            (1, 2), (1, 3), (2, 4), (3, 4), (4, 5),
            (5, 6), (6, 7), (5, 7), (7, 8), (3, 8)
        };
        foreach (var (fromV, toV) in edges)
        {
            _graph.AddEdge(fromV, toV);
        }

        var result = Bfs.Run(_graph, 1);
        Assert.Equal(new List<int> { 1, 2, 3, 4, 8, 5, 7, 6 }, result);
    }

    [Fact]
    public void Bfs_OrderConsistency_MaintainsConsistentOrder()
    {
        _graph.AddEdge(1, 3);
        _graph.AddEdge(1, 2);

        var results = new List<List<int>>();
        for (int i = 0; i < 5; i++)
        {
            results.Add(Bfs.Run(_graph, 1));
        }

        foreach (var result in results)
        {
            Assert.Equal(results[0], result);
        }
    }

    [Fact]
    public void Bfs_PerformanceStressTest_HandlesLargeGraph()
    {
        int size = 1000;
        for (int i = 1; i < size; i++)
        {
            _graph.AddEdge(i, i + 1);
        }

        var result = Bfs.Run(_graph, 1);
        Assert.Equal(size, result.Count);
        Assert.Equal(1, result[0]);
        Assert.Equal(size, result[^1]);
    }

    [Fact]
    public void Bfs_PerformanceSpeedTest_MeasuresExecutionTime()
    {
        int size = 2000;
        for (int i = 1; i <= size; i++)
        {
            for (int j = i + 1; j <= size; j++)
            {
                _graph.AddEdge(i, j);
                _graph.AddEdge(j, i);
            }
        }

        // Warm-up
        Bfs.Run(_graph, 1);

        int reps = 5;
        int iters = 20;
        var times = new List<double>();

        for (int r = 0; r < reps; r++)
        {
            var sw = Stopwatch.StartNew();
            for (int i = 0; i < iters; i++)
            {
                Bfs.Run(_graph, 1);
            }
            sw.Stop();
            times.Add(sw.Elapsed.TotalMilliseconds / iters);
        }

        double avg = Average(times);
        double sd = StandardDeviation(times);

        _output.WriteLine($"BFS complete graph | nodes={size}, undirected edges≈{size * (size - 1) / 2:N0} " +
                          $"(directed≈{size * (size - 1):N0}) | {avg:F2} ms/run ± {sd:F2} (n={reps})");
    }

    private static double Average(List<double> values)
    {
        double sum = 0;
        foreach (var v in values) sum += v;
        return sum / values.Count;
    }

    private static double StandardDeviation(List<double> values)
    {
        double avg = Average(values);
        double sumSquares = 0;
        foreach (var v in values)
        {
            sumSquares += (v - avg) * (v - avg);
        }
        return Math.Sqrt(sumSquares / values.Count);
    }
}