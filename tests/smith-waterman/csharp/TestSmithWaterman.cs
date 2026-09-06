using System;
using System.IO;

// Plain benchmark runner: correctness via the shared FindAlignment entry
// (uniform across all impls) + large-file check + perf. The implementation
// under test is provided by the staged adapter class BenchImpl
// (see bench/manifests/smith-waterman/csharp.json).
public static class TestSmithWaterman
{
    private static int passed = 0;
    private static int failed = 0;
    private const double EPS = 1e-6;

    public static int Main(string[] args)
    {
        TestCase("test_perfect_match", "ACGT", "ACGT", "ACGT", "ACGT", 8, 100.0);
        TestCase("test_no_match", "AAAA", "TTTT", "", "", 0, 0.0);
        TestCase("test_partial_match", "ACGTACGT", "TACGTGCA", "TACGT", "TACGT", 10, 100.0);
        TestCase("test_gap_in_query", "ACGT", "ACAGT", "AC-GT", "ACAGT", 7, 80.0);
        TestCase("test_gap_in_reference", "ACAGT", "ACGT", "ACAGT", "AC-GT", 7, 80.0);
        TestCase("test_single_char_match", "A", "A", "A", "A", 2, 100.0);

        string[]? input = ReadSWInput();
        if (input != null)
        {
            var impl = new BenchImpl(2, -1, -1);
            var (a, b, score, identity) = impl.FindAlignment(input[0], input[1]);
            int expScore = int.Parse(input[2].Trim());
            double expIdentity = double.Parse(input[3].Trim());
            bool ok = a.Length == b.Length && score == expScore
                      && Math.Abs(identity - expIdentity) <= EPS;
            Report("test_large_sequences_from_file", ok);
        }

        Console.WriteLine($"{passed} passed, {failed} failed");
        if (failed > 0)
        {
            Console.WriteLine($"{failed} test(s) failed — skipping benchmark");
            return 1;
        }

        if (input == null)
        {
            Console.WriteLine("SW_INPUT not set — skipping benchmark");
            return 0;
        }

        PerformanceSpeed(input[0], input[1]);
        return 0;
    }

    private static void TestCase(string name, string query, string reference,
                                 string expA, string expB, int expScore, double expIdentity)
    {
        var impl = new BenchImpl(2, -1, -1);
        var (a, b, score, identity) = impl.FindAlignment(query, reference);
        bool ok = a == expA && b == expB && score == expScore
                  && Math.Abs(identity - expIdentity) <= EPS;
        if (!ok)
            Console.WriteLine($"  got: a={a} b={b} score={score} identity={identity}");
        Report(name, ok);
    }

    private static void Report(string name, bool ok)
    {
        Console.WriteLine(name + (ok ? " passed" : " failed"));
        if (ok) passed++;
        else failed++;
    }

    private static string[]? ReadSWInput()
    {
        string? path = Environment.GetEnvironmentVariable("SW_INPUT");
        if (string.IsNullOrEmpty(path) || !File.Exists(path)) return null;
        var lines = File.ReadAllLines(path);
        if (lines.Length < 4) return null;
        return new[] { lines[0].Trim(), lines[1].Trim(), lines[2], lines[3] };
    }

    private static void PerformanceSpeed(string query, string reference)
    {
        var impl = new BenchImpl(2, -1, -1);
        int reps = Bench.Reps(5);
        int iters = Bench.Iters(1);

        var r = Bench.Run(() => impl.FindAlignment(query, reference), reps, iters, 1);
        Console.WriteLine(Bench.Format("SW large sequences", r));

        var params_ = new System.Collections.Generic.Dictionary<string, object>
        {
            ["query_len"] = query.Length,
            ["reference_len"] = reference.Length,
        };
        Bench.WriteResult(Bench.Out(), r, "smith-waterman", Bench.Impl(), params_);
    }
}
