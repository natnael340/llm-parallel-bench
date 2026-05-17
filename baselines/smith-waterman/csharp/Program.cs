namespace SmithWatermanAlignment
{
    class Program
    {
        static int Main(string[] args)
        {
            // If "test" argument is passed, run tests
            if (args.Length > 0 && args[0] == "test")
            {
                Console.WriteLine("Running tests...\n");
                SmithWatermanTests tests = new SmithWatermanTests();
                tests.RunAllTests();
                return tests.GetFailedCount() > 0 ? 1 : 0;
            }
            
            // Otherwise, run the main application
            Console.WriteLine("Running Smith-Waterman Alignment\n");
            
            string seqA = "AGCTGTA";
            string seqB = "GCTAGTA";
            
            SmithWatermanParallel sw = new SmithWatermanParallel(2, -1, -2);
            var (alignedA, alignedB, score, identity) = sw.FindAlignment(seqA, seqB);
            
            Console.WriteLine($"Sequence A: {alignedA}");
            Console.WriteLine($"Sequence B: {alignedB}");
            Console.WriteLine($"Alignment score: {score}");
            Console.WriteLine($"Identity: {identity}%");
            
            return 0;
        }
    }
}