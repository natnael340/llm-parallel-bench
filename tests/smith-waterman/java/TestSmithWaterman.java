import java.io.BufferedReader;
import java.io.FileReader;
import java.io.IOException;

public class Tests {
    private SmithWatermanParallel swStandard;
    private SmithWatermanParallel swHighGap;
    private static final double EPSILON = 1e-6;
    
    private int testsPassed = 0;
    private int testsFailed = 0;

    public int getPassedCount() {
        return testsPassed;
    }

    public int getFailedCount() {
        return testsFailed;
    }

    public void setUp() {
        swStandard = new SmithWatermanParallel(2, -1, -1);
        swHighGap = new SmithWatermanParallel(3, -3, -2);
    }

    private void runTest(String testName, Runnable testMethod) {
        System.out.print("Running: " + testName + "... ");
        try {
            testMethod.run();
            System.out.println("✓ PASSED");
            testsPassed++;
        } catch (Exception ex) {
            System.out.println("✗ FAILED: " + ex.getMessage());
            testsFailed++;
        }
    }

    private void assertEqual(Object expected, Object actual, String message) {
        if (expected == null && actual == null) return;
        if (expected == null || actual == null || !expected.equals(actual)) {
            throw new AssertionError("Expected: " + expected + ", Actual: " + actual + ". " + message);
        }
    }

    private void assertEqual(int expected, int actual, String message) {
        if (expected != actual) {
            throw new AssertionError("Expected: " + expected + ", Actual: " + actual + ". " + message);
        }
    }

    private void assertEqual(double expected, double actual, double delta, String message) {
        if (Math.abs(expected - actual) > delta) {
            throw new AssertionError("Expected: " + expected + ", Actual: " + actual + " (within " + delta + "). " + message);
        }
    }

    private void assertGreater(int actual, int threshold, String message) {
        if (actual <= threshold) {
            throw new AssertionError("Expected " + actual + " > " + threshold + ". " + message);
        }
    }

    private void assertGreaterOrEqual(int actual, int threshold, String message) {
        if (actual < threshold) {
            throw new AssertionError("Expected " + actual + " >= " + threshold + ". " + message);
        }
    }

    private void assertLess(double actual, double threshold, String message) {
        if (actual >= threshold) {
            throw new AssertionError("Expected " + actual + " < " + threshold + ". " + message);
        }
    }

    private void assertNotNull(Object obj, String message) {
        if (obj == null) {
            throw new AssertionError("Expected non-null object. " + message);
        }
    }

    // ==================== Basic Functionality Tests ====================

    public void testPerfectMatch() {
        String query = "ACGT";
        String reference = "ACGT";

        SmithWatermanParallel.AlignmentResult result = swStandard.findAlignment(query, reference);

        assertEqual(result.alignedA, result.alignedB, "");
        assertEqual(8, result.score, "");
        assertEqual(100.0, result.identity, EPSILON, "");
    }

    public void testNoMatch() {
        String query = "AAAA";
        String reference = "TTTT";

        SmithWatermanParallel.AlignmentResult result = swStandard.findAlignment(query, reference);

        assertEqual("", result.alignedA, "");
        assertEqual("", result.alignedB, "");
        assertEqual(0, result.score, "");
        assertEqual(0.0, result.identity, EPSILON, "");
    }

    public void testPartialMatch() {
        String query = "ACGTACGT";
        String reference = "TACGTGCA";

        SmithWatermanParallel.AlignmentResult result = swStandard.findAlignment(query, reference);

        assertEqual(result.alignedA.length(), result.alignedB.length(), "");
        assertEqual("TACGT", result.alignedA, "");
        assertEqual("TACGT", result.alignedB, "");
        assertEqual(10, result.score, "");
        assertEqual(100.0, result.identity, EPSILON, "");
    }

    public void testGapInQuery() {
        String query = "ACGT";
        String reference = "ACAGT";

        SmithWatermanParallel.AlignmentResult result = swStandard.findAlignment(query, reference);

        assertEqual("AC-GT", result.alignedA, "");
        assertEqual("ACAGT", result.alignedB, "");
        assertEqual(7, result.score, "");
        assertEqual(80.0, result.identity, EPSILON, "");
    }

    public void testGapInReference() {
        String query = "ACAGT";
        String reference = "ACGT";

        SmithWatermanParallel.AlignmentResult result = swStandard.findAlignment(query, reference);

        assertEqual("AC-GT", result.alignedB, "");
        assertEqual("ACAGT", result.alignedA, "");
        assertEqual(7, result.score, "");
        assertEqual(80.0, result.identity, EPSILON, "");
    }

