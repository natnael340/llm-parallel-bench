import java.util.*;
import java.security.MessageDigest;
import java.io.*;

public class TestGemm {

    private static class TestResult {
        String name;
        boolean passed;
        String message;

        TestResult(String name, boolean passed, String message) {
            this.name = name;
            this.passed = passed;
            this.message = message;
        }
    }

    private static String computeHash(double[][] matrix) {
        try {
            MessageDigest md = MessageDigest.getInstance("SHA-256");
            for (double[] row : matrix) {
                for (double val : row) {
                    long bits = Double.doubleToLongBits(val);
                    for (int i = 0; i < 8; i++) {
                        md.update((byte) (bits >> (i * 8)));
                    }
                }
            }
            byte[] digest = md.digest();
            StringBuilder sb = new StringBuilder();
            for (byte b : digest) {
                sb.append(String.format("%02x", b));
            }
            return sb.toString();
        } catch (Exception e) {
            throw new RuntimeException(e);
        }
    }

    private static boolean matricesEqual(double[][] A, double[][] B) {
        if (A.length != B.length) return false;
        for (int i = 0; i < A.length; i++) {
            if (A[i].length != B[i].length) return false;
            for (int j = 0; j < A[i].length; j++) {
                if (Double.doubleToLongBits(A[i][j]) != Double.doubleToLongBits(B[i][j])) {
                    return false;
                }
            }
        }
        return true;
    }

    private static double[][] randomMatrix(int rows, int cols, Random rng) {
        double[][] result = new double[rows][cols];
        for (int i = 0; i < rows; i++) {
            for (int j = 0; j < cols; j++) {
                result[i][j] = rng.nextDouble() * 10.0 - 5.0;
            }
        }
        return result;
    }

    private static double[][] copyMatrix(double[][] matrix) {
        double[][] result = new double[matrix.length][];
        for (int i = 0; i < matrix.length; i++) {
            result[i] = Arrays.copyOf(matrix[i], matrix[i].length);
        }
        return result;
    }

    private static List<TestResult> runCorrectnessTests() {
        List<TestResult> results = new ArrayList<>();
        Random rng = new Random(42);

        // Test 1: 1x1 matrix
        {
            double[][] A = {{2.0}};
            double[][] B = {{3.0}};
            double[][] seqResult = Gemm.run(A, B);
            double[][] parResult = GemmParallel.run(A, B);
            boolean passed = matricesEqual(seqResult, parResult);
            results.add(new TestResult("1x1 matrix", passed,
                passed ? "PASS" : "FAIL: Results differ"));
        }

        // Test 2: 1xN matrix
        {
            double[][] A = {{1.0, 2.0, 3.0}};
            double[][] B = {{1.0}, {2.0}, {3.0}};
            double[][] seqResult = Gemm.run(A, B);
            double[][] parResult = GemmParallel.run(A, B);
            boolean passed = matricesEqual(seqResult, parResult);
            results.add(new TestResult("1xN matrix", passed,
                passed ? "PASS" : "FAIL: Results differ"));
        }

        // Test 3: Mx1 matrix
        {
            double[][] A = {{1.0}, {2.0}, {3.0}};
            double[][] B = {{1.0, 2.0, 3.0}};
            double[][] seqResult = Gemm.run(A, B);
            double[][] parResult = GemmParallel.run(A, B);
            boolean passed = matricesEqual(seqResult, parResult);
            results.add(new TestResult("Mx1 matrix", passed,
                passed ? "PASS" : "FAIL: Results differ"));
        }

        // Test 4: Small 8x8
        {
            double[][] A = randomMatrix(8, 8, rng);
            double[][] B = randomMatrix(8, 8, rng);
            double[][] seqResult = Gemm.run(A, B);
            double[][] parResult = GemmParallel.run(A, B);
            boolean passed = matricesEqual(seqResult, parResult);
            results.add(new TestResult("8x8 matrix", passed,
                passed ? "PASS" : "FAIL: Results differ"));
        }

        // Test 5: Medium 128x128
        {
            double[][] A = randomMatrix(128, 128, rng);
            double[][] B = randomMatrix(128, 128, rng);
            double[][] seqResult = Gemm.run(A, B);
            double[][] parResult = GemmParallel.run(A, B);
            boolean passed = matricesEqual(seqResult, parResult);
            results.add(new TestResult("128x128 matrix", passed,
                passed ? "PASS" : "FAIL: Results differ"));
        }

        // Test 6: Large 512x512
        {
            double[][] A = randomMatrix(512, 512, rng);
            double[][] B = randomMatrix(512, 512, rng);
            double[][] seqResult = Gemm.run(A, B);
            double[][] parResult = GemmParallel.run(A, B);
            boolean passed = matricesEqual(seqResult, parResult);
            results.add(new TestResult("512x512 matrix", passed,
                passed ? "PASS" : "FAIL: Results differ"));
        }

        // Test 7: Non-square 100x200 * 200x150
        {
            double[][] A = randomMatrix(100, 200, rng);
            double[][] B = randomMatrix(200, 150, rng);
            double[][] seqResult = Gemm.run(A, B);
            double[][] parResult = GemmParallel.run(A, B);
            boolean passed = matricesEqual(seqResult, parResult);
            results.add(new TestResult("100x200 * 200x150", passed,
                passed ? "PASS" : "FAIL: Results differ"));
        }

        // Test 8: With alpha
        {
            double[][] A = randomMatrix(64, 64, rng);
            double[][] B = randomMatrix(64, 64, rng);
            double alpha = 2.5;
            double[][] seqResult = Gemm.run(A, B, alpha);
            double[][] parResult = GemmParallel.run(A, B, alpha);
            boolean passed = matricesEqual(seqResult, parResult);
            results.add(new TestResult("64x64 with alpha=2.5", passed,
                passed ? "PASS" : "FAIL: Results differ"));
        }

        // Test 9: With C and beta
        {
            double[][] A = randomMatrix(64, 64, rng);
            double[][] B = randomMatrix(64, 64, rng);
            double[][] C_seq = randomMatrix(64, 64, rng);
            double[][] C_par = copyMatrix(C_seq);
            double alpha = 1.5;
            double beta = 0.5;
            double[][] seqResult = Gemm.run(A, B, alpha, C_seq, beta);
            double[][] parResult = GemmParallel.run(A, B, alpha, C_par, beta);
            boolean passed = matricesEqual(seqResult, parResult);
            results.add(new TestResult("64x64 with alpha=1.5, beta=0.5", passed,
                passed ? "PASS" : "FAIL: Results differ"));
        }

        // Test 10: alpha = 0
        {
            double[][] A = randomMatrix(64, 64, rng);
            double[][] B = randomMatrix(64, 64, rng);
            double[][] C_seq = randomMatrix(64, 64, rng);
            double[][] C_par = copyMatrix(C_seq);
            double alpha = 0.0;
            double beta = 2.0;
            double[][] seqResult = Gemm.run(A, B, alpha, C_seq, beta);
            double[][] parResult = GemmParallel.run(A, B, alpha, C_par, beta);
            boolean passed = matricesEqual(seqResult, parResult);
            results.add(new TestResult("64x64 with alpha=0", passed,
                passed ? "PASS" : "FAIL: Results differ"));
        }

        return results;
    }

