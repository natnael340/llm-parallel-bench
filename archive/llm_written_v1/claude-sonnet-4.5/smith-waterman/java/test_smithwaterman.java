import java.security.MessageDigest;
import java.util.Arrays;
import java.nio.charset.StandardCharsets;

/**
 * Differential test harness for Smith-Waterman parallel implementation.
 * Tests correctness (vs sequential baseline), determinism, and performance.
 */
public class TestSmithWaterman {
    
    private static final int MATCH_SCORE = 3;
    private static final int MISMATCH_SCORE = -3;
    private static final int GAP_SCORE = -2;
    
    public static void main(String[] args) {
        boolean allPassed = true;
        
        System.out.println("=== Smith-Waterman Differential Testing ===\n");
        
        // Edge cases
        allPassed &= runTest("Edge: Empty query", "", "ACGT");
        allPassed &= runTest("Edge: Empty reference", "ACGT", "");
        allPassed &= runTest("Edge: Both empty", "", "");
        allPassed &= runTest("Edge: Single char match", "A", "A");
        allPassed &= runTest("Edge: Single char mismatch", "A", "T");
        
        // Small cases
        allPassed &= runTest("Small: Identical short", "ACGT", "ACGT");
        allPassed &= runTest("Small: Different short", "AAAA", "TTTT");
        allPassed &= runTest("Small: Partial match", "ACGTACGT", "CGTA");
        
        // Medium cases
        String medQuery = generateSequence(150, 12345);
        String medRef = generateSequence(200, 67890);
        allPassed &= runTest("Medium: Random 150x200", medQuery, medRef);
        
        String medQuery2 = "ACGT".repeat(50);
        String medRef2 = "TGCA".repeat(60);
        allPassed &= runTest("Medium: Repeated pattern 200x240", medQuery2, medRef2);
        
        // Large cases
        String largeQuery = generateSequence(500, 11111);
        String largeRef = generateSequence(600, 22222);
        allPassed &= runTest("Large: Random 500x600", largeQuery, largeRef);
        
        String largeQuery2 = generateSequence(800, 33333);
        String largeRef2 = generateSequence(700, 44444);
        allPassed &= runTest("Large: Random 800x700", largeQuery2, largeRef2);
        
        // Very large (triggers parallel path)
        String veryLargeQuery = generateSequence(1000, 55555);
        String veryLargeRef = generateSequence(1200, 66666);
        allPassed &= runTest("VeryLarge: Random 1000x1200", veryLargeQuery, veryLargeRef);
        
        // Determinism tests (run parallel twice)
        System.out.println("\n=== Determinism Tests ===\n");
        allPassed &= runDeterminismTest("Det: Medium 150x200", medQuery, medRef);
        allPassed &= runDeterminismTest("Det: Large 500x600", largeQuery, largeRef);
        allPassed &= runDeterminismTest("Det: VeryLarge 1000x1200", veryLargeQuery, veryLargeRef);
        
        // Performance comparison
        System.out.println("\n=== Performance Tests ===\n");
        runPerformanceTest("Perf: Large 500x600", largeQuery, largeRef);
        runPerformanceTest("Perf: Large 800x700", largeQuery2, largeRef2);
        runPerformanceTest("Perf: VeryLarge 1000x1200", veryLargeQuery, veryLargeRef);
        
        System.out.println("\n" + ("=".repeat(50)));
        if (allPassed) {
            System.out.println("✓ ALL TESTS PASSED");
            System.exit(0);
        } else {
            System.out.println("✗ SOME TESTS FAILED");
            System.exit(1);
        }
    }
    
    private static boolean runTest(String testName, String query, String reference) {
        System.out.println("Test: " + testName);
        System.out.println("  Query length: " + query.length() + ", Reference length: " + reference.length());
        
        try {
            SmithWatermanSequential seqSW = new SmithWatermanSequential(MATCH_SCORE, MISMATCH_SCORE, GAP_SCORE);
            SmithWaterman parSW = new SmithWaterman(MATCH_SCORE, MISMATCH_SCORE, GAP_SCORE);
            
            // Run sequential
            long startSeq = System.nanoTime();
            SmithWatermanSequential.AlignmentResult seqResult = seqSW.findAlignment(query, reference);
            long endSeq = System.nanoTime();
            
            // Run parallel
            long startPar = System.nanoTime();
            SmithWaterman.AlignmentResult parResult = parSW.findAlignment(query, reference);
            long endPar = System.nanoTime();
            
            // Compare results
            boolean scoreMatch = seqResult.score == parResult.score;
            boolean alignedAMatch = seqResult.alignedA.equals(parResult.alignedA);
            boolean alignedBMatch = seqResult.alignedB.equals(parResult.alignedB);
            boolean identityMatch = Math.abs(seqResult.identity - parResult.identity) < 0.0001;
            
            boolean passed = scoreMatch && alignedAMatch && alignedBMatch && identityMatch;
            
            double seqMs = (endSeq - startSeq) / 1_000_000.0;
            double parMs = (endPar - startPar) / 1_000_000.0;
            
            System.out.println("  Sequential: " + String.format("%.2f", seqMs) + " ms");
            System.out.println("  Parallel:   " + String.format("%.2f", parMs) + " ms");
            System.out.println("  Score match: " + scoreMatch + " (seq=" + seqResult.score + ", par=" + parResult.score + ")");
            System.out.println("  Alignment match: " + (alignedAMatch && alignedBMatch));
            System.out.println("  Result: " + (passed ? "✓ PASS" : "✗ FAIL"));
            System.out.println();
            
            return passed;
        } catch (Exception e) {
            System.out.println("  ✗ EXCEPTION: " + e.getMessage());
            e.printStackTrace();
            System.out.println();
            return false;
        }
    }
    