    // ==================== Edge Cases ====================

    public void testEmptyQuery() {
        String query = "";
        String reference = "ACGT";

        int[][] H = swStandard.constructMatrix(query, reference);
        assertEqual(1, H.length, "");

        SmithWatermanParallel.AlignmentResult result = swStandard.traceback(H, query, reference);
        assertEqual("", result.alignedA, "");
        assertEqual("", result.alignedB, "");
        assertEqual(0, result.score, "");
        assertEqual(0.0, result.identity, EPSILON, "");
    }

    public void testEmptyReference() {
        String query = "ACGT";
        String reference = "";

        int[][] H = swStandard.constructMatrix(query, reference);
        assertEqual(1, H[0].length, "");

        SmithWatermanParallel.AlignmentResult result = swStandard.traceback(H, query, reference);
        assertEqual("", result.alignedA, "");
        assertEqual("", result.alignedB, "");
        assertEqual(0, result.score, "");
        assertEqual(0.0, result.identity, EPSILON, "");
    }

    public void testBothEmpty() {
        String query = "";
        String reference = "";

        int[][] H = swStandard.constructMatrix(query, reference);
        assertEqual(1, H.length, "");
        assertEqual(1, H[0].length, "");

        SmithWatermanParallel.AlignmentResult result = swStandard.traceback(H, query, reference);
        assertEqual("", result.alignedA, "");
        assertEqual("", result.alignedB, "");
        assertEqual(0, result.score, "");
        assertEqual(0.0, result.identity, EPSILON, "");
    }

    public void testSingleCharacterMatch() {
        String query = "A";
        String reference = "A";

        SmithWatermanParallel.AlignmentResult result = swStandard.findAlignment(query, reference);

        assertEqual("A", result.alignedA, "");
        assertEqual("A", result.alignedB, "");
        assertEqual(2, result.score, "");
        assertEqual(100.0, result.identity, EPSILON, "");
    }

    public void testSingleCharacterMismatch() {
        String query = "A";
        String reference = "T";

        SmithWatermanParallel.AlignmentResult result = swStandard.findAlignment(query, reference);

        assertEqual("", result.alignedA, "");
        assertEqual("", result.alignedB, "");
        assertEqual(0, result.score, "");
        assertEqual(0.0, result.identity, EPSILON, "");
    }

    public void testQueryMuchLonger() {
        String query = "ACGTACGTACGTACGT";
        String reference = "ACG";

        SmithWatermanParallel.AlignmentResult result = swStandard.findAlignment(query, reference);

        assertEqual(result.alignedA.length(), result.alignedB.length(), "");
        assertEqual("ACG", result.alignedB, "");
        assertEqual("ACG", result.alignedA, "");
        assertEqual(6, result.score, "");
        assertEqual(100.0, result.identity, EPSILON, "");
    }

    public void testReferenceMuchLonger() {
        String query = "ACG";
        String reference = "ACGTACGTACGTACGT";

        SmithWatermanParallel.AlignmentResult result = swStandard.findAlignment(query, reference);

        assertEqual(result.alignedA.length(), result.alignedB.length(), "");
        assertEqual("ACG", result.alignedB, "");
        assertEqual("ACG", result.alignedA, "");
        assertEqual(6, result.score, "");
        assertEqual(100.0, result.identity, EPSILON, "");
    }

    // ==================== Matrix Construction Tests ====================

    public void testMatrixDimensions() {
        String query = "ACGT";
        String reference = "TAGC";

        int[][] H = swStandard.constructMatrix(query, reference);

        assertEqual(query.length() + 1, H.length, "");
        assertEqual(reference.length() + 1, H[0].length, "");
    }

    public void testMatrixFirstRowColumnZeros() {
        String query = "ACGT";
        String reference = "TAGC";

        int[][] H = swStandard.constructMatrix(query, reference);

        // Check first row
        for (int val : H[0]) {
            assertEqual(0, val, "");
        }

        // Check first column
        for (int[] row : H) {
            assertEqual(0, row[0], "");
        }
    }

    public void testMatrixNonNegativeValues() {
        String query = "ACGTTAGC";
        String reference = "GCATACGT";

        int[][] H = swStandard.constructMatrix(query, reference);

        for (int[] row : H) {
            for (int val : row) {
                assertGreaterOrEqual(val, 0, "");
            }
        }
    }

