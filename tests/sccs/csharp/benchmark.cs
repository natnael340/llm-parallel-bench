using System;
using System.Collections.Generic;

namespace SCC
{

class Program
{
    // --- correctness: SCC strong-check heuristic (mirrors the Go harness) ---
    // For SCC of size k>1: (k-1) <= internal edges <= 2*(k-1), and every SCC
    // node appears in at least one kept internal edge.
    static bool IsSccStrong(List<int> sccNodes, List<(int, int)> edges)
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
        if (internalEdges < k - 1) return false;
        if (internalEdges > 2 * (k - 1)) return false;
        if (touched.Count < k) return false;
        return true;
    }

    static bool CheckAllSCCs(BenchImpl g)
    {
        var edges = g.ReduceEdges();
        foreach (var scc in g.FindSCCs())
        {
            if (!IsSccStrong(scc, edges)) return false;
        }
        return true;
    }

    static int Report(string name, bool ok)
    {
        Console.WriteLine(name + (ok ? " passed" : " failed"));
        return ok ? 0 : 1;
    }

    static int RunCorrectnessChecks()
    {
        int failures = 0;

        var g1 = new BenchImpl(3);
        g1.AddEdge(0, 1); g1.AddEdge(1, 2); g1.AddEdge(2, 0);
        failures += Report("test_scc_3cycle", CheckAllSCCs(g1));

        var g2 = new BenchImpl(2);
        g2.AddEdge(0, 1); g2.AddEdge(1, 0);
        failures += Report("test_scc_2node_mutual", CheckAllSCCs(g2));

        var g3 = new BenchImpl(5);
        g3.AddEdge(0, 1); g3.AddEdge(1, 2); g3.AddEdge(2, 0);
        g3.AddEdge(3, 4); g3.AddEdge(4, 3);
        g3.AddEdge(2, 3);
        failures += Report("test_scc_multiple", CheckAllSCCs(g3));

        var g4 = new BenchImpl(7);
        g4.AddEdge(0, 1); g4.AddEdge(1, 2); g4.AddEdge(1, 3); g4.AddEdge(1, 4);
        g4.AddEdge(2, 0); g4.AddEdge(2, 3); g4.AddEdge(3, 5); g4.AddEdge(5, 3);
        g4.AddEdge(5, 4); g4.AddEdge(5, 6); g4.AddEdge(6, 4); g4.AddEdge(4, 6);
        failures += Report("test_scc_7node", CheckAllSCCs(g4));

        return failures;
    }

    // --- benchmark graph construction (shared with all languages) ---

    static void RingSCC(int start, int end, BenchImpl g)
    {
        for (int i = start; i < end; i++)
        {
            int v = (i + 1) % end;
            if (v == 0) v = start;
            if (i == v) continue;
            g.AddEdge(i, v);
        }
    }

    static BenchImpl BuildGraph(int graphSize, int clusterSize, int noClusterInGroup)
    {
        BenchImpl g = new BenchImpl(graphSize);
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

        BenchImpl g = BuildGraph(graphSize, clusterSize, noClusterInGroup);

        int reps = Bench.Reps(5);
        int iters = Bench.Iters(20);

        var r = Bench.Run(() => g.ReduceEdges(), reps, iters, 1);

        Console.WriteLine(Bench.Format($"SCC ReduceEdges | graph_size={graphSize}", r));

        var params_ = new Dictionary<string, object>
        {
            ["graph_size"] = graphSize,
            ["cluster_size"] = clusterSize,
            ["no_cluster_in_group"] = noClusterInGroup,
        };
        Bench.WriteResult(filename, r, "sccs", Bench.Impl(), params_);
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

    static int Main(string[] args)
    {
        var argDict = ParseArgs(args);

        // Output path: --out flag, else BENCH_OUT env (may be empty: print only).
        string filename = argDict.TryGetValue("out", out var outArg) ? outArg : Bench.Out();

        int failures = RunCorrectnessChecks();
        if (failures > 0)
        {
            Console.WriteLine($"{failures} correctness check(s) failed — skipping benchmark");
            return 1;
        }

        BenchmarkReduceEdges(filename);
        return 0;
    }
}
}
