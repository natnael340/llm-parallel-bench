// GemmSweepBenchmark.cs - Staged GEMM configuration sweep
// Equivalent to tests/go/test_go_pack.go

using System.Diagnostics;

namespace GemmBenchmark;

public static class GemmSweepBenchmark
{
    public static void Main(string[] args)
    {
        // Quick dry-run; raise to 512/1024 for real tests.
        int m = 256, n = 256, k = 256;

        int[] kbList = { 16, 32, 48, 64, 96, 128 };
        int[] coarse = { 8, 16, 32, 48, 64 };
        int stepRefine = 8;

        int topKB = 2;
        int topMBNB = 5;
        int repeats = 3;
        double minWall = 5.0; // seconds
        string csvPath = "gemm_sweep_staged_256_csharp.csv";

        int seedA = 1;
        int seedB = 2;

        StagedSweep(m, n, k, kbList, coarse, stepRefine, topKB, topMBNB, repeats, minWall, csvPath, seedA, seedB);
    }

    private static double[][] MakeRandomMatrix(int rows, int cols, int seed)
    {
        var rng = new Random(seed);
        var matrix = new double[rows][];
        for (int i = 0; i < rows; i++)
        {
            matrix[i] = new double[cols];
            for (int j = 0; j < cols; j++)
            {
                matrix[i][j] = rng.NextDouble() * 2.0 - 1.0; // [-1, 1]
            }
        }
        return matrix;
    }

    private static double[][] Zeros(int rows, int cols)
    {
        var matrix = new double[rows][];
        for (int i = 0; i < rows; i++)
        {
            matrix[i] = new double[cols];
        }
        return matrix;
    }

    private static double TimeAvgPerRun(Action fn, double minWallSeconds, int warmup)
    {
        for (int i = 0; i < warmup; i++)
        {
            fn();
        }

        var sw = Stopwatch.StartNew();
        double total = 0.0;
        int runs = 0;

        while (total < minWallSeconds)
        {
            fn();
            runs++;
            total = sw.Elapsed.TotalSeconds;
        }

        if (runs == 0) return 0.0;
        return total / runs;
    }

    private static double GFlops(int m, int n, int k, double seconds)
    {
        if (seconds <= 0) return 0;
        return (2.0 * m * n * k) / (seconds * 1e9);
    }

    private static double Mean(List<double> xs)
    {
        if (xs.Count == 0) return 0;
        return xs.Sum() / xs.Count;
    }

    private static double PStdev(List<double> xs)
    {
        if (xs.Count == 0) return 0;
        double m = Mean(xs);
        double sum = xs.Sum(x => (x - m) * (x - m));
        return Math.Sqrt(sum / xs.Count);
    }

    private record Row(int Stage, int MB, int NB, int KB, double AvgMs, double SdMs, double GFlops);

    private static (double avgMs, double sdMs, double gflops) EvalConfig(
        double[][] A, double[][] B, int MB, int NB, int KB, int repeats, double minWall)
    {
        int m = A.Length;
        int k = A[0].Length;
        int n = B[0].Length;

        var samples = new List<double>(repeats);
        for (int i = 0; i < repeats; i++)
        {
            double avgSec = TimeAvgPerRun(() =>
            {
                var C = Zeros(m, n);
                Gemm.Run(A, B, 1.0, C, 0.0, MB, NB, KB);
            }, minWall, 1);
            samples.Add(avgSec);
        }

        double avgSec2 = Mean(samples);
        double sdSec = PStdev(samples);
        return (avgSec2 * 1000.0, sdSec * 1000.0, GFlops(m, n, k, avgSec2));
    }

    private static int Clamp(int v, int lo, int hi)
    {
        if (v < lo) return lo;
        if (v > hi) return hi;
        return v;
    }

    private static int FloorToMultipleOf(int v, int step)
    {
        if (step <= 0) return v;
        return (v / step) * step;
    }

