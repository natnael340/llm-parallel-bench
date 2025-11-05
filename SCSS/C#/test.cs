using System;
using System.Collections.Generic;
using System.Diagnostics;

namespace LLMParallelBench.Tests
{
class GraphAllTests
{
    public static void RunAll()
    {
        Console.WriteLine("=== Running SCC edge-minimization tests ===");
        int failed = 0;

        // local helper: check SCC strong connectivity using only given edges
        bool IsSccStrong(List<int> sccNodes, List<(int, int)> edges)
        {
            var nodeSet = new HashSet<int>(sccNodes);

            // build small forward / reverse graphs only for this SCC
            var fwd = new Dictionary<int, List<int>>();
            var rev = new Dictionary<int, List<int>>();
            foreach (var n in sccNodes)
            {
                fwd[n] = new List<int>();
                rev[n] = new List<int>();
            }

            foreach (var (u, v) in edges)
            {
                if (nodeSet.Contains(u) && nodeSet.Contains(v))
                {
                    fwd[u].Add(v);
                    rev[v].Add(u);
                }
            }

            int start = sccNodes[0];

            // forward DFS
            var seenF = new HashSet<int>();
            var stack = new Stack<int>();
            stack.Push(start);
            seenF.Add(start);
            while (stack.Count > 0)
            {
                var x = stack.Pop();
                foreach (var nb in fwd[x])
                {
                    if (seenF.Add(nb))
                        stack.Push(nb);
                }
            }

            // reverse DFS
            var seenR = new HashSet<int>();
            stack.Push(start);
            seenR.Add(start);
            while (stack.Count > 0)
            {
                var x = stack.Pop();
                foreach (var nb in rev[x])
                {
                    if (seenR.Add(nb))
                        stack.Push(nb);
                }
            }

            return seenF.Count == sccNodes.Count && seenR.Count == sccNodes.Count;
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
            bool ok = true;
            foreach (var scc in sccs)
            {
                if (!IsSccStrong(scc, edges))
                    ok = false;
            }
            Console.WriteLine("[Single node, no edges] " + (ok ? "PASS" : "FAIL"));
            if (!ok) failed++;
        }

        // ========== 3) single node, self-loop ==========
        {
            var g = new Graph(1);
            g.AddEdge(0, 0);
            var edges = g.ReduceEdges();
            var sccs = g.FindSCCs();
            bool ok = true;
            foreach (var scc in sccs)
            {
                if (!IsSccStrong(scc, edges))
                    ok = false;
            }
            Console.WriteLine("[Single node, self-loop] " + (ok ? "PASS" : "FAIL"));
            if (!ok) failed++;
        }

        // ========== 4) simple 3-cycle 0->1->2->0 ==========
        {
            var g = new Graph(3);
            g.AddEdge(0, 1);
            g.AddEdge(1, 2);
            g.AddEdge(2, 0);

            var edges = g.ReduceEdges();
            var sccs = g.FindSCCs();
            bool ok = true;
            foreach (var scc in sccs)
            {
                if (!IsSccStrong(scc, edges))
                    ok = false;
            }
            Console.WriteLine("[Simple 3-cycle] " + (ok ? "PASS" : "FAIL"));
            if (!ok)
            {
                Console.WriteLine("  Reduced edges:");
                foreach (var e in edges) Console.WriteLine($"    {e.Item1} -> {e.Item2}");
                failed++;
            }
        }

        // ========== 5) two-node mutual SCC ==========
        {
            var g = new Graph(2);
            g.AddEdge(0, 1);
            g.AddEdge(1, 0);

            var edges = g.ReduceEdges();
            var sccs = g.FindSCCs();
            bool ok = true;
            foreach (var scc in sccs)
            {
                if (!IsSccStrong(scc, edges))
                    ok = false;
            }
            Console.WriteLine("[2-node mutual SCC] " + (ok ? "PASS" : "FAIL"));
            if (!ok) failed++;
        }

        // ========== 6) dense-ish single SCC ==========
        // 0->1->2->0, plus 0->2, 1->0, 2->1
        {
            var g = new Graph(3);
            g.AddEdge(0, 1);
            g.AddEdge(1, 2);
            g.AddEdge(2, 0);
            g.AddEdge(0, 2);
            g.AddEdge(1, 0);
            g.AddEdge(2, 1);

            var edges = g.ReduceEdges();
            var sccs = g.FindSCCs();
            bool ok = true;
            foreach (var scc in sccs)
            {
                if (!IsSccStrong(scc, edges))
                    ok = false;
            }
            Console.WriteLine("[Dense 3-node SCC] " + (ok ? "PASS" : "FAIL"));
            if (!ok)
            {
                Console.WriteLine("  Reduced edges:");
                foreach (var e in edges) Console.WriteLine($"    {e.Item1} -> {e.Item2}");
                failed++;
            }
        }

        // ========== 7) multiple SCCs ==========
        // SCC1: 0<->1<->2<->0
        // SCC2: 3<->4
        // cross: 2->3
        {
            var g = new Graph(5);
            // SCC1
            g.AddEdge(0, 1);
            g.AddEdge(1, 2);
            g.AddEdge(2, 0);
            // SCC2
            g.AddEdge(3, 4);
            g.AddEdge(4, 3);
            // cross
            g.AddEdge(2, 3);

            var edges = g.ReduceEdges();
            var sccs = g.FindSCCs();
            bool ok = true;
            foreach (var scc in sccs)
            {
                if (!IsSccStrong(scc, edges))
                    ok = false;
            }
            Console.WriteLine("[Multiple SCCs] " + (ok ? "PASS" : "FAIL"));
            if (!ok)
            {
                Console.WriteLine("  Reduced edges:");
                foreach (var e in edges) Console.WriteLine($"    {e.Item1} -> {e.Item2}");
                failed++;
            }
        }

        // ========== 8) your provided 7-node example graph ==========
        {
            var g = new Graph(7);

            g.AddEdge(0, 1);
            g.AddEdge(1, 2);
            g.AddEdge(1, 3);
            g.AddEdge(1, 4);
            g.AddEdge(2, 0);
            g.AddEdge(2, 3);
            g.AddEdge(3, 5);
            g.AddEdge(5, 3);
            g.AddEdge(5, 4);
            g.AddEdge(5, 6);
            g.AddEdge(6, 4);
            g.AddEdge(4, 6);

            var edges = g.ReduceEdges();
            var sccs = g.FindSCCs();
            bool ok = true;
            foreach (var scc in sccs)
            {
                if (!IsSccStrong(scc, edges))
                    ok = false;
            }
            Console.WriteLine("[Your 7-node graph] " + (ok ? "PASS" : "FAIL"));
            if (!ok)
            {
                Console.WriteLine("  Reduced edges:");
                foreach (var e in edges) Console.WriteLine($"    {e.Item1} -> {e.Item2}");
                failed++;
            }
        }

        // ========== 9) stress + performance test ==========
        {
            Console.WriteLine("=== Stress / Performance test ===");
            int n = 2000;
            int runs = 5;
            long totalTicks = 0;

            for (int r = 0; r < runs; r++)
            {
                var g = new Graph(n);

                // make a big strongly-connected graph:
                // ring + one extra forward edge to increase E
                for (int i = 0; i < n; i++)
                {
                    int next = (i + 1) % n;
                    g.AddEdge(i, next);               // ring
                    int next2 = (i + 13) % n;         // jump edge to ensure more paths
                    g.AddEdge(i, next2);
                }

                var sw = Stopwatch.StartNew();
                var edges = g.ReduceEdges();
                sw.Stop();
                totalTicks += sw.ElapsedTicks;

                // quick sanity: there should be at least n-1 edges (forward tree)
                if (edges.Count == 0)
                {
                    Console.WriteLine("  [Stress run " + r + "] FAIL: no edges returned");
                    failed++;
                }
                else
                {
                    Console.WriteLine("  [Stress run " + r + "] edges kept: " + edges.Count + ", time: " + sw.ElapsedMilliseconds + " ms");
                }

                // optional: verify 1 SCC still strong
                var sccs = g.FindSCCs();
                bool ok = true;
                foreach (var scc in sccs)
                {
                    if (!IsSccStrong(scc, edges))
                        ok = false;
                }
                if (!ok)
                {
                    Console.WriteLine("  [Stress run " + r + "] FAIL: reduced edges broke SCC");
                    failed++;
                }
            }

            double avgMs = (totalTicks / (double)runs) * 1000.0 / Stopwatch.Frequency;
            Console.WriteLine($"Average time over {runs} runs (n={n}): {avgMs:F3} ms");
        }

        Console.WriteLine("=== Tests finished ===");
        Console.WriteLine(failed == 0 ? "ALL PASSED ✅" : $"{failed} TEST(S) FAILED ❌");
    }
}
}