using System;
using System.Diagnostics;
using System.Linq;
using GemmBenchmark;

public class RunGemm
{
    static double[][] RandMatrix(int rows, int cols, int seed)
    {
        var rnd = new Random(seed);
        var m = new double[rows][];
        for (int i = 0; i < rows; i++)
        {
            m[i] = new double[cols];
            for (int j = 0; j < cols; j++) m[i][j] = rnd.NextDouble() - 0.5;
        }
        return m;
    }

    static string Hash(double[][] M)
    {
        unchecked
        {
            long h = 1469598103934665603L; // FNV offset basis 64-bit
            foreach (var row in M)
            {
                foreach (var v in row)
                {
                    // Convert double to stable bytes (IEEE 754)
                    ulong bits = (ulong)BitConverter.DoubleToInt64Bits(v);
                    h ^= (long)bits;
                    h *= 1099511628211L; // FNV prime
                }
            }
            return h.ToString();
        }
    }

    static bool Equal(double[][] A, double[][] B)
    {
        if (A.Length != B.Length) return false;
        for (int i = 0; i < A.Length; i++)
        {
            var ar = A[i]; var br = B[i];
            if (ar.Length != br.Length) return false;
            for (int j = 0; j < ar.Length; j++)
            {
                if (ar[j] != br[j]) return false;
            }
        }
        return true;
    }

    static (double[][] A, double[][] B) MakeCase(int m, int k, int n, int seed)
    {
        var A = RandMatrix(m, k, seed);
        var B = RandMatrix(k, n, seed * 31 + 7);
        return (A, B);
    }

    static void CheckCase(int m, int k, int n, int seed, int repeats, int MB=64, int NB=64, int KB=64)
    {
        Console.WriteLine($"Case m={m} k={k} n={n}");
        var (A, B) = MakeCase(m, k, n, seed);

        // Baseline sequential
        var Cseq = Gemm.RunSequential(A, B, alpha: 1.0, C: null, beta: 0.0, MB: MB, NB: NB, KB: KB);
        string hSeq = Hash(Cseq);

        // Parallel once
        var Cpar = Gemm.Run(A, B, alpha: 1.0, C: null, beta: 0.0, MB: MB, NB: NB, KB: KB);
        string hPar = Hash(Cpar);
        bool eq = Equal(Cseq, Cpar);
        Console.WriteLine($"  parity: {eq}  hash seq={hSeq} par={hPar}");

        // Determinism: repeat 3 times
        string[] hashes = new string[repeats];
        for (int r = 0; r < repeats; r++)
        {
            var Cr = Gemm.Run(A, B, alpha: 1.0, C: null, beta: 0.0, MB: MB, NB: NB, KB: KB);
            hashes[r] = Hash(Cr);
        }
        bool det = hashes.All(h => h == hashes[0]);
        Console.WriteLine($"  determinism[{repeats} runs]: {det}  hash={hashes[0]}");

        if (!eq || !det)
        {
            throw new Exception("Correctness/determinism check failed");
        }
    }

    static void PerfCase(int m, int k, int n, int MB=128, int NB=128, int KB=128)
    {
        var (A, B) = MakeCase(m, k, n, 123);
        var sw = new Stopwatch();

        // Warmup
        Gemm.RunSequential(A, B, 1.0, null, 0.0, MB, NB, KB);
        Gemm.Run(A, B, 1.0, null, 0.0, MB, NB, KB);

        sw.Restart();
        var Cs = Gemm.RunSequential(A, B, 1.0, null, 0.0, MB, NB, KB);
        sw.Stop();
        double tSeq = sw.Elapsed.TotalMilliseconds;

        sw.Restart();
        var Cp = Gemm.Run(A, B, 1.0, null, 0.0, MB, NB, KB);
        sw.Stop();
        double tPar = sw.Elapsed.TotalMilliseconds;

        bool ok = Equal(Cs, Cp);
        Console.WriteLine($"PERF m={m} k={k} n={n} -> seq={tSeq:F1} ms par={tPar:F1} ms speedup={tSeq/tPar:F2}x eq={ok}");
    }

    public static int Main(string[] args)
    {
        try
        {
            // Edge cases
            CheckCase(1, 1, 1, 42, 3);
            CheckCase(2, 3, 1, 43, 3);

            // Small / Medium
            CheckCase(16, 16, 16, 11, 3);
            CheckCase(63, 31, 47, 12, 3);
            CheckCase(128, 64, 96, 13, 3);

            // Larger
            CheckCase(256, 256, 256, 21, 3);

            // Perf smoke (adjust size to stay under time limits)
            PerfCase(384, 384, 384);

            return 0;
        }
        catch (Exception ex)
        {
            Console.WriteLine("ERROR: " + ex.Message);
            return 1;
        }
    }
}
