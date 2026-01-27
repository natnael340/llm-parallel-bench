using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Linq;
using System.Security.Cryptography;
using System.Text;

public class TestSCC
{
    // Helper: Compute deterministic hash of edge list
    private static string ComputeHash(List<(int, int)> edges)
    {
        // Sort edges for deterministic hash
        var sorted = edges.OrderBy(e => e.Item1).ThenBy(e => e.Item2).ToList();
        
        var sb = new StringBuilder();
        foreach (var edge in sorted)
        {
            sb.Append($"{edge.Item1},{edge.Item2};");
        }
        
        using (var sha256 = SHA256.Create())
        {
            byte[] hashBytes = sha256.ComputeHash(Encoding.UTF8.GetBytes(sb.ToString()));
            return BitConverter.ToString(hashBytes).Replace("-", "").Substring(0, 16);
        }
    }

    // Helper: Compare two edge lists for equality
    private static bool EdgesEqual(List<(int, int)> edges1, List<(int, int)> edges2)
    {
        if (edges1.Count != edges2.Count) return false;
        
        var sorted1 = edges1.OrderBy(e => e.Item1).ThenBy(e => e.Item2).ToList();
        var sorted2 = edges2.OrderBy(e => e.Item1).ThenBy(e => e.Item2).ToList();
        
        for (int i = 0; i < sorted1.Count; i++)
        {
            if (sorted1[i] != sorted2[i]) return false;
        }
        return true;
    }

    // Build a simple cyclic graph
    private static Graph BuildGraphSequential(int vertices, List<(int, int)> edges)
    {
        var g = new Graph(vertices);
        foreach (var edge in edges)
        {
            g.AddEdge(edge.Item1, edge.Item2);
        }
        return g;
    }

    private static GraphParallel BuildGraphParallel(int vertices, List<(int, int)> edges)
    {
        var g = new GraphParallel(vertices);
        foreach (var edge in edges)
        {
            g.AddEdge(edge.Item1, edge.Item2);
        }
        return g;
    }

    // Test case: Edge case - single vertex
    private static bool TestEdgeSingleVertex()
    {
        Console.WriteLine("\n=== Test: Edge - Single Vertex ===");
        var edges = new List<(int, int)>();
        
        var gSeq = BuildGraphSequential(1, edges);
        var gPar = BuildGraphParallel(1, edges);
        
        var seqResult = gSeq.ReduceEdges();
        var parResult = gPar.ReduceEdges();
        
        bool match = EdgesEqual(seqResult, parResult);
        Console.WriteLine($"Sequential edges: {seqResult.Count}, Parallel edges: {parResult.Count}");
        Console.WriteLine($"Match: {match}");
        return match;
    }

    // Test case: Small graph - 5 vertices with 2 SCCs
    private static bool TestSmallGraph()
    {
        Console.WriteLine("\n=== Test: Small - 5 vertices, 2 SCCs ===");
        var edges = new List<(int, int)>
        {
            (0, 1), (1, 2), (2, 0),  // SCC 1: 0-1-2
            (2, 3), (3, 4), (4, 3)   // SCC 2: 3-4
        };
        
        var gSeq = BuildGraphSequential(5, edges);
        var gPar = BuildGraphParallel(5, edges);
        
        var seqResult = gSeq.ReduceEdges();
        var parResult = gPar.ReduceEdges();
        
        bool match = EdgesEqual(seqResult, parResult);
        Console.WriteLine($"Sequential edges: {seqResult.Count}, Parallel edges: {parResult.Count}");
        Console.WriteLine($"Match: {match}");
        return match;
    }

