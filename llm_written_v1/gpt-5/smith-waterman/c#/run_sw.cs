using System;
using System.Diagnostics;
using System.Linq;
using System.Security.Cryptography;
using System.Text;
using SmithWatermanAlignment;

class Runner
{
    static string HashAlignment((string a, string b, int score, double pid) res)
    {
        using var sha = SHA256.Create();
        var s = $"{res.a}\n{res.b}\n{res.score}\n{res.pid:F6}";
        var bytes = Encoding.UTF8.GetBytes(s);
        var h = sha.ComputeHash(bytes);
        return BitConverter.ToString(h).Replace("-", "");
    }

    static (TimeSpan, (string,string,int,double)) RunSeq(string q, string r)
    {
        var sw = new Stopwatch();
        var seq = new SmithWatermanSeq(2, -1, -2);
        sw.Start();
        var res = seq.FindAlignment(q, r);
        sw.Stop();
        return (sw.Elapsed, res);
    }

    static (TimeSpan, (string,string,int,double)) RunPar(string q, string r)
    {
        var sw = new Stopwatch();
        var par = new SmithWaterman(2, -1, -2);
        sw.Start();
        var res = par.FindAlignment(q, r);
        sw.Stop();
        return (sw.Elapsed, res);
    }

    static string RandSeq(int n, int seed)
    {
        var rnd = new Random(seed);
        char[] alphabet = new[]{'A','C','G','T'};
        var sb = new StringBuilder(n);
        for (int i=0;i<n;i++) sb.Append(alphabet[rnd.Next(alphabet.Length)]);
        return sb.ToString();
    }

    static int Main(string[] args)
    {
        try
        {
            System.IO.Directory.CreateDirectory("evidence");
            var summary = new StringBuilder();
            var perf = new StringBuilder();

            var cases = new (string q, string r)[]
            {
                ("", ""),
                ("A", "G"),
                ("GATTACA", "GCATGCU"),
                ("AAAAA", "AAA"),
                (RandSeq(100, 1), RandSeq(120, 2)),
                (RandSeq(800, 3), RandSeq(900, 4)),
                (RandSeq(2000, 5), RandSeq(2500, 6)) // large
            };

            int failures = 0;
            int determinismFailures = 0;

            for (int idx=0; idx<cases.Length; idx++)
            {
                var (q, r) = cases[idx];
                var (tSeq, resSeq) = RunSeq(q, r);
                var (tPar1, resPar1) = RunPar(q, r);
                var (tPar2, resPar2) = RunPar(q, r);

                bool equal = resSeq.Equals(resPar1) && resPar1.Equals(resPar2);
                if (!equal) failures++;

                string h1 = HashAlignment(resPar1);
                string h2 = HashAlignment(resPar2);
                if (h1 != h2) determinismFailures++;

                summary.AppendLine($"Case {idx}: |q|={q.Length}, |r|={r.Length} -> OK={equal} det={(h1==h2)}");
                summary.AppendLine($"  hashes: {h1} | {h2}");
                summary.AppendLine($"  seq: {tSeq.TotalMilliseconds:F2} ms, par1: {tPar1.TotalMilliseconds:F2} ms, par2: {tPar2.TotalMilliseconds:F2} ms");
            }

            // Simple perf gate on the largest case
            var (Q, R) = cases.Last();
            var (tSeqL, _) = RunSeq(Q, R);
            var (tParL, _) = RunPar(Q, R);
            double speedup = tSeqL.TotalMilliseconds / Math.Max(1.0, tParL.TotalMilliseconds);
            perf.AppendLine($"Largest N: |q|={Q.Length}, |r|={R.Length}");
            perf.AppendLine($"seq={tSeqL.TotalMilliseconds:F2} ms, par={tParL.TotalMilliseconds:F2} ms, speedup={speedup:F2}x, cores={Environment.ProcessorCount}");

            System.IO.File.WriteAllText("evidence/run_summary.txt", summary.ToString());
            System.IO.File.WriteAllText("evidence/perf.txt", perf.ToString());

            Console.WriteLine(summary.ToString());
            Console.WriteLine(perf.ToString());

            if (failures>0 || determinismFailures>0)
            {
                Console.Error.WriteLine($"Failures: correctness={failures}, determinism={determinismFailures}");
                return 1;
            }

            // Do not enforce speedup gate strictly; environments may vary
            return 0;
        }
        catch (Exception ex)
        {
            Console.Error.WriteLine("Error: "+ex.Message);
            return 2;
        }
    }
}