    private static boolean runDeterminismTest(String testName, String query, String reference) {
        System.out.println("Test: " + testName);
        System.out.println("  Query length: " + query.length() + ", Reference length: " + reference.length());
        
        try {
            SmithWaterman parSW = new SmithWaterman(MATCH_SCORE, MISMATCH_SCORE, GAP_SCORE);
            
            // Run parallel twice
            SmithWaterman.AlignmentResult result1 = parSW.findAlignment(query, reference);
            SmithWaterman.AlignmentResult result2 = parSW.findAlignment(query, reference);
            
            // Compute hashes
            String hash1 = computeHash(result1);
            String hash2 = computeHash(result2);
            
            boolean passed = hash1.equals(hash2);
            
            System.out.println("  Run 1 hash: " + hash1);
            System.out.println("  Run 2 hash: " + hash2);
            System.out.println("  Result: " + (passed ? "✓ DETERMINISTIC" : "✗ NON-DETERMINISTIC"));
            System.out.println();
            
            return passed;
        } catch (Exception e) {
            System.out.println("  ✗ EXCEPTION: " + e.getMessage());
            e.printStackTrace();
            System.out.println();
            return false;
        }
    }
    
    private static void runPerformanceTest(String testName, String query, String reference) {
        System.out.println("Test: " + testName);
        System.out.println("  Query length: " + query.length() + ", Reference length: " + reference.length());
        System.out.println("  Matrix size: " + (long)query.length() * reference.length());
        
        try {
            SmithWatermanSequential seqSW = new SmithWatermanSequential(MATCH_SCORE, MISMATCH_SCORE, GAP_SCORE);
            SmithWaterman parSW = new SmithWaterman(MATCH_SCORE, MISMATCH_SCORE, GAP_SCORE);
            
            // Warmup
            seqSW.findAlignment(query.substring(0, Math.min(50, query.length())), 
                               reference.substring(0, Math.min(50, reference.length())));
            parSW.findAlignment(query.substring(0, Math.min(50, query.length())), 
                               reference.substring(0, Math.min(50, reference.length())));
            
            // Sequential timing (3 runs)
            long seqTotal = 0;
            for (int i = 0; i < 3; i++) {
                long start = System.nanoTime();
                seqSW.findAlignment(query, reference);
                long end = System.nanoTime();
                seqTotal += (end - start);
            }
            double seqAvgMs = (seqTotal / 3.0) / 1_000_000.0;
            
            // Parallel timing (3 runs)
            long parTotal = 0;
            for (int i = 0; i < 3; i++) {
                long start = System.nanoTime();
                parSW.findAlignment(query, reference);
                long end = System.nanoTime();
                parTotal += (end - start);
            }
            double parAvgMs = (parTotal / 3.0) / 1_000_000.0;
            
            double speedup = seqAvgMs / parAvgMs;
            int cores = Runtime.getRuntime().availableProcessors();
            
            System.out.println("  Sequential avg: " + String.format("%.2f", seqAvgMs) + " ms");
            System.out.println("  Parallel avg:   " + String.format("%.2f", parAvgMs) + " ms");
            System.out.println("  Speedup:        " + String.format("%.2f", speedup) + "x");
            System.out.println("  Cores:          " + cores);
            System.out.println();
        } catch (Exception e) {
            System.out.println("  ✗ EXCEPTION: " + e.getMessage());
            e.printStackTrace();
            System.out.println();
        }
    }
    
    private static String generateSequence(int length, long seed) {
        char[] bases = {'A', 'C', 'G', 'T'};
        StringBuilder sb = new StringBuilder(length);
        long state = seed;
        for (int i = 0; i < length; i++) {
            // Simple LCG (linear congruential generator)
            state = (state * 1103515245L + 12345L) & 0x7fffffffL;
            sb.append(bases[(int)(state % 4)]);
        }
        return sb.toString();
    }
    
    private static String computeHash(SmithWaterman.AlignmentResult result) {
        try {
            MessageDigest md = MessageDigest.getInstance("SHA-256");
            String data = result.alignedA + "|" + result.alignedB + "|" + 
                         result.score + "|" + result.identity;
            byte[] hash = md.digest(data.getBytes(StandardCharsets.UTF_8));
            StringBuilder hexString = new StringBuilder();
            for (byte b : hash) {
                String hex = Integer.toHexString(0xff & b);
                if (hex.length() == 1) hexString.append('0');
                hexString.append(hex);
            }
            return hexString.toString().substring(0, 16);
        } catch (Exception e) {
            return "hash-error";
        }
    }
}