    // Test case: Medium graph - 20 vertices with multiple SCCs
    private static bool TestMediumGraph()
    {
        Console.WriteLine("\n=== Test: Medium - 20 vertices, multiple SCCs ===");
        var edges = new List<(int, int)>();
        
        // Create 5 SCCs of 4 vertices each
        for (int scc = 0; scc < 5; scc++)
        {
            int base_v = scc * 4;
            edges.Add((base_v, base_v + 1));
            edges.Add((base_v + 1, base_v + 2));
            edges.Add((base_v + 2, base_v + 3));
            edges.Add((base_v + 3, base_v));
            
            // Inter-SCC edges
            if (scc < 4)
            {
                edges.Add((base_v + 3, base_v + 4));
            }
        }
        
        var gSeq = BuildGraphSequential(20, edges);
        var gPar = BuildGraphParallel(20, edges);
        
        var seqResult = gSeq.ReduceEdges();
        var parResult = gPar.ReduceEdges();
        
        bool match = EdgesEqual(seqResult, parResult);
        Console.WriteLine($"Sequential edges: {seqResult.Count}, Parallel edges: {parResult.Count}");
        Console.WriteLine($"Match: {match}");
        return match;
    }

    // Test case: Large graph - 200 vertices with many SCCs
    private static (bool, double, double, string, string) TestLargeGraph()
    {
        Console.WriteLine("\n=== Test: Large - 200 vertices, many SCCs ===");
        var edges = new List<(int, int)>();
        
        // Create 40 SCCs of 5 vertices each
        for (int scc = 0; scc < 40; scc++)
        {
            int base_v = scc * 5;
            for (int i = 0; i < 5; i++)
            {
                edges.Add((base_v + i, base_v + (i + 1) % 5));
            }
            
            // Inter-SCC edges
            if (scc < 39)
            {
                edges.Add((base_v + 4, base_v + 5));
            }
        }
        
        var gSeq = BuildGraphSequential(200, edges);
        var gPar = BuildGraphParallel(200, edges);
        
        // Sequential run
        var sw = Stopwatch.StartNew();
        var seqResult = gSeq.ReduceEdges();
        sw.Stop();
        double seqTime = sw.Elapsed.TotalMilliseconds;
        string seqHash = ComputeHash(seqResult);
        
        // Parallel run 1
        sw.Restart();
        var parResult1 = gPar.ReduceEdges();
        sw.Stop();
        double parTime = sw.Elapsed.TotalMilliseconds;
        string parHash1 = ComputeHash(parResult1);
        
        // Parallel run 2 (determinism check)
        var gPar2 = BuildGraphParallel(200, edges);
        var parResult2 = gPar2.ReduceEdges();
        string parHash2 = ComputeHash(parResult2);
        
        bool match = EdgesEqual(seqResult, parResult1);
        bool deterministic = parHash1 == parHash2;
        
        Console.WriteLine($"Sequential: {seqResult.Count} edges, {seqTime:F2}ms, hash={seqHash}");
        Console.WriteLine($"Parallel 1: {parResult1.Count} edges, {parTime:F2}ms, hash={parHash1}");
        Console.WriteLine($"Parallel 2: {parResult2.Count} edges, hash={parHash2}");
        Console.WriteLine($"Correctness match: {match}");
        Console.WriteLine($"Determinism (hash match): {deterministic}");
        Console.WriteLine($"Speedup: {seqTime / parTime:F2}x");
        
        return (match && deterministic, seqTime, parTime, parHash1, parHash2);
    }

    public static int Main(string[] args)
    {
        Console.WriteLine("=== SCC Edge Reduction Differential Tests ===");
        Console.WriteLine($"Processors available: {Environment.ProcessorCount}");
        
        bool allPassed = true;
        
        // Edge cases
        allPassed &= TestEdgeSingleVertex();
        
        // Small (sequential fallback)
        allPassed &= TestSmallGraph();
        
        // Medium (triggers parallelism)
        allPassed &= TestMediumGraph();
        
        // Large (performance + determinism check)
        var (largePass, seqTime, parTime, hash1, hash2) = TestLargeGraph();
        allPassed &= largePass;
        
        // Summary
        Console.WriteLine("\n=== SUMMARY ===");
        if (allPassed)
        {
            Console.WriteLine("✓ All tests PASSED");
            Console.WriteLine($"  Large test: seq={seqTime:F2}ms, par={parTime:F2}ms, speedup={seqTime/parTime:F2}x");
            Console.WriteLine($"  Determinism: hash1={hash1}, hash2={hash2}, match={hash1 == hash2}");
            return 0;
        }
        else
        {
            Console.WriteLine("✗ Some tests FAILED");
            return 1;
        }
    }
}
