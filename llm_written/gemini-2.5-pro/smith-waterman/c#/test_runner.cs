using System;
using System.Diagnostics;
using System.Security.Cryptography;
using System.Text;
using SmithWatermanAlignment;

public class TestRunner
{
    private const int MatchScore = 2;
    private const int MismatchScore = -1;
    private const int GapScore = -1;

    public static void Main(string[] args)
    {
        bool allTestsPassed = true;

        allTestsPassed &= RunTest("Empty", "", "", true);
        allTestsPassed &= RunTest("Identical", "AGTC", "AGTC", true);
        allTestsPassed &= RunTest("Simple Mismatch", "AGTC", "AGGC", true);
        allTestsPassed &= RunTest("Simple Gap", "AGTC", "AGC", true);
        allTestsPassed &= RunTest("Longer Sequences", "GATTACA", "GCATGCU", true);
        allTestsPassed &= RunTest("No Alignment", "AAAA", "TTTT", true);
        allTestsPassed &= RunTest("Medium", GenerateRandomString(150), GenerateRandomString(160), true);
        
        // Performance test on larger input, only if not in CI
        if (Environment.GetEnvironmentVariable("CI") == null)
        {
             allTestsPassed &= RunTest("Large (Perf)", GenerateRandomString(1000), GenerateRandomString(1100), false);
        }

        Console.WriteLine(allTestsPassed ? "✅ All tests passed!" : "❌ Some tests failed!");
        Environment.Exit(allTestsPassed ? 0 : 1);
    }

    private static bool RunTest(string testName, string query, string reference, bool checkDeterminism)
    {
        Console.WriteLine($"--- Running Test: {testName} ---");
        var swSequential = new SmithWaterman(MatchScore, MismatchScore, GapScore);
        var swParallel = new SmithWatermanParallel(MatchScore, MismatchScore, GapScore);

        // --- Correctness Check ---
        var stopwatch = Stopwatch.StartNew();
        var (seqA1, seqB1, score1, pct1) = swSequential.FindAlignment(query, reference);
        stopwatch.Stop();
        double seqTime = stopwatch.Elapsed.TotalMilliseconds;

        stopwatch.Restart();
        var (parA1, parB1, pScore1, pPct1) = swParallel.FindAlignment(query, reference);
        stopwatch.Stop();
        double parTime = stopwatch.Elapsed.TotalMilliseconds;

        bool isCorrect = (seqA1 == parA1) && (seqB1 == parB1) && (score1 == pScore1) && Math.Abs(pct1 - pPct1) < 0.001;
        Console.WriteLine($"Correctness: {(isCorrect ? "PASS" : "FAIL")}");
        if (!isCorrect)
        {
            Console.WriteLine($"  Sequential: ({seqA1}, {seqB1}, {score1}, {pct1:F2})");
            Console.WriteLine($"  Parallel:   ({parA1}, {parB1}, {pScore1}, {pPct1:F2})");
            return false;
        }

        // --- Determinism Check ---
        if (checkDeterminism)
        {
            var (parA2, parB2, pScore2, pPct2) = swParallel.FindAlignment(query, reference);
            bool isDeterministic = (parA1 == parA2) && (parB1 == parB2) && (pScore1 == pScore2) && Math.Abs(pPct1 - pPct2) < 0.001;
            Console.WriteLine($"Determinism: {(isDeterministic ? "PASS" : "FAIL")}");
            if (!isDeterministic)
            {
                Console.WriteLine($"  Run 1: ({parA1}, {parB1}, {pScore1}, {pPct1:F2})");
                Console.WriteLine($"  Run 2: ({parA2}, {parB2}, {pScore2}, {pPct2:F2})");
                return false;
            }
        }
        
        // --- Performance Check ---
        Console.WriteLine($"  Sequential Time: {seqTime:F2} ms");
        Console.WriteLine($"  Parallel Time:   {parTime:F2} ms");
        if (seqTime > 0 && parTime > 0)
        {
            double speedup = seqTime / parTime;
            Console.WriteLine($"  Speedup:         {speedup:F2}x");
            if (testName.Contains("Perf") && speedup < 1.3)
            {
                 Console.WriteLine("  NOTE: Speedup is less than 1.3x for the large test case.");
            }
        }
        
        return true;
    }

    private static string GenerateRandomString(int length)
    {
        const string chars = "ACGT";
        var random = new Random();
        var builder = new StringBuilder(length);
        for (int i = 0; i < length; i++)
        {
            builder.Append(chars[random.Next(chars.Length)]);
        }
        return builder.ToString();
    }
}