    private static List<TestResult> runDeterminismTests() {
        List<TestResult> results = new ArrayList<>();
        Random rng = new Random(123);

        // Test 1: 512x512 - run twice, compare hashes
        {
            double[][] A = randomMatrix(512, 512, rng);
            double[][] B = randomMatrix(512, 512, rng);
            
            double[][] result1 = GemmParallel.run(A, B);
            String hash1 = computeHash(result1);
            
            double[][] result2 = GemmParallel.run(A, B);
            String hash2 = computeHash(result2);
            
            boolean passed = hash1.equals(hash2);
            results.add(new TestResult("Determinism 512x512 (run 1 vs run 2)", passed,
                passed ? "PASS: hash1=" + hash1.substring(0, 16) + "..., hash2=" + hash2.substring(0, 16) + "..." :
                         "FAIL: hash1=" + hash1 + ", hash2=" + hash2));
        }

        // Test 2: 256x256 - run three times
        {
            double[][] A = randomMatrix(256, 256, rng);
            double[][] B = randomMatrix(256, 256, rng);
            
            double[][] result1 = GemmParallel.run(A, B);
            String hash1 = computeHash(result1);
            
            double[][] result2 = GemmParallel.run(A, B);
            String hash2 = computeHash(result2);
            
            double[][] result3 = GemmParallel.run(A, B);
            String hash3 = computeHash(result3);
            
            boolean passed = hash1.equals(hash2) && hash2.equals(hash3);
            results.add(new TestResult("Determinism 256x256 (3 runs)", passed,
                passed ? "PASS: all hashes match" :
                         "FAIL: hash1=" + hash1 + ", hash2=" + hash2 + ", hash3=" + hash3));
        }

        return results;
    }

