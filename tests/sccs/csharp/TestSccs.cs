// Swap the line below to switch between sequential and parallel implementations.
using Graph = SCC.Par.Graph;
// using Graph = SCC.Par.Graph;

using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Linq;

namespace SCC.Tests
{
class GraphAllTests
{
    public static void RunAll()
    {
        Console.WriteLine("=== Running SCC edge-minimization tests ===");
        int failed = 0;

        bool IsSccStrong(List<int> sccNodes, List<(int, int)> edges)
        {
            var nodeSet = new HashSet<int>(sccNodes);
            int k = sccNodes.Count;
            if (k <= 1) return true;

            int internalEdges = 0;
            var touched = new HashSet<int>();
            foreach (var (u, v) in edges)
            {
                if (nodeSet.Contains(u) && nodeSet.Contains(v))
                {
                    internalEdges++;
                    touched.Add(u);
                    touched.Add(v);
                }
            }

            if (internalEdges < (k - 1)) return false;
            if (internalEdges > 2 * (k - 1)) return false;
            if (touched.Count < k) return false;
            return true;
        }

        // ========== 1) empty graph ==========
        try
        {
            var g0 = new Graph(0);
            var edges0 = g0.ReduceEdges();
            Console.WriteLine("[Empty graph] PASS (no crash)");
        }
        catch (Exception ex)
        {
            Console.WriteLine("[Empty graph] FAIL: " + ex.Message);
            failed++;
        }

        // ========== 2) single node, no edges ==========
        {
            var g = new Graph(1);
            var edges = g.ReduceEdges();
            var sccs = g.FindSCCs();
            bool ok = sccs.All(scc => IsSccStrong(scc, edges));
            Console.WriteLine("[Single node, no edges] " + (ok ? "PASS" : "FAIL"));
            if (!ok) failed++;
        }

        // ========== 3) single node, self-loop ==========
        {
            var g = new Graph(1);
            g.AddEdge(0, 0);
            var edges = g.ReduceEdges();
            var sccs = g.FindSCCs();
            bool ok = sccs.All(scc => IsSccStrong(scc, edges));
            Console.WriteLine("[Single node, self-loop] " + (ok ? "PASS" : "FAIL"));
            if (!ok) failed++;
        }

        // ========== 4) simple 3-cycle 0->1->2->0 ==========
        {
            var g = new Graph(3);
            g.AddEdge(0, 1); g.AddEdge(1, 2); g.AddEdge(2, 0);
            var edges = g.ReduceEdges();
            var sccs = g.FindSCCs();
            bool ok = sccs.All(scc => IsSccStrong(scc, edges));
            Console.WriteLine("[Simple 3-cycle] " + (ok ? "PASS" : "FAIL"));
            if (!ok) { foreach (var e in edges) Console.WriteLine($"  {e.Item1} -> {e.Item2}"); failed++; }
        }

        // ========== 5) two-node mutual SCC ==========
        {
            var g = new Graph(2);
            g.AddEdge(0, 1); g.AddEdge(1, 0);
            var edges = g.ReduceEdges();
            var sccs = g.FindSCCs();
            bool ok = sccs.All(scc => IsSccStrong(scc, edges));
            Console.WriteLine("[2-node mutual SCC] " + (ok ? "PASS" : "FAIL"));
            if (!ok) failed++;
        }

        // ========== 6) dense 3-node SCC ==========
        {
            var g = new Graph(3);
            g.AddEdge(0, 1); g.AddEdge(1, 2); g.AddEdge(2, 0);
            g.AddEdge(0, 2); g.AddEdge(1, 0); g.AddEdge(2, 1);
            var edges = g.ReduceEdges();
            var sccs = g.FindSCCs();
            bool ok = sccs.All(scc => IsSccStrong(scc, edges));
            Console.WriteLine("[Dense 3-node SCC] " + (ok ? "PASS" : "FAIL"));
            if (!ok) { foreach (var e in edges) Console.WriteLine($"  {e.Item1} -> {e.Item2}"); failed++; }
        }

        // ========== 7) multiple SCCs ==========
        {
            var g = new Graph(5);
            g.AddEdge(0, 1); g.AddEdge(1, 2); g.AddEdge(2, 0);
            g.AddEdge(3, 4); g.AddEdge(4, 3);
            g.AddEdge(2, 3);
            var edges = g.ReduceEdges();
            var sccs = g.FindSCCs();
            bool ok = sccs.All(scc => IsSccStrong(scc, edges));
            Console.WriteLine("[Multiple SCCs] " + (ok ? "PASS" : "FAIL"));
            if (!ok) { foreach (var e in edges) Console.WriteLine($"  {e.Item1} -> {e.Item2}"); failed++; }
        }

        // ========== 8) 7-node example graph ==========
        {
            var g = new Graph(7);
            g.AddEdge(0, 1); g.AddEdge(1, 2); g.AddEdge(1, 3); g.AddEdge(1, 4);
            g.AddEdge(2, 0); g.AddEdge(2, 3); g.AddEdge(3, 5); g.AddEdge(5, 3);
            g.AddEdge(5, 4); g.AddEdge(5, 6); g.AddEdge(6, 4); g.AddEdge(4, 6);
            var edges = g.ReduceEdges();
            var sccs = g.FindSCCs();
            bool ok = sccs.All(scc => IsSccStrong(scc, edges));
            Console.WriteLine("[7-node graph] " + (ok ? "PASS" : "FAIL"));
            if (!ok) { foreach (var e in edges) Console.WriteLine($"  {e.Item1} -> {e.Item2}"); failed++; }
        }

        // ========== 9) stress + performance test ==========
        {
            Console.WriteLine("=== Stress / Performance test ===");
            int n = 2000, runs = 5;
            long totalTicks = 0;

            for (int r = 0; r < runs; r++)
            {
                var g = new Graph(n);
                for (int i = 0; i < n; i++)
                {
                    g.AddEdge(i, (i + 1) % n);
                    g.AddEdge(i, (i + 13) % n);
                }

                var sw = Stopwatch.StartNew();
                var edges = g.ReduceEdges();
                sw.Stop();
                totalTicks += sw.ElapsedTicks;

                if (edges.Count == 0)
                {
                    Console.WriteLine($"  [Stress run {r}] FAIL: no edges returned");
                    failed++;
                }
                else
                {
                    Console.WriteLine($"  [Stress run {r}] edges kept: {edges.Count}, time: {sw.ElapsedMilliseconds} ms");
                }

                var sccs = g.FindSCCs();
                if (!sccs.All(scc => IsSccStrong(scc, edges)))
                {
                    Console.WriteLine($"  [Stress run {r}] FAIL: reduced edges broke SCC");
                    failed++;
                }
            }

            double avgMs = (totalTicks / (double)runs) * 1000.0 / Stopwatch.Frequency;
            Console.WriteLine($"Average time over {runs} runs (n={n}): {avgMs:F3} ms");
        }

        // ========== 10) Determinism test ==========
        {
            Console.WriteLine("=== Determinism test (randomized large graph, multiple SCCs) ===");

            int numScc = 24, sccSize = 40, n = numScc * sccSize, runs = 5;

            Graph BuildRandomGraph(int seed)
            {
                var rand = new Random(seed);
                var g = new Graph(n);

                for (int s = 0; s < numScc; s++)
                {
                    int start = s * sccSize;
                    for (int u = start; u < start + sccSize; u++)
                        g.AddEdge(u, start + ((u - start + 1) % sccSize));
                    for (int i = 0; i < sccSize * 3; i++)
                    {
                        int u = start + rand.Next(sccSize);
                        int v = start + rand.Next(sccSize);
                        if (u != v) g.AddEdge(u, v);
                    }
                }
                for (int s = 0; s < numScc - 1; s++)
                {
                    int a0 = s * sccSize, b0 = (s + 1) * sccSize;
                    for (int i = 0; i < 6; i++)
                        g.AddEdge(a0 + rand.Next(sccSize), b0 + rand.Next(sccSize));
                }
                return g;
            }

            string Signature(List<(int, int)> edges) =>
                string.Join(";", edges.Select(e => $"{e.Item1},{e.Item2}"));

            bool ok = true;
            string baseline = "";
            int baselineCount = -1;
            int seed = Random.Shared.Next();
            var g = BuildRandomGraph(seed);
            var sccs = g.FindSCCs();

            for (int r = 0; r < runs; r++)
            {
                var sw = Stopwatch.StartNew();
                var edges = g.ReduceEdges();
                sw.Stop();

                foreach (var scc in sccs)
                {
                    if (!IsSccStrong(scc, edges))
                    {
                        ok = false;
                        Console.WriteLine($"  [Det run {r}] FAIL: reduced edges broke SCC");
                        break;
                    }
                }

                string sig = Signature(edges);
                if (r == 0) { baseline = sig; baselineCount = edges.Count; }
                else if (!sig.Equals(baseline, StringComparison.Ordinal))
                {
                    ok = false;
                    Console.WriteLine($"  [Det run {r}] FAIL: output differs from run 0");
                }

                Console.WriteLine($"  [Det run {r}] seed: {seed}, SCCs: {sccs.Count}, edges kept: {edges.Count}, time: {sw.ElapsedMilliseconds} ms");
            }

            Console.WriteLine("[Determinism randomized large multi-SCC] " + (ok ? "PASS" : "FAIL"));
            if (!ok) { Console.WriteLine($"  Baseline seed: {seed}, edge count: {baselineCount}"); failed++; }
        }

        Console.WriteLine("=== Tests finished ===");
        Console.WriteLine(failed == 0 ? "ALL PASSED" : $"{failed} TEST(S) FAILED");
    }
}
}
