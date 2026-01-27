using System;
using System.Diagnostics;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Security.Cryptography;
using System.Text;

namespace GemmBenchmark
{
    public static class Utils
    {
        public static double[][] MakeRandom(int rows, int cols, Random rng)
        {
            var a = new double[rows][];
            for (int i = 0; i < rows; i++)
            {
                a[i] = new double[cols];
                for (int j = 0; j < cols; j++)
                {
                    // symmetric range to reduce bias
                    a[i][j] = (rng.NextDouble() - 0.5) * 2.0;
                }
            }
            return a;
        }

        public static double[][] Clone(double[][] m)
        {
            var r = new double[m.Length][];
            for (int i = 0; i < m.Length; i++)
            {
                r[i] = (double[])m[i].Clone();
            }
            return r;
        }

        public static string HashMatrix(double[][] m)
        {
            using var sha = SHA256.Create();
            foreach (var row in m)
            {
                var bytes = new byte[row.Length * sizeof(double)];
                Buffer.BlockCopy(row, 0, bytes, 0, bytes.Length);
                sha.TransformBlock(bytes, 0, bytes.Length, null, 0);
            }
            sha.TransformFinalBlock(Array.Empty<byte>(), 0, 0);
            return BitConverter.ToString(sha.Hash!).Replace("-", "");
        }

        public static bool Equal(double[][] a, double[][] b)
        {
            if (a.Length != b.Length) return false;
            for (int i = 0; i < a.Length; i++)
            {
                if (a[i].Length != b[i].Length) return false;
                for (int j = 0; j < a[i].Length; j++)
                {
                    if (a[i][j] != b[i][j]) return false; // strict equality expected
                }
            }
            return true;
        }
    }

    public class Runner
    {
        static (double[][] seq, double tSeqMs) RunSeq(double[][] A, double[][] B, double alpha, double[][]? C, double beta, int MB, int NB, int KB)
        {
            var Cseq = C == null ? null : Utils.Clone(C);
            var sw = Stopwatch.StartNew();
            var outSeq = GemmSeq.Run(A, B, alpha, Cseq, beta, MB, NB, KB);
            sw.Stop();
            return (outSeq, sw.Elapsed.TotalMilliseconds);
        }

        static (double[][] par, double tParMs, string hash) RunPar(double[][] A, double[][] B, double alpha, double[][]? C, double beta, int MB, int NB, int KB)
        {
            var Cpar = C == null ? null : Utils.Clone(C);
            var sw = Stopwatch.StartNew();
            var outPar = Gemm.Run(A, B, alpha, Cpar, beta, MB, NB, KB);
            sw.Stop();
            return (outPar, sw.Elapsed.TotalMilliseconds, Utils.HashMatrix(outPar));
        }

        static string CaseName(int m, int k, int n) => $"{m}x{k}x{n}";

        public static int Main(string[] args)
        {
            var summary = new StringBuilder();
            var perf = new StringBuilder();
            var rng = new Random(12345);
            CultureInfo.CurrentCulture = CultureInfo.InvariantCulture;

            // Test cases: edge, small, medium, large
            var cases = new (int m, int k, int n)[]
            {
                (1,1,1),
                (1,5,3),
                (4,3,1),
                (16,16,16),
                (64,64,64),
                (96,64,48),
                (128,128,128),
                (256,256,256)
            };

            bool allOk = true;
            foreach (var (m, k, n) in cases)
            {
                var A = Utils.MakeRandom(m, k, rng);
                var B = Utils.MakeRandom(k, n, rng);
                var C0 = Utils.MakeRandom(m, n, rng);
                double alpha = 1.0;
                double beta = 0.6; // exercise beta path
                int MB = 64, NB = 64, KB = 64;

                var (seq, tSeq) = RunSeq(A, B, alpha, Utils.Clone(C0), beta, MB, NB, KB);
                var (par, tPar, h1) = RunPar(A, B, alpha, Utils.Clone(C0), beta, MB, NB, KB);
                var (_, _, h2) = RunPar(A, B, alpha, Utils.Clone(C0), beta, MB, NB, KB);

                bool eq = Utils.Equal(seq, par);
                bool det = h1 == h2;

                summary.AppendLine($"Case {CaseName(m,k,n)}: equal={eq}, deterministic={det}");
                if (!eq || !det) allOk = false;

                // perf on larger cases only
                long work = (long)m * n * k;
                if (work >= 16_000_000) // N0 threshold for perf reporting
                {
                    double speedup = tSeq / tPar;
                    perf.AppendLine($"{CaseName(m,k,n)} seq_ms={tSeq:F2} par_ms={tPar:F2} speedup={speedup:F2}");
                }
            }

            // Alpha zero path test
            {
                int m = 32, k = 32, n = 32;
                var A = Utils.MakeRandom(m, k, rng);
                var B = Utils.MakeRandom(k, n, rng);
                var C0 = Utils.MakeRandom(m, n, rng);
                double alpha = 0.0;
                double beta = 0.5;
                var (seq, _) = RunSeq(A, B, alpha, Utils.Clone(C0), beta, 64, 64, 64);
                var (par, _, h1) = RunPar(A, B, alpha, Utils.Clone(C0), beta, 64, 64, 64);
                var (_, _, h2) = RunPar(A, B, alpha, Utils.Clone(C0), beta, 64, 64, 64);
                bool eq = Utils.Equal(seq, par);
                bool det = h1 == h2;
                summary.AppendLine($"Case alpha0 32x32x32: equal={eq}, deterministic={det}");
                if (!eq || !det) allOk = false;
            }

            File.WriteAllText("run_summary.txt", summary.ToString());
            File.WriteAllText("perf.txt", perf.ToString());

            Console.WriteLine(summary.ToString());
            Console.WriteLine("Perf (if any):\n" + perf.ToString());

            return allOk ? 0 : 1;
        }
    }
}