    private static void runPerformanceTests() throws IOException {
        Random rng = new Random(456);
        int N = 512;
        int warmupRuns = 2;
        int testRuns = 5;

        double[][] A = randomMatrix(N, N, rng);
        double[][] B = randomMatrix(N, N, rng);

        // Warmup
        for (int i = 0; i < warmupRuns; i++) {
            Gemm.run(A, B);
            GemmParallel.run(A, B);
        }

        // Sequential timing
        long seqTotal = 0;
        for (int i = 0; i < testRuns; i++) {
            long start = System.nanoTime();
            Gemm.run(A, B);
            long end = System.nanoTime();
            seqTotal += (end - start);
        }
        double seqAvg = seqTotal / (double) testRuns / 1e9;

        // Parallel timing
        long parTotal = 0;
        for (int i = 0; i < testRuns; i++) {
            long start = System.nanoTime();
            GemmParallel.run(A, B);
            long end = System.nanoTime();
            parTotal += (end - start);
        }
        double parAvg = parTotal / (double) testRuns / 1e9;

        double speedup = seqAvg / parAvg;
        int cores = Runtime.getRuntime().availableProcessors();
        double efficiency = speedup / cores;

        StringBuilder sb = new StringBuilder();
        sb.append("Performance Test Results\n");
        sb.append("========================\n");
        sb.append("Matrix size: ").append(N).append("x").append(N).append("\n");
        sb.append("Test runs: ").append(testRuns).append("\n");
        sb.append("Sequential time: ").append(String.format("%.4f", seqAvg)).append(" seconds\n");
        sb.append("Parallel time: ").append(String.format("%.4f", parAvg)).append(" seconds\n");
        sb.append("Speedup: ").append(String.format("%.2f", speedup)).append("x\n");
        sb.append("Cores: ").append(cores).append("\n");
        sb.append("Parallel efficiency: ").append(String.format("%.2f", efficiency * 100)).append("%\n");

        System.out.println(sb.toString());

        try (PrintWriter writer = new PrintWriter(new FileWriter("perf.txt"))) {
            writer.print(sb.toString());
        }
    }

    private static void writeSummary(List<TestResult> correctnessResults, List<TestResult> determinismResults) throws IOException {
        StringBuilder sb = new StringBuilder();
        sb.append("GEMM Test Summary\n");
        sb.append("=================\n\n");

        sb.append("Correctness Tests\n");
        sb.append("-----------------\n");
        int correctnessPassed = 0;
        for (TestResult result : correctnessResults) {
            sb.append(result.name).append(": ").append(result.message).append("\n");
            if (result.passed) correctnessPassed++;
        }
        sb.append("Passed: ").append(correctnessPassed).append("/").append(correctnessResults.size()).append("\n\n");

        sb.append("Determinism Tests\n");
        sb.append("-----------------\n");
        int determinismPassed = 0;
        for (TestResult result : determinismResults) {
            sb.append(result.name).append(": ").append(result.message).append("\n");
            if (result.passed) determinismPassed++;
        }
        sb.append("Passed: ").append(determinismPassed).append("/").append(determinismResults.size()).append("\n\n");

        int totalPassed = correctnessPassed + determinismPassed;
        int totalTests = correctnessResults.size() + determinismResults.size();
        sb.append("Overall: ").append(totalPassed).append("/").append(totalTests).append(" tests passed\n");

        System.out.println(sb.toString());

        try (PrintWriter writer = new PrintWriter(new FileWriter("run_summary.txt"))) {
            writer.print(sb.toString());
        }
    }

    public static void main(String[] args) throws IOException {
        if (args.length == 0) {
            System.out.println("Usage: java TestGemm [correctness|determinism|performance|all]");
            System.exit(1);
        }

        String mode = args[0];
        boolean allPassed = true;

        if (mode.equals("correctness") || mode.equals("all")) {
            System.out.println("Running correctness tests...");
            List<TestResult> results = runCorrectnessTests();
            for (TestResult result : results) {
                System.out.println(result.name + ": " + result.message);
                if (!result.passed) allPassed = false;
            }
            if (mode.equals("correctness")) {
                writeSummary(results, new ArrayList<>());
            }
        }

        if (mode.equals("determinism") || mode.equals("all")) {
            System.out.println("\nRunning determinism tests...");
            List<TestResult> results = runDeterminismTests();
            for (TestResult result : results) {
                System.out.println(result.name + ": " + result.message);
                if (!result.passed) allPassed = false;
            }
            if (mode.equals("determinism")) {
                writeSummary(new ArrayList<>(), results);
            }
        }

        if (mode.equals("all")) {
            List<TestResult> correctnessResults = runCorrectnessTests();
            List<TestResult> determinismResults = runDeterminismTests();
            writeSummary(correctnessResults, determinismResults);
            
            for (TestResult r : correctnessResults) {
                if (!r.passed) allPassed = false;
            }
            for (TestResult r : determinismResults) {
                if (!r.passed) allPassed = false;
            }
        }

        if (mode.equals("performance") || mode.equals("all")) {
            System.out.println("\nRunning performance tests...");
            runPerformanceTests();
        }

        System.exit(allPassed ? 0 : 1);
    }
}
