using System;
using System.Diagnostics;
using System.Linq;
using System.Security.Cryptography;
using System.Text;
using SmithWatermanAlignment;

class TestSmithWaterman
{
    static int exitCode = 0;

    static void Main(string[] args)
    {
        Console.WriteLine("=== Smith-Waterman Differential Test Suite ===\n");

        // Test cases: edge, small, medium, large
        RunTestCase("Edge: Empty strings", "", "", 2, -1, -1);
        RunTestCase("Edge: Single char match", "A", "A", 2, -1, -1);
        RunTestCase("Edge: Single char mismatch", "A", "C", 2, -1, -1);
        RunTestCase("Edge: Query empty", "", "ACGT", 2, -1, -1);
        RunTestCase("Edge: Reference empty", "ACGT", "", 2, -1, -1);

        RunTestCase("Small: Short exact match", "ACGT", "ACGT", 2, -1, -1);
        RunTestCase("Small: With mismatch", "ACGT", "AGGT", 2, -1, -1);
        RunTestCase("Small: With gap", "ACGT", "ACT", 2, -1, -1);
        RunTestCase("Small: No similarity", "AAAA", "CCCC", 2, -1, -1);

        // Medium test case
        string query1 = GenerateRandomDNA(200, 42);
        string ref1 = GenerateRandomDNA(200, 43);
        RunTestCase("Medium: Random 200x200", query1, ref1, 2, -1, -1);

        // Large test case (below threshold - will use sequential)
        string query2 = GenerateRandomDNA(400, 100);
        string ref2 = GenerateRandomDNA(400, 101);
        RunTestCase("Large: Random 400x400", query2, ref2, 2, -1, -1);

        // XLarge test case (above threshold - will use parallel)
        string query3 = GenerateRandomDNA(600, 200);
        string ref3 = GenerateRandomDNA(600, 201);
        RunTestCase("XLarge: Random 600x600", query3, ref3, 2, -1, -1, true);

        // XXLarge for performance measurement
        string query4 = GenerateRandomDNA(1200, 300);
        string ref4 = GenerateRandomDNA(1200, 301);
        RunTestCase("XXLarge: Random 1200x1200", query4, ref4, 2, -1, -1, true);

        Console.WriteLine("\n=== Test Summary ===");
        if (exitCode == 0)
        {
            Console.WriteLine("✓ All tests PASSED");
        }
        else
        {
            Console.WriteLine($"✗ Tests FAILED (exit code: {exitCode})");
        }

        Environment.Exit(exitCode);
    }

    static void RunTestCase(string name, string query, string reference, 
                           int match, int mismatch, int gap, bool measurePerf = false)
    {
        Console.WriteLine($"Test: {name}");
        Console.WriteLine($"  Query length: {query.Length}, Reference length: {reference.Length}");

        // Run sequential baseline
        var seqAlgo = new SmithWatermanSequential(match, mismatch, gap);
        Stopwatch swSeq = Stopwatch.StartNew();
        var seqResult = seqAlgo.FindAlignment(query, reference);
        swSeq.Stop();
        double seqTime = swSeq.Elapsed.TotalMilliseconds;

        // Run parallel version twice for determinism check
        var parAlgo = new SmithWaterman(match, mismatch, gap);
        
        Stopwatch swPar1 = Stopwatch.StartNew();
        var parResult1 = parAlgo.FindAlignment(query, reference);
        swPar1.Stop();
        double parTime1 = swPar1.Elapsed.TotalMilliseconds;

        Stopwatch swPar2 = Stopwatch.StartNew();
        var parResult2 = parAlgo.FindAlignment(query, reference);
        swPar2.Stop();
        double parTime2 = swPar2.Elapsed.TotalMilliseconds;

        // Check correctness (parallel vs sequential)
        bool correctnessPass = CompareResults(seqResult, parResult1, "Sequential", "Parallel-Run1");

        // Check determinism (parallel run1 vs run2)
        bool determinismPass = CompareResults(parResult1, parResult2, "Parallel-Run1", "Parallel-Run2");

        if (correctnessPass && determinismPass)
        {
            Console.WriteLine("  ✓ PASS - Correctness and Determinism verified");
            
            // Show hashes for determinism proof
            string hash1 = ComputeHash($"{parResult1.Item1}|{parResult1.Item2}|{parResult1.Item3}|{parResult1.Item4}");
            string hash2 = ComputeHash($"{parResult2.Item1}|{parResult2.Item2}|{parResult2.Item3}|{parResult2.Item4}");
            Console.WriteLine($"    Parallel-Run1 hash: {hash1}");
            Console.WriteLine($"    Parallel-Run2 hash: {hash2}");
        }
        else
        {
            Console.WriteLine("  ✗ FAIL");
            exitCode = 1;
        }

        if (measurePerf && query.Length >= 500)
        {
            double avgParTime = (parTime1 + parTime2) / 2.0;
            double speedup = seqTime / avgParTime;
            Console.WriteLine($"  Performance: Seq={seqTime:F2}ms, Par={avgParTime:F2}ms, Speedup={speedup:F2}x, Cores={Environment.ProcessorCount}");
        }

        Console.WriteLine();
    }

    static bool CompareResults((string, string, int, double) result1, 
                              (string, string, int, double) result2,
                              string label1, string label2)
    {
        bool match = result1.Item1 == result2.Item1 &&
                     result1.Item2 == result2.Item2 &&
                     result1.Item3 == result2.Item3 &&
                     Math.Abs(result1.Item4 - result2.Item4) < 1e-9;

        if (!match)
        {
            Console.WriteLine($"  ✗ Mismatch between {label1} and {label2}:");
            Console.WriteLine($"    {label1}: AlignedA='{result1.Item1}', AlignedB='{result1.Item2}', Score={result1.Item3}, Identity={result1.Item4:F2}%");
            Console.WriteLine($"    {label2}: AlignedA='{result2.Item1}', AlignedB='{result2.Item2}', Score={result2.Item3}, Identity={result2.Item4:F2}%");
            
            // Compute hashes for easier comparison
            string hash1 = ComputeHash($"{result1.Item1}|{result1.Item2}|{result1.Item3}|{result1.Item4}");
            string hash2 = ComputeHash($"{result2.Item1}|{result2.Item2}|{result2.Item3}|{result2.Item4}");
            Console.WriteLine($"    {label1} hash: {hash1}");
            Console.WriteLine($"    {label2} hash: {hash2}");
        }

        return match;
    }

    static string GenerateRandomDNA(int length, int seed)
    {
        Random rand = new Random(seed);
        char[] bases = { 'A', 'C', 'G', 'T' };
        StringBuilder sb = new StringBuilder(length);
        
        for (int i = 0; i < length; i++)
        {
            sb.Append(bases[rand.Next(bases.Length)]);
        }
        
        return sb.ToString();
    }

    static string ComputeHash(string input)
    {
        using (SHA256 sha256 = SHA256.Create())
        {
            byte[] bytes = sha256.ComputeHash(Encoding.UTF8.GetBytes(input));
            return BitConverter.ToString(bytes).Replace("-", "").Substring(0, 16);
        }
    }
}