    public void testFindHighestScoreSimple() {
        String query = "AC";
        String reference = "AC";

        int[][] H = swStandard.constructMatrix(query, reference);
        int[] pos = swStandard.findHighestScore(H);

        assertEqual(2, pos[0], "");
        assertEqual(2, pos[1], "");
    }

    public void testFindHighestScoreZeroMatrix() {
        int[][] H = {
            {0, 0, 0},
            {0, 0, 0},
            {0, 0, 0}
        };

        int[] pos = swStandard.findHighestScore(H);

        assertEqual(0, pos[0], "");
        assertEqual(0, pos[1], "");
    }

    // ==================== Different Scoring Schemes ====================

    public void testHighGapPenalty() {
        String query = "ACGT";
        String reference = "ACAGT";

        SmithWatermanParallel.AlignmentResult result = swHighGap.findAlignment(query, reference);

        assertEqual(result.alignedA.length(), result.alignedB.length(), "");
        assertEqual("AC-GT", result.alignedA, "");
        assertEqual("ACAGT", result.alignedB, "");
        assertEqual(10, result.score, "");
        assertEqual(80.0, result.identity, EPSILON, "");
    }

    public void testNegativeMatchScore() {
        SmithWatermanParallel swNegative = new SmithWatermanParallel(-1, -2, -1);
        String query = "ACGT";
        String reference = "ACGT";

        int[][] H = swNegative.constructMatrix(query, reference);

        for (int[] row : H) {
            for (int val : row) {
                assertEqual(0, val, "");
            }
        }
    }

    // ==================== Special Character Tests ====================

    public void testLowercaseSequences() {
        String query = "acgt";
        String reference = "acgt";

        SmithWatermanParallel.AlignmentResult result = swStandard.findAlignment(query, reference);

        assertEqual("acgt", result.alignedA, "");
        assertEqual("acgt", result.alignedB, "");
        assertEqual(8, result.score, "");
        assertEqual(100.0, result.identity, EPSILON, "");
    }

    public void testMixedCaseSequences() {
        String query = "AcGt";
        String reference = "aCgT";

        SmithWatermanParallel.AlignmentResult result = swStandard.findAlignment(query, reference);

        assertEqual(result.alignedA.length(), result.alignedB.length(), "");
        assertEqual("", result.alignedA, "");
        assertEqual("", result.alignedB, "");
        assertEqual(0, result.score, "");
        assertEqual(0.0, result.identity, EPSILON, "");
    }

    public void testNumericCharacters() {
        String query = "123";
        String reference = "123";

        SmithWatermanParallel.AlignmentResult result = swStandard.findAlignment(query, reference);

        assertEqual("123", result.alignedA, "");
        assertEqual("123", result.alignedB, "");
        assertEqual(6, result.score, "");
        assertEqual(100.0, result.identity, EPSILON, "");
    }

    public void testSpecialCharacters() {
        String query = "A-C*G";
        String reference = "A-C*G";

        SmithWatermanParallel.AlignmentResult result = swStandard.findAlignment(query, reference);

        assertEqual("A-C*G", result.alignedA, "");
        assertEqual("A-C*G", result.alignedB, "");
        assertEqual(10, result.score, "");
        assertEqual(100.0, result.identity, EPSILON, "");
    }

    // ==================== Repetitive Patterns ====================

    public void testRepeatedCharacters() {
        String query = "AAAA";
        String reference = "AAAA";

        SmithWatermanParallel.AlignmentResult result = swStandard.findAlignment(query, reference);

        assertEqual("AAAA", result.alignedA, "");
        assertEqual("AAAA", result.alignedB, "");
        assertEqual(8, result.score, "");
        assertEqual(100.0, result.identity, EPSILON, "");
    }

    public void testTandemRepeats() {
        String query = "ACGTACGTACGT";
        String reference = "ACGTACGTACGT";

        SmithWatermanParallel.AlignmentResult result = swStandard.findAlignment(query, reference);

        assertEqual(query, result.alignedA, "");
        assertEqual(reference, result.alignedB, "");
        assertEqual(24, result.score, "");
        assertEqual(100.0, result.identity, EPSILON, "");
    }

    // ==================== Alignment Properties Tests ====================

