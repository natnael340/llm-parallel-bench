using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Text.Json;

/// <summary>
/// Shared benchmark harness for all C# benchmarks. Mirrors tests/bench_utils.py:
/// reps x iters timing with warmup, median/IQR and mean/SD statistics, and the
/// schema-v2 JSON result format.
/// </summary>
public static class Bench
{
    public class Result
    {
        public List<double> ElapsedMs = new();
        public double Median, Iqr, Mean, Sd;
        public int Reps, Iters;
    }

    // --- env helpers: the standard benchmark env contract ---

    private static int EnvInt(string name, int def)
    {
        string? v = Environment.GetEnvironmentVariable(name);
        return int.TryParse(v, out int n) ? n : def;
    }

    public static int Reps(int def) => EnvInt("BENCH_REPS", def);
    public static int Iters(int def) => EnvInt("BENCH_ITERS", def);

    public static string Impl()
    {
        string? v = Environment.GetEnvironmentVariable("IMPL");
        return string.IsNullOrEmpty(v) ? "seq" : v;
    }

    public static string Model()
    {
        string? v = Environment.GetEnvironmentVariable("MODEL");
        return string.IsNullOrEmpty(v) ? "baseline" : v;
    }

    public static string Out() =>
        Environment.GetEnvironmentVariable("BENCH_OUT") ?? "";

    // --- statistics ---

    public static double MedianOf(List<double> values)
    {
        var s = new List<double>(values);
        s.Sort();
        int n = s.Count;
        return (n % 2 == 0) ? (s[n / 2 - 1] + s[n / 2]) / 2.0 : s[n / 2];
    }

    /// <summary>
    /// Interquartile range using the same definition as Python's
    /// statistics.quantiles(data, n=4) (exclusive, interpolated), so the
    /// dispersion figure is comparable across all six languages and matches
    /// what bench/aggregate.py recomputes. The previous truncated nearest-rank
    /// indexing disagreed with the Python harness on identical samples.
    /// </summary>
    public static double IqrOf(List<double> values)
    {
        var s = new List<double>(values);
        s.Sort();
        int n = s.Count;
        if (n < 2) return 0.0;
        const int nq = 4;
        int m = n + 1;
        var q = new double[3];
        for (int i = 1; i <= 3; i++)
        {
            int j = i * m / nq;
            if (j < 1) j = 1;
            if (j > n - 1) j = n - 1;
            double delta = i * m - j * nq;
            q[i - 1] = (s[j - 1] * (nq - delta) + s[j] * delta) / nq;
        }
        return q[2] - q[0];
    }

    public static double MeanOf(List<double> values)
    {
        double sum = 0;
        foreach (var v in values) sum += v;
        return sum / values.Count;
    }

    public static double SdOf(List<double> values)
    {
        if (values.Count < 2) return 0;
        double m = MeanOf(values);
        double sq = 0;
        foreach (var v in values) sq += (v - m) * (v - m);
        return Math.Sqrt(sq / (values.Count - 1));
    }

    /// <summary>
    /// Runs warmup untimed calls, then reps timed blocks of iters calls each,
    /// recording per-block mean time per call in milliseconds.
    /// </summary>
    public static Result Run(Action fn, int reps, int iters, int warmup)
    {
        for (int i = 0; i < warmup; i++) fn();

        var perRunMs = new List<double>(reps);
        for (int r = 0; r < reps; r++)
        {
            var sw = Stopwatch.StartNew();
            for (int k = 0; k < iters; k++) fn();
            sw.Stop();
            perRunMs.Add(sw.Elapsed.TotalMilliseconds / iters);
        }

        return new Result
        {
            ElapsedMs = perRunMs,
            Median = MedianOf(perRunMs),
            Iqr = IqrOf(perRunMs),
            Mean = MeanOf(perRunMs),
            Sd = SdOf(perRunMs),
            Reps = reps,
            Iters = iters,
        };
    }

    public static string Format(string label, Result r) =>
        $"{label} | mean {r.Mean:F2} ms/run ± {r.Sd:F2} SD | median {r.Median:F2} ms/run ± {r.Iqr:F2} IQR (n={r.Reps})";

    /// <summary>
    /// Writes the schema-v2 JSON result to path (no-op if empty).
    /// </summary>
    public static void WriteResult(string path, Result r, string algo, string impl,
                                   Dictionary<string, object>? params_ = null)
    {
        if (string.IsNullOrEmpty(path)) return;
        var payload = new Dictionary<string, object>
        {
            ["schema_version"] = 2,
            ["algo"] = algo,
            ["lang"] = "csharp",
            ["impl"] = impl,
            ["model"] = Model(),
            ["elapsed_ms"] = r.ElapsedMs,
            ["mean"] = r.Mean,
            ["sd"] = r.Sd,
            ["median"] = r.Median,
            ["iqr"] = r.Iqr,
            ["reps"] = r.Reps,
            ["iters_per_rep"] = r.Iters,
            ["params"] = params_ ?? new Dictionary<string, object>(),
            ["timestamp"] = DateTime.UtcNow.ToString("o"),
        };
        try
        {
            string json = JsonSerializer.Serialize(payload, new JsonSerializerOptions { WriteIndented = true });
            File.WriteAllText(path, json);
        }
        catch (Exception ex)
        {
            Console.Error.WriteLine($"Error writing result JSON to {path}: {ex.Message}");
        }
    }
}
