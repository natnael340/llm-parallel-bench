using System;
using System.IO;

namespace GemmBenchmark;

class Program
{
    static int Main(string[] args)
    {
        bool runCorrectness = true;
        bool runDeterminism = true;
        bool runPerformance = true;

        // Parse command line arguments
        if (args.Length > 0)
        {
            runCorrectness = false;
            runDeterminism = false;
            runPerformance = false;

            foreach (var arg in args)
            {
                if (arg == "--test" && args.Length > 1)
                {
                    continue;
                }
                if (arg == "correctness")
                {
                    runCorrectness = true;
                }
                else if (arg == "determinism")
                {
                    runDeterminism = true;
                }
                else if (arg == "performance")
                {
                    runPerformance = true;
                }
                else if (arg == "all")
                {
                    runCorrectness = true;
                    runDeterminism = true;
                    runPerformance = true;
                }
            }
        }

        try
        {
            using (var summaryWriter = new StreamWriter("run_summary.txt"))
            using (var perfWriter = new StreamWriter("perf.txt"))
            {
                var consoleOut = Console.Out;
                var multiWriter = new MultiTextWriter(consoleOut, summaryWriter);

                Console.WriteLine("GEMM Parallel Test Suite");
                Console.WriteLine("========================");
                Console.WriteLine();

                if (runCorrectness)
                {
                    TestGemm.RunCorrectnessTests(multiWriter);
                }

                if (runDeterminism)
                {
                    TestGemm.RunDeterminismTests(multiWriter);
                }

                if (runPerformance)
                {
                    var perfMultiWriter = new MultiTextWriter(consoleOut, summaryWriter, perfWriter);
                    TestGemm.RunPerformanceTests(perfMultiWriter);
                }

                Console.WriteLine("Results written to run_summary.txt and perf.txt");
            }

            return 0;
        }
        catch (Exception ex)
        {
            Console.Error.WriteLine($"Error: {ex.Message}");
            Console.Error.WriteLine(ex.StackTrace);
            return 1;
        }
    }
}

// Helper class to write to multiple streams simultaneously
class MultiTextWriter : StreamWriter
{
    private readonly TextWriter[] writers;

    public MultiTextWriter(params TextWriter[] writers) : base(Stream.Null)
    {
        this.writers = writers;
    }

    public override void Write(char value)
    {
        foreach (var writer in writers)
        {
            writer.Write(value);
        }
    }

    public override void Write(string? value)
    {
        foreach (var writer in writers)
        {
            writer.Write(value);
        }
    }

    public override void WriteLine()
    {
        foreach (var writer in writers)
        {
            writer.WriteLine();
        }
    }

    public override void WriteLine(string? value)
    {
        foreach (var writer in writers)
        {
            writer.WriteLine(value);
        }
    }

    public override void Flush()
    {
        foreach (var writer in writers)
        {
            writer.Flush();
        }
    }

    protected override void Dispose(bool disposing)
    {
        if (disposing)
        {
            foreach (var writer in writers)
            {
                if (writer != Console.Out && writer != Console.Error)
                {
                    writer.Flush();
                }
            }
        }
        base.Dispose(disposing);
    }
}