    public void testAlignmentLengthsEqual() {
        String[][] testCases = {
            {"ACGT", "TAGC", "A-C", "AGC"},
            {"AAAA", "TTTT", "", ""},
            {"ACGTACGT", "ACGT", "ACGT", "ACGT"},
            {"A", "ACGTACGT", "A", "A"},
            {"ACGTNNACGT", "ACGTACGT", "ACGTNNACGT", "ACGT--ACGT"}
        };

        for (String[] testCase : testCases) {
            String query = testCase[0];
            String reference = testCase[1];
            String expectedA = testCase[2];
            String expectedB = testCase[3];

            SmithWatermanParallel.AlignmentResult result = swStandard.findAlignment(query, reference);
            assertEqual(result.alignedA.length(), result.alignedB.length(),
                "Failed for query=" + query + ", reference=" + reference);
            assertEqual(expectedA, result.alignedA, "");
            assertEqual(expectedB, result.alignedB, "");
        }
    }

    public void testNoDoubleGaps() {
        String query = "ACGTACGT";
        String reference = "TAGCTAGC";

        SmithWatermanParallel.AlignmentResult result = swStandard.findAlignment(query, reference);

        assertEqual(result.alignedA.length(), result.alignedB.length(), "");
        assertEqual("A-CGTA-C", result.alignedA, "");
        assertEqual("AGC-TAGC", result.alignedB, "");
        assertEqual(7, result.score, "");
        assertEqual(62.5, result.identity, EPSILON, "");
    }

    // ==================== Real Biological Sequences ====================

    public void testRealisticDnaSequences() {
        String query = "ATCGATCGATCG";
        String reference = "ATCGATCGATCG";

        SmithWatermanParallel.AlignmentResult result = swStandard.findAlignment(query, reference);

        assertEqual(query, result.alignedA, "");
        assertEqual(reference, result.alignedB, "");
        assertEqual(24, result.score, "");
        assertEqual(100.0, result.identity, EPSILON, "");
    }

    public void testDnaWithSingleMutation() {
        String query = "ATCGATCGATCG";
        String reference = "ATCGTTCGATCG";

        SmithWatermanParallel.AlignmentResult result = swStandard.findAlignment(query, reference);

        assertGreater(result.alignedA.length(), 8, "");
        assertEqual(result.alignedA.length(), result.alignedB.length(), "");
        assertEqual(21, result.score, "");
        assertEqual(91.66666666666666, result.identity, EPSILON, "");
    }

    // ==================== Performance Tests ====================

    public void testPerformanceMediumSequences() {
        String query = "ACGT".repeat(50);
        String reference = "TAGC".repeat(50);

        long startTime = System.nanoTime();
        int[][] H = swStandard.constructMatrix(query, reference);
        long endTime = System.nanoTime();
        double matrixTime = (endTime - startTime) / 1_000_000_000.0;

        startTime = System.nanoTime();
        SmithWatermanParallel.AlignmentResult result = swStandard.traceback(H, query, reference);
        endTime = System.nanoTime();
        double tracebackTime = (endTime - startTime) / 1_000_000_000.0;

        System.out.print(String.format("(Matrix: %.4fs, Traceback: %.4fs) ", matrixTime, tracebackTime));

        assertLess(matrixTime, 5.0, "Matrix construction took too long");
        assertLess(tracebackTime, 2.0, "Traceback took too long");
    }

    public void testLargeSequencesFromFile() {
        String filePath = "large_test_input.txt";

        try (BufferedReader br = new BufferedReader(new FileReader(filePath))) {
            String query = br.readLine().trim();
            String reference = br.readLine().trim();
            int expectedScore = Integer.parseInt(br.readLine().trim());
            double expectedIdentity = Double.parseDouble(br.readLine().trim());

            int[][] H = swStandard.constructMatrix(query, reference);
            assertNotNull(H, "");
            assertEqual(query.length() + 1, H.length, "");
            assertEqual(reference.length() + 1, H[0].length, "");

            SmithWatermanParallel.AlignmentResult result = swStandard.traceback(H, query, reference);
            assertEqual(result.alignedA.length(), result.alignedB.length(), "");
            assertEqual(expectedScore, result.score, "");
            assertEqual(expectedIdentity, result.identity, EPSILON, "");
        } catch (IOException e) {
            System.out.print("SKIPPED (file not found) ");
        }
    }

