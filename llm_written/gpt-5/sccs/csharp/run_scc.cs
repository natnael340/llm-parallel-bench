using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Linq;

namespace llm_written
{
    public static class Program
    {
        static (List<(int,int)> seq, List<(int,int)> par, TimeSpan tSeq, TimeSpan tPar) RunOnce(int n, int m, int seed)
        {
            var rng = new Random(seed);
            var g1 = new GraphSeq(n);
            var g2 = new Graph(n);
            for (int i = 0; i < m; i++)
            {
                int u = rng.Next(n == 0 ? 1 : n) % Math.Max(1, n);
                int v = rng.Next(n == 0 ? 1 : n) % Math.Max(1, n);
                if (n > 0)
                {
                    g1.AddEdge(u, v);
                    g2.AddEdge(u, v);
                }
            }

            var sw = Stopwatch.StartNew();
            var seq = g1.ReduceEdges();
            sw.Stop();
            var tSeq = sw.Elapsed;

            sw.Restart();
            var par = g2.ReduceEdges();
            sw.Stop();
            var tPar = sw.Elapsed;

            return (seq, par, tSeq, tPar);
        }

        static string HashEdges(List<(int,int)> edges)
        {
            // Deterministic FNV-1a 64-bit over ordered edges
            ulong h = 1469598103934665603UL; // offset basis
            const ulong p = 1099511628211UL; // prime
            foreach (var e in edges.OrderBy(e => e.Item1).ThenBy(e => e.Item2))
            {
                unchecked
                {
                    h ^= (ulong)e.Item1;
                    h *= p;
                    h ^= (ulong)e.Item2;
                    h *= p;
                }
            }
            return h.ToString();
        }

        static int CompareEdgeSets(List<(int,int)> a, List<(int,int)> b)
        {
            var sa = a.OrderBy(e => e.Item1).ThenBy(e => e.Item2).ToArray();
            var sb = b.OrderBy(e => e.Item1).ThenBy(e => e.Item2).ToArray();
            if (sa.Length != sb.Length) return sa.Length - sb.Length;
            for (int i = 0; i < sa.Length; i++)
            {
                if (sa[i].Item1 != sb[i].Item1) return sa[i].Item1 - sb[i].Item1;
                if (sa[i].Item2 != sb[i].Item2) return sa[i].Item2 - sb[i].Item2;
            }
            return 0;
        }

        public static int Main(string[] args)
        {
            var evidenceDir = System.IO.Path.Combine("evidence");
            System.IO.Directory.CreateDirectory(evidenceDir);
            var summaryPath = System.IO.Path.Combine(evidenceDir, "run_summary.txt");
            var perfPath = System.IO.Path.Combine(evidenceDir, "perf.txt");

            bool allOk = true;
            using var summary = new System.IO.StreamWriter(summaryPath);
            using var perf = new System.IO.StreamWriter(perfPath);

            // Edge and small cases
            var sizes = new (int n, int m)[] { (0,0), (1,0), (2,1), (5,6), (50,120) };
            int seedBase = 42;
            foreach (var s in sizes)
            {
                var (seq, par, tSeq, tPar) = RunOnce(s.n, s.m, seedBase++);
                int cmp = CompareEdgeSets(seq, par);
                bool ok = (cmp == 0);
                allOk &= ok;
                summary.WriteLine($"N={s.n},M={s.m} parity={(ok?"OK":"FAIL")} seqEdges={seq.Count} parEdges={par.Count}");
            }

            // Medium / Large and determinism check (run parallel twice)
            var big = (n: 2000, m: 8000);
            var (seqB, parB1, tSeqB, tParB1) = RunOnce(big.n, big.m, 777);
            var (_, parB2, _, tParB2) = RunOnce(big.n, big.m, 777); // same seed to build same graph

            int cmpB = CompareEdgeSets(seqB, parB1);
            bool okB = (cmpB == 0);
            allOk &= okB;

            string h1 = HashEdges(parB1);
            string h2 = HashEdges(parB2);
            bool det = (h1 == h2);
            allOk &= det;

            summary.WriteLine($"BIG parity={(okB?"OK":"FAIL")} det={(det?"OK":"FAIL")} hash1={h1} hash2={h2}");

            // Perf gate for N>=1000
            if (big.n >= 1000)
            {
                double speedup = tSeqB.TotalMilliseconds / Math.Max(1e-9, tParB1.TotalMilliseconds);
                perf.WriteLine($"N={big.n},M={big.m} t_seq_ms={tSeqB.TotalMilliseconds:F3} t_par_ms={tParB1.TotalMilliseconds:F3} speedup={speedup:F2} cores={Environment.ProcessorCount}");
            }

            Console.WriteLine(System.IO.File.ReadAllText(summaryPath));
            Console.WriteLine(System.IO.File.ReadAllText(perfPath));

            return allOk ? 0 : 1;
        }
    }
}
