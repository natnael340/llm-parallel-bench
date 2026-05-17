using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Linq;
using System.Security.Cryptography;
using System.Text;

public static class Program
{
    static string HashList(List<int> list)
    {
        using var sha = SHA256.Create();
        var bytes = Encoding.UTF8.GetBytes(string.Join(",", list));
        var hash = sha.ComputeHash(bytes);
        return BitConverter.ToString(hash).Replace("-", "");
    }

    static Graph MakeLine(int n)
    {
        var g = new Graph();
        for (int i = 0; i < n - 1; i++) g.AddEdge(i, i + 1);
        if (n == 1) g.AddEdge(0, 0); // ensure vertex exists
        return g;
    }

    static Graph MakeGrid(int w, int h)
    {
        int Id(int x, int y) => y * w + x;
        var g = new Graph();
        for (int y = 0; y < h; y++)
        for (int x = 0; x < w; x++)
        {
            if (x + 1 < w) g.AddEdge(Id(x, y), Id(x + 1, y));
            if (y + 1 < h) g.AddEdge(Id(x, y), Id(x, y + 1));
        }
        return g;
    }

    static Graph MakeRandom(int n, int m, int seed)
    {
        var g = new Graph();
        var rnd = new Random(seed);
        if (n <= 0) return g;
        // ensure all vertices exist by connecting each to itself then remove later? Graph has no remove.
        // Instead connect in a ring first
        for (int i = 0; i < Math.Max(1, n - 1); i++) g.AddEdge(i, (i + 1) % n);
        for (int i = 0; i < m; i++)
        {
            int a = rnd.Next(n);
            int b = rnd.Next(n);
            if (a != b) g.AddEdge(a, b);
        }
        return g;
    }

    static (bool ok, string msg) CheckCase(string name, Graph g, int start)
    {
        var seq = BfsSequential.Run(g, start);
        var par1 = Bfs.Run(g, start);
        var par2 = Bfs.Run(g, start);
        bool same12 = par1.SequenceEqual(par2);
        bool same = seq.SequenceEqual(par1);
        string h1 = HashList(par1);
        string h2 = HashList(par2);
        return (same && same12, $"{name}: seq==par:{same}, par deterministic:{same12}, hash1={h1}, hash2={h2}, len={par1.Count}");
    }

    static void PerfCase(string name, Graph g, int start, StringBuilder perfOut)
    {
        var sw = new Stopwatch();
        // warmup
        BfsSequential.Run(g, start);
        Bfs.Run(g, start);

        sw.Restart();
        var seq = BfsSequential.Run(g, start);
        sw.Stop();
        long tSeq = sw.ElapsedMilliseconds;

        sw.Restart();
        var par = Bfs.Run(g, start);
        sw.Stop();
        long tPar = sw.ElapsedMilliseconds;

        double speedup = tPar > 0 ? (double)tSeq / tPar : double.PositiveInfinity;
        perfOut.AppendLine($"{name}: N={g.Vertices.Count}, seq_ms={tSeq}, par_ms={tPar}, speedup={speedup:F2}");
    }

    public static void Main()
    {
        var sb = new StringBuilder();
        var perf = new StringBuilder();
        int pass = 0, fail = 0;
        // Edge: empty graph
        {
            var g = new Graph();
            var (ok, msg) = CheckCase("empty", g, 42);
            if (ok) pass++; else fail++;
            sb.AppendLine(msg);
        }
        // Single vertex
        {
            var g = MakeLine(1);
            var (ok, msg) = CheckCase("single", g, 0);
            if (ok) pass++; else fail++;
            sb.AppendLine(msg);
        }
        // Small line
        {
            var g = MakeLine(10);
            var (ok, msg) = CheckCase("line10", g, 0);
            if (ok) pass++; else fail++;
            sb.AppendLine(msg);
        }
        // Medium grid
        {
            var g = MakeGrid(64, 64); // 4096 vertices
            var (ok, msg) = CheckCase("grid64x64", g, 0);
            if (ok) pass++; else fail++;
            sb.AppendLine(msg);
            PerfCase("grid64x64", g, 0, perf);
        }
        // Larger random
        {
            var g = MakeRandom(8000, 24000, 123);
            var (ok, msg) = CheckCase("rand8k", g, 0);
            if (ok) pass++; else fail++;
            sb.AppendLine(msg);
            PerfCase("rand8k", g, 0, perf);
        }

        sb.AppendLine($"SUMMARY: pass={pass}, fail={fail}");
        File.WriteAllText("run_summary.txt", sb.ToString());
        File.WriteAllText("perf.txt", perf.ToString());

        Console.WriteLine(sb.ToString());
        Console.Error.WriteLine(perf.ToString());

        if (fail > 0) Environment.Exit(1);
    }
}