    public void testPerformanceTest(){
        String filePath = "large_test_input.txt";

        try (BufferedReader br = new BufferedReader(new FileReader(filePath))) {
            String query = br.readLine().trim();
            String reference = br.readLine().trim();

            // record the mean and sd with 5 run and 20 iretations
            // with 1 warmup run

            int iters = 20;
            int runs = 5;

            // Warmup run
            SmithWatermanParallel.AlignmentResult _ = swStandard.findAlignment(query, reference);

            double[] times = new double[runs];

            for (int run = 0; run < runs; run++) {
                long startTime = System.nanoTime();
                for (int iter = 0; iter < iters; iter++) {
                    SmithWatermanParallel.AlignmentResult _ = swStandard.findAlignment(query, reference);
                }
                long endTime = System.nanoTime();

                times[run] = (endTime - startTime) / 1_000_000.0 / iters;
            }

            double mean = 0;
            for (double t : times) mean += t;
            mean /= runs;

            double variance = 0;
            for (double t : times) variance += (t - mean) * (t - mean);
            variance /= runs;
            double sd = Math.sqrt(variance);

            System.out.printf("Mean: %.2f ms, SD: %.2f ms%n", mean, sd);
            
        } catch (IOException e) {
            System.out.print("SKIPPED (file not found) ");
        }
    }

    // ==================== Run All Tests ====================

    public void runAllTests() {
        setUp();

        System.out.println("============================================");
        System.out.println("Running Smith-Waterman Tests");
        System.out.println("============================================\n");

        System.out.println("=== Basic Functionality Tests ===");
        runTest("testPerfectMatch", this::testPerfectMatch);
        runTest("testNoMatch", this::testNoMatch);
        runTest("testPartialMatch", this::testPartialMatch);
        runTest("testGapInQuery", this::testGapInQuery);
        runTest("testGapInReference", this::testGapInReference);

        System.out.println("\n=== Edge Cases ===");
        runTest("testEmptyQuery", this::testEmptyQuery);
        runTest("testEmptyReference", this::testEmptyReference);
        runTest("testBothEmpty", this::testBothEmpty);
        runTest("testSingleCharacterMatch", this::testSingleCharacterMatch);
        runTest("testSingleCharacterMismatch", this::testSingleCharacterMismatch);
        runTest("testQueryMuchLonger", this::testQueryMuchLonger);
        runTest("testReferenceMuchLonger", this::testReferenceMuchLonger);

        System.out.println("\n=== Matrix Construction Tests ===");
        runTest("testMatrixDimensions", this::testMatrixDimensions);
        runTest("testMatrixFirstRowColumnZeros", this::testMatrixFirstRowColumnZeros);
        runTest("testMatrixNonNegativeValues", this::testMatrixNonNegativeValues);
        runTest("testFindHighestScoreSimple", this::testFindHighestScoreSimple);
        runTest("testFindHighestScoreZeroMatrix", this::testFindHighestScoreZeroMatrix);

        System.out.println("\n=== Different Scoring Schemes ===");
        runTest("testHighGapPenalty", this::testHighGapPenalty);
        runTest("testNegativeMatchScore", this::testNegativeMatchScore);

        System.out.println("\n=== Special Character Tests ===");
        runTest("testLowercaseSequences", this::testLowercaseSequences);
        runTest("testMixedCaseSequences", this::testMixedCaseSequences);
        runTest("testNumericCharacters", this::testNumericCharacters);
        runTest("testSpecialCharacters", this::testSpecialCharacters);

        System.out.println("\n=== Repetitive Patterns ===");
        runTest("testRepeatedCharacters", this::testRepeatedCharacters);
        runTest("testTandemRepeats", this::testTandemRepeats);

        System.out.println("\n=== Alignment Properties ===");
        runTest("testAlignmentLengthsEqual", this::testAlignmentLengthsEqual);
        runTest("testNoDoubleGaps", this::testNoDoubleGaps);

        System.out.println("\n=== Biological Sequences ===");
        runTest("testRealisticDnaSequences", this::testRealisticDnaSequences);
        runTest("testDnaWithSingleMutation", this::testDnaWithSingleMutation);

        System.out.println("\n=== Performance Tests ===");
        runTest("testPerformanceMediumSequences", this::testPerformanceMediumSequences);
        runTest("testLargeSequencesFromFile", this::testLargeSequencesFromFile);
        runTest("testPerformanceTest", this::testPerformanceTest);



        System.out.println("\n============================================");
        System.out.println("Test Summary:");
        System.out.println("  Passed: " + testsPassed);
        System.out.println("  Failed: " + testsFailed);
        System.out.println("  Total:  " + (testsPassed + testsFailed));
        System.out.println("============================================");
    }
}