    private static List<Row> StagedSweep(
        int m, int n, int k,
        int[] kbList,
        int[] coarse,
        int stepRefine,
        int topKB,
        int topMBNB,
        int repeats,
        double minWall,
        string csvPath,
        int seedA, int seedB)
    {
        var A = MakeRandomMatrix(m, k, seedA);
        var B = MakeRandomMatrix(k, n, seedB);

        var rows = new List<Row>(1024);

        // ----- Stage 1: scan KB with MB=NB=32 -----
        var kbScores = new List<(double G, int K)>(kbList.Length);

        foreach (int KB in kbList)
        {
            var (avgMs, sdMs, flops) = EvalConfig(A, B, 32, 32, KB, repeats, minWall);
            rows.Add(new Row(1, 32, 32, KB, avgMs, sdMs, flops));
            kbScores.Add((flops, KB));
        }

        kbScores = kbScores.OrderByDescending(x => x.G).ToList();
        if (topKB > kbScores.Count) topKB = kbScores.Count;
        var chosenKB = kbScores.Take(topKB).Select(x => x.K).ToList();

        // ----- Stage 2: coarse MB/NB for each chosen KB -----
        var mbnbCandidates = new HashSet<(int MB, int NB, int KB)>();

        foreach (int KB in chosenKB)
        {
            var cands = new List<(double G, int MB, int NB)>();
            foreach (int MB in coarse)
            {
                foreach (int NB in coarse)
                {
                    var (avgMs, sdMs, flops) = EvalConfig(A, B, MB, NB, KB, repeats, minWall);
                    rows.Add(new Row(2, MB, NB, KB, avgMs, sdMs, flops));
                    cands.Add((flops, MB, NB));
                }
            }

            cands = cands.OrderByDescending(x => x.G).ToList();
            int limit = Math.Min(topMBNB, cands.Count);
            for (int i = 0; i < limit; i++)
            {
                mbnbCandidates.Add((cands[i].MB, cands[i].NB, KB));
            }
        }

        // ----- Stage 3: local refinement around each (MB,NB,KB) -----
        var refined = new HashSet<(int MB, int NB, int KB)>();

        foreach (var (MB, NB, KB) in mbnbCandidates)
        {
            foreach (int dmb in new[] { -stepRefine, 0, stepRefine })
            {
                foreach (int dnb in new[] { -stepRefine, 0, stepRefine })
                {
                    int mb2 = Clamp(MB + dmb, 4, m);
                    int nb2 = Clamp(NB + dnb, 4, n);
                    mb2 = FloorToMultipleOf(mb2, 4);
                    nb2 = FloorToMultipleOf(nb2, 4);
                    if (mb2 <= 0 || nb2 <= 0) continue;
                    refined.Add((mb2, nb2, KB));
                }
            }
        }

        var keys = refined.OrderBy(x => x.KB).ThenBy(x => x.MB).ThenBy(x => x.NB).ToList();
        foreach (var (MB, NB, KB) in keys)
        {
            var (avgMs, sdMs, flops) = EvalConfig(A, B, MB, NB, KB, repeats, minWall);
            rows.Add(new Row(3, MB, NB, KB, avgMs, sdMs, flops));
        }

        // ----- Save CSV -----
        if (!string.IsNullOrEmpty(csvPath))
        {
            try
            {
                using var writer = new StreamWriter(csvPath);
                writer.WriteLine("stage,MB,NB,KB,avg_ms,sd_ms,gflops");
                foreach (var r in rows)
                {
                    writer.WriteLine($"{r.Stage},{r.MB},{r.NB},{r.KB},{r.AvgMs:F6},{r.SdMs:F6},{r.GFlops:F6}");
                }
                Console.WriteLine($"Results saved to {csvPath}");
            }
            catch (Exception e)
            {
                Console.WriteLine($"Failed to create CSV: {e.Message}");
            }
        }

        // ----- Top 10 overall -----
        var rowsCopy = rows.OrderByDescending(r => r.GFlops).ToList();
        int top = Math.Min(10, rowsCopy.Count);

        Console.WriteLine("Top 10 configs:");
        for (int i = 0; i < top; i++)
        {
            var r = rowsCopy[i];
            Console.WriteLine($"stage{r.Stage} MB/NB/KB={r.MB}/{r.NB}/{r.KB}  {r.AvgMs:F2} ms  ~{r.GFlops:F2} GFLOP/s  (±{r.SdMs:F2} ms)");
        }

        return rows;
    }
}
