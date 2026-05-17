import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.Arrays;

public class TestSmithWaterman {

    private static final int MATCH_SCORE = 2;
    private static final int MISMATCH_SCORE = -1;
    private static final int GAP_SCORE = -1;

    public static void main(String[] args) {
        System.out.println("Running Smith-Waterman Differential Tests...");

        // Test Cases
        TestCase[] testCases = new TestCase[]{
            new TestCase("EMPTY", "", ""),
            new TestCase("SMALL_IDENTICAL", "AGTC", "AGTC"),
            new TestCase("SMALL_DIFFERENT", "AGTC", "AGGC"),
            new TestCase("MEDIUM_SEQ", "GATTACA", "GCATGCU"),
            new TestCase("MEDIUM_SEQ_2", "ACGTACGT", "ACGTACGT"),
            new TestCase("LARGE_SEQ", generateRandomString(1000), generateRandomString(1000)),
            new TestCase("LARGE_SEQ_DISSIMILAR", generateRandomString(1200), generateRandomString(800)),
        };

        boolean allTestsPassed = true;
        for (TestCase tc : testCases) {
            System.out.println("--- Running Test Case: " + tc.name + " ---");
            boolean passed = runTest(tc.query, tc.reference);
            if (!passed) {
                allTestsPassed = false;
            }
            System.out.println("--- Test Case " + tc.name + ": " + (passed ? "PASSED" : "FAILED") + " ---\n");
        }

        if (allTestsPassed) {
            System.out.println("All tests passed successfully!");
            System.exit(0);
        } else {
            System.err.println("Some tests failed.");
            System.exit(1);
        }
    }

    private static boolean runTest(String query, String reference) {
        // 1. Run Sequential Baseline
        SmithWaterman sw = new SmithWaterman(MATCH_SCORE, MISMATCH_SCORE, GAP_SCORE);
        SmithWaterman.AlignmentResult sequentialResult = sw.findAlignment(query, reference);
        System.out.println("Sequential run complete.");

        // 2. Run Parallel Implementation (First Run)
        SmithWatermanParallel swParallel = new SmithWatermanParallel(MATCH_SCORE, MISMATCH_SCORE, GAP_SCORE);
        SmithWatermanParallel.AlignmentResult parallelResult1 = swParallel.findAlignment(query, reference);
        System.out.println("Parallel run 1 complete.");

        // 3. Run Parallel Implementation (Second Run for Determinism)
        SmithWatermanParallel.AlignmentResult parallelResult2 = swParallel.findAlignment(query, reference);
        swParallel.shutdown();
        System.out.println("Parallel run 2 complete.");

        // 4. Compare Results
        boolean correctnessCheck = sequentialResult.alignedA.equals(parallelResult1.alignedA) &&
                                   sequentialResult.alignedB.equals(parallelResult1.alignedB) &&
                                   sequentialResult.score == parallelResult1.score;

        if (!correctnessCheck) {
            System.err.println("Correctness Check FAILED: Sequential and Parallel results do not match.");
            System.err.println("Sequential: " + sequentialResult);
            System.err.println("Parallel:   " + parallelResult1);
            return false;
        }
        System.out.println("Correctness Check PASSED.");

        // 5. Determinism Check
        String hash1 = toHash(parallelResult1);
        String hash2 = toHash(parallelResult2);
        boolean determinismCheck = hash1.equals(hash2);

        if (!determinismCheck) {
            System.err.println("Determinism Check FAILED: Two parallel runs produced different results.");
            System.err.println("Run 1 Hash: " + hash1);
            System.err.println("Run 2 Hash: " + hash2);
            return false;
        }
        System.out.println("Determinism Check PASSED. Hash: " + hash1);

        return true;
    }

    private static String toHash(SmithWatermanParallel.AlignmentResult result) {
        try {
            MessageDigest md = MessageDigest.getInstance("SHA-256");
            String data = result.alignedA + result.alignedB + result.score + result.identity;
            byte[] hashBytes = md.digest(data.getBytes());
            StringBuilder sb = new StringBuilder();
            for (byte b : hashBytes) {
                sb.append(String.format("%02x", b));
            }
            return sb.toString();
        } catch (NoSuchAlgorithmException e) {
            throw new RuntimeException("Could not create SHA-256 hasher", e);
        }
    }
    
    private static String generateRandomString(int length) {
        String chars = "ACGT";
        StringBuilder sb = new StringBuilder(length);
        java.util.Random random = new java.util.Random();
        for (int i = 0; i < length; i++) {
            sb.append(chars.charAt(random.nextInt(chars.length())));
        }
        return sb.toString();
    }

    static class TestCase {
        String name;
        String query;
        String reference;

        TestCase(String name, String query, String reference) {
            this.name = name;
            this.query = query;
            this.reference = reference;
        }
    }
}
