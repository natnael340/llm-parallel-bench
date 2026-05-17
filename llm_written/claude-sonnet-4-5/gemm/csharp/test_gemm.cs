using System.Security.Cryptography;
using System.Text;
using System.Diagnostics;

namespace GemmBenchmark;

public class TestGemm
{
    private static Random rng = new Random(42);

    public static double[][] RandomMatrix(int rows, int cols, double min = -1.0, double max = 1.0)
    {
        var result = new double[rows][];
        for (int i = 0; i < rows; i++)
        {
            result[i] = new double[cols];
            for (int j = 0; j < cols; j++)
            {
                result[i][j] = min + (max - min) * rng.NextDouble();
            }
        }
        return result;
    }

    public static double[][] IdentityMatrix(int n)
    {
        var result = Gemm.Zeros(n, n);
        for (int i = 0; i < n; i++)
        {
            result[i][i] = 1.0;
        }
        return result;
    }

    public static string ComputeHash(double[][] matrix)
    {
        using (var sha256 = SHA256.Create())
        {
            var bytes = new List<byte>();
            foreach (var row in matrix)
            {
                foreach (var val in row)
                {
                    bytes.AddRange(BitConverter.GetBytes(val));
                }
            }
            var hash = sha256.ComputeHash(bytes.ToArray());
            return BitConverter.ToString(hash).Replace("-", "").ToLower();
        }
    }

    public static bool MatricesEqual(double[][] A, double[][] B, double tolerance = 0.0)
    {
        if (A.Length != B.Length) return false;
        for (int i = 0; i < A.Length; i++)
        {
            if (A[i].Length != B[i].Length) return false;
            for (int j = 0; j < A[i].Length; j++)
            {
                if (tolerance == 0.0)
                {
                    if (A[i][j] != B[i][j]) return false;
                }
                else
                {
                    if (Math.Abs(A[i][j] - B[i][j]) > tolerance) return false;
                }
            }
        }
        return true;
    }

    public static double[][] DeepCopy(double[][] matrix)
    {
        var result = new double[matrix.Length][];
        for (int i = 0; i < matrix.Length; i++)
        {
            result[i] = new double[matrix[i].Length];
            Array.Copy(matrix[i], result[i], matrix[i].Length);
        }
        return result;
    }

    public class TestCase
    {
        public string Name { get; set; } = "";
        public double[][] A { get; set; } = null!;
        public double[][] B { get; set; } = null!;
        public double Alpha { get; set; } = 1.0;
        public double Beta { get; set; } = 0.0;
        public double[][]? C { get; set; } = null;
    }

    public static List<TestCase> GetTestCases()
    {
        var cases = new List<TestCase>();

        // Edge case: 1x1
        cases.Add(new TestCase
        {
            Name = "1x1",
            A = new double[][] { new double[] { 2.0 } },
            B = new double[][] { new double[] { 3.0 } },
            Alpha = 1.0,
            Beta = 0.0
        });

        // Edge case: 2x2
        cases.Add(new TestCase
        {
            Name = "2x2",
            A = new double[][] { new double[] { 1, 2 }, new double[] { 3, 4 } },
            B = new double[][] { new double[] { 5, 6 }, new double[] { 7, 8 } },
            Alpha = 1.0,
            Beta = 0.0
        });

        // Small: 10x10
        cases.Add(new TestCase
        {
            Name = "10x10",
            A = RandomMatrix(10, 10),
            B = RandomMatrix(10, 10),
            Alpha = 1.0,
            Beta = 0.0
        });

        // Small: non-square 15x20x25
        cases.Add(new TestCase
        {
            Name = "15x20x25",
            A = RandomMatrix(15, 20),
            B = RandomMatrix(20, 25),
            Alpha = 1.0,
            Beta = 0.0
        });

        // Medium: 100x100
        cases.Add(new TestCase
        {
            Name = "100x100",
            A = RandomMatrix(100, 100),
            B = RandomMatrix(100, 100),
            Alpha = 1.0,
            Beta = 0.0
        });

        // Medium: 128x256x128 (tests tiling boundaries)
        cases.Add(new TestCase
        {
            Name = "128x256x128",
            A = RandomMatrix(128, 256),
            B = RandomMatrix(256, 128),
            Alpha = 1.0,
            Beta = 0.0
        });

        // Large: 512x512
        cases.Add(new TestCase
        {
            Name = "512x512",
            A = RandomMatrix(512, 512),
            B = RandomMatrix(512, 512),
            Alpha = 1.0,
            Beta = 0.0
        });

        // Test with alpha and beta
        cases.Add(new TestCase
        {
            Name = "100x100_alpha_beta",
            A = RandomMatrix(100, 100),
            B = RandomMatrix(100, 100),
            Alpha = 2.5,
            Beta = 0.5,
            C = RandomMatrix(100, 100)
        });

        // Test with identity matrix
        cases.Add(new TestCase
        {
            Name = "identity_50x50",
            A = RandomMatrix(50, 50),
            B = IdentityMatrix(50),
            Alpha = 1.0,
            Beta = 0.0
        });

        return cases;
    }

