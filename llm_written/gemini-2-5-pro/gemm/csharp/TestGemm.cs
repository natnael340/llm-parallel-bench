
using System;
using System.Diagnostics;
using System.Linq;
using System.Security.Cryptography;
using System.Text;

namespace GemmBenchmark
{
    public class TestGemm
    {
        private static Random rng = new Random(42);

        public static double[][] RandomMatrix(int rows, int cols)
        {
            var matrix = new double[rows][];
            for (int i = 0; i < rows; i++)
            {
                matrix[i] = new double[cols];
                for (int j = 0; j < cols; j++)
                {
                    matrix[i][j] = rng.NextDouble();
                }
            }
            return matrix;
        }

        public static string GetMatrixHash(double[][] matrix)
        {
            using (var sha256 = SHA256.Create())
            {
                var stringBuilder = new StringBuilder();
                for (int i = 0; i < matrix.Length; i++)
                {
                    for (int j = 0; j < matrix[i].Length; j++)
                    {
                        stringBuilder.Append(matrix[i][j].ToString("G17"));
                    }
                }
                byte[] bytes = Encoding.UTF8.GetBytes(stringBuilder.ToString());
                byte[] hash = sha256.ComputeHash(bytes);
                return BitConverter.ToString(hash).Replace("-", "").ToLowerInvariant();
            }
        }

        public static bool AreMatricesEqual(double[][] a, double[][] b, double tolerance = 1e-9)
        {
            if (a.Length != b.Length) return false;
            for (int i = 0; i < a.Length; i++)
            {
                if (a[i].Length != b[i].Length) return false;
                for (int j = 0; j < a[i].Length; j++)
                {
                    if (Math.Abs(a[i][j] - b[i][j]) > tolerance)
                    {
                        Console.WriteLine($"Mismatch at [{i}][{j}]: {a[i][j]} vs {b[i][j]}");
                        return false;
                    }
                }
            }
            return true;
        }

        public static void Main(string[] args)
        {
            var testCases = new[]
            {
                new { M = 1, K = 1, N = 1 },
                new { M = 16, K = 16, N = 16 },
                new { M = 63, K = 63, N = 63 },
                new { M = 64, K = 64, N = 64 },
                new { M = 128, K = 128, N = 128 },
                new { M = 256, K = 127, N = 255 },
                new { M = 512, K = 512, N = 512 }
            };

            var summary = new StringBuilder();
            bool allTestsPassed = true;

            foreach (var tc in testCases)
            {
                Console.WriteLine($"--- Testing {tc.M}x{tc.K} * {tc.K}x{tc.N} ---");
                summary.AppendLine($"--- Testing {tc.M}x{tc.K} * {tc.K}x{tc.N} ---");

                var A = RandomMatrix(tc.M, tc.K);
                var B = RandomMatrix(tc.K, tc.N);

                // Correctness Test
                var C_seq = Gemm.Run(A, B);
                var C_par = GemmParallel.Run(A, B);

                if (AreMatricesEqual(C_seq, C_par))
                {
                    Console.WriteLine("Correctness: PASS");
                    summary.AppendLine("Correctness: PASS");
                }
                else
                {
                    Console.WriteLine("Correctness: FAIL");
                    summary.AppendLine("Correctness: FAIL");
                    allTestsPassed = false;
                }

                // Determinism Test
                var hash1 = GetMatrixHash(GemmParallel.Run(A, B));
                var hash2 = GetMatrixHash(GemmParallel.Run(A, B));
                var hash3 = GetMatrixHash(GemmParallel.Run(A, B));

                if (hash1 == hash2 && hash2 == hash3)
                {
                    Console.WriteLine($"Determinism: PASS (hash: {hash1})");
                    summary.AppendLine($"Determinism: PASS (hash1: {hash1}, hash2: {hash2}, hash3: {hash3})");
                }
                else
                {
                    Console.WriteLine($"Determinism: FAIL (hashes: {hash1}, {hash2}, {hash3})");
                    summary.AppendLine($"Determinism: FAIL (hashes: {hash1}, {hash2}, {hash3})");
                    allTestsPassed = false;
                }
                summary.AppendLine();
            }
            
            // Performance Test
            int perf_M = 1024;
            int perf_K = 1024;
            int perf_N = 1024;
            Console.WriteLine($"--- Performance Test {perf_M}x{perf_K} * {perf_K}x{perf_N} ---");
            summary.AppendLine($"--- Performance Test {perf_M}x{perf_K} * {perf_K}x{perf_N} ---");
            var perfA = RandomMatrix(perf_M, perf_K);
            var perfB = RandomMatrix(perf_K, perf_N);

            var stopwatch = new Stopwatch();

            stopwatch.Restart();
            var perf_C_seq = Gemm.Run(perfA, perfB);
            stopwatch.Stop();
            var seq_time = stopwatch.Elapsed.TotalMilliseconds;
            Console.WriteLine($"Sequential time: {seq_time:F2} ms");
            summary.AppendLine($"Sequential time: {seq_time:F2} ms");

            stopwatch.Restart();
            var perf_C_par = GemmParallel.Run(perfA, perfB);
            stopwatch.Stop();
            var par_time = stopwatch.Elapsed.TotalMilliseconds;
            Console.WriteLine($"Parallel time:   {par_time:F2} ms");
            summary.AppendLine($"Parallel time:   {par_time:F2} ms");

            if (!AreMatricesEqual(perf_C_seq, perf_C_par))
            {
                 Console.WriteLine("Performance test correctness: FAIL");
                 summary.AppendLine("Performance test correctness: FAIL");
                 allTestsPassed = false;
            }

            double speedup = seq_time / par_time;
            Console.WriteLine($"Speedup: {speedup:F2}x");
            summary.AppendLine($"Speedup: {speedup:F2}x");
            
            var perfSummary = new StringBuilder();
            perfSummary.AppendLine($"M={perf_M}, K={perf_K}, N={perf_N}");
            perfSummary.AppendLine($"t_seq={seq_time:F2}ms");
            perfSummary.AppendLine($"t_par={par_time:F2}ms");
            perfSummary.AppendLine($"speedup={speedup:F2}x");
            perfSummary.AppendLine($"cores={Environment.ProcessorCount}");
            
            System.IO.File.WriteAllText("perf.txt", perfSummary.ToString());
            System.IO.File.WriteAllText("run_summary.txt", summary.ToString());

            if (!allTestsPassed)
            {
                Console.WriteLine("\nSome tests failed.");
                Environment.Exit(1);
            }
            else
            {
                Console.WriteLine("\nAll tests passed.");
            }
        }
    }
}
