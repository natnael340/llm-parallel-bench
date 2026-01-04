public class Main {
    public static void main(String[] args) {
        // If "test" argument is passed, run tests
        if (args.length > 0 && args[0].equals("test")) {
            System.out.println("Running tests...\n");
            Tests tests = new Tests();
            tests.runAllTests();
            System.exit(tests.getFailedCount() > 0 ? 1 : 0);
        }
        
        // Otherwise, run the main application
        System.out.println("Running Smith-Waterman Alignment\n");
        
        String seqA = "AGCTGTA";
        String seqB = "GCTAGTA";
        
        SmithWaterman sw = new SmithWaterman(2, -1, -2);
        SmithWaterman.AlignmentResult result = sw.findAlignment(seqA, seqB);
        
        System.out.println("Sequence A: " + result.alignedA);
        System.out.println("Sequence B: " + result.alignedB);
        System.out.println("Alignment score: " + result.score);
        System.out.println("Identity: " + result.identity + "%");
    }
}