    public static void RunCorrectnessTests(StreamWriter log)
    {
        var cases = GetTestCases();
        int passed = 0;
        int failed = 0;

        log.WriteLine("=== CORRECTNESS TESTS ===");
        log.WriteLine();

        foreach (var testCase in cases)
        {
            try
            {
                // Run sequential
                double[][] seqC = testCase.C != null ? DeepCopy(testCase.C) : null!;
                var seqResult = Gemm.Run(testCase.A, testCase.B, testCase.Alpha, seqC, testCase.Beta);

                // Run parallel
                double[][] parC = testCase.C != null ? DeepCopy(testCase.C) : null!;
                var parResult = GemmParallel.Run(testCase.A, testCase.B, testCase.Alpha, parC, testCase.Beta);

                // Compare
                bool match = MatricesEqual(seqResult, parResult, 0.0);

                if (match)
                {
                    log.WriteLine($"✓ {testCase.Name}: PASS");
                    passed++;
                }
                else
                {
                    log.WriteLine($"✗ {testCase.Name}: FAIL (outputs differ)");
                    failed++;
                }
            }
            catch (Exception ex)
            {
                log.WriteLine($"✗ {testCase.Name}: FAIL (exception: {ex.Message})");
                failed++;
            }
        }

        log.WriteLine();
        log.WriteLine($"Correctness: {passed} passed, {failed} failed");
        log.WriteLine();
    }

    public static void RunDeterminismTests(StreamWriter log)
    {
        log.WriteLine("=== DETERMINISM TESTS ===");
        log.WriteLine();

        var testSizes = new[] { 
            (128, 128, 128),
            (256, 256, 256),
            (512, 512, 512)
        };

        int passed = 0;
        int failed = 0;

        foreach (var (m, k, n) in testSizes)
        {
            var A = RandomMatrix(m, k);
            var B = RandomMatrix(k, n);

            // Run 3 times
            var hashes = new List<string>();
            for (int run = 0; run < 3; run++)
            {
                var result = GemmParallel.Run(A, B);
                var hash = ComputeHash(result);
                hashes.Add(hash);
            }

            // Check all hashes match
            bool allMatch = hashes.All(h => h == hashes[0]);

            if (allMatch)
            {
                log.WriteLine($"✓ {m}x{k}x{n}: DETERMINISTIC");
                log.WriteLine($"  Hash: {hashes[0]}");
                passed++;
            }
            else
            {
                log.WriteLine($"✗ {m}x{k}x{n}: NON-DETERMINISTIC");
                for (int i = 0; i < hashes.Count; i++)
                {
                    log.WriteLine($"  Run {i + 1}: {hashes[i]}");
                }
                failed++;
            }
        }

        log.WriteLine();
        log.WriteLine($"Determinism: {passed} passed, {failed} failed");
        log.WriteLine();
    }

    public static void RunPerformanceTests(StreamWriter log)
    {
        log.WriteLine("=== PERFORMANCE TESTS ===");
        log.WriteLine();

        var testSizes = new[] { 
            (256, 256, 256),
            (512, 512, 512),
            (1024, 1024, 1024)
        };

        foreach (var (m, k, n) in testSizes)
        {
            var A = RandomMatrix(m, k);
            var B = RandomMatrix(k, n);

            // Warmup
            Gemm.Run(A, B);
            GemmParallel.Run(A, B);

            // Sequential timing
            var swSeq = Stopwatch.StartNew();
            var seqResult = Gemm.Run(A, B);
            swSeq.Stop();
            double seqTime = swSeq.Elapsed.TotalSeconds;

            // Parallel timing
            var swPar = Stopwatch.StartNew();
            var parResult = GemmParallel.Run(A, B);
            swPar.Stop();
            double parTime = swPar.Elapsed.TotalSeconds;

            double speedup = seqTime / parTime;
            double efficiency = speedup / Environment.ProcessorCount;

            log.WriteLine($"{m}x{k}x{n}:");
            log.WriteLine($"  Sequential: {seqTime:F3}s");
            log.WriteLine($"  Parallel:   {parTime:F3}s");
            log.WriteLine($"  Speedup:    {speedup:F2}x");
            log.WriteLine($"  Efficiency: {efficiency * 100:F1}% ({Environment.ProcessorCount} cores)");
            log.WriteLine();
        }
    }
}
