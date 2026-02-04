import java.util.Arrays;
import java.util.Random;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.math.BigInteger;

public class TestGemm {

    private static final int WARMUP_ITERATIONS = 5;
    private static final int BENCHMARK_ITERATIONS = 10;

    public static double[][] randomMatrix(int rows, int cols, Random rand) {
        double[][] matrix = new double[rows][cols];
        for (int i = 0; i < rows; i++) {
            for (int j = 0; j < cols; j++) {
                matrix[i][j] = rand.nextDouble();
            }
        }
        return matrix;
    }

    public static String hashMatrix(double[][] matrix) {
        try {
            MessageDigest md = MessageDigest.getInstance("SHA-256");
            for (double[] row : matrix) {
                for (double val : row) {
                    md.update(Double.toString(val).getBytes());
                }
            }
            byte[] digest = md.digest();
            return new BigInteger(1, digest).toString(16);
        } catch (NoSuchAlgorithmException e) {
            throw new RuntimeException(e);
        }
    }

    public static boolean compareMatrices(double[][] a, double[][] b) {
        if (a.length != b.length || a[0].length != b[0].length) {
            return false;
        }
        for (int i = 0; i < a.length; i++) {
            for (int j = 0; j < a[0].length; j++) {
                if (Math.abs(a[i][j] - b[i][j]) > 1e-9) {
                    return false;
                }
            }
        }
        return true;
    }

    public static void main(String[] args) {
        System.out.println("Running GEMM correctness and determinism tests...");
        StringBuilder summary = new StringBuilder();

        // Test cases
        int[][] testShapes = {
            {1, 1, 1},       // Edge case: 1x1
            {10, 10, 10},    // Small
            {128, 128, 128}, // Medium
            {512, 512, 512}, // Large
            {100, 200, 300}  // Rectangular
        };

        boolean allTestsPassed = true;

        for (int[] shape : testShapes) {
            int m = shape[0], k = shape[1], n = shape[2];
            System.out.println("\nTesting shape: M=" + m + ", K=" + k + ", N=" + n);
            summary.append("\n--- Shape: M=").append(m).append(", K=").append(k).append(", N=").append(n).append(" ---\n");

            Random rand = new Random(12345); // Fixed seed for reproducibility
            double[][] A = randomMatrix(m, k, rand);
            double[][] B = randomMatrix(k, n, rand);

            // Run sequential version
            double[][] C_seq = Gemm.run(A, B);
            String hash_seq = hashMatrix(C_seq);
            summary.append("Sequential Hash: ").append(hash_seq).append("\n");

            // Run parallel version (correctness)
            double[][] C_par1 = GemmParallel.run(A, B);
            String hash_par1 = hashMatrix(C_par1);
            summary.append("Parallel Run 1 Hash: ").append(hash_par1).append("\n");

            boolean correct = compareMatrices(C_seq, C_par1);
            if (correct) {
                System.out.println("Correctness PASSED");
                summary.append("Correctness: PASSED\n");
            } else {
                System.out.println("Correctness FAILED");
                summary.append("Correctness: FAILED\n");
                allTestsPassed = false;
            }

            // Run parallel version again (determinism)
            double[][] C_par2 = GemmParallel.run(A, B);
            String hash_par2 = hashMatrix(C_par2);
            summary.append("Parallel Run 2 Hash: ").append(hash_par2).append("\n");

            boolean deterministic = hash_par1.equals(hash_par2);
            if (deterministic) {
                System.out.println("Determinism PASSED");
                summary.append("Determinism: PASSED\n");
            } else {
                System.out.println("Determinism FAILED");
                summary.append("Determinism: FAILED\n");
                allTestsPassed = false;
            }
        }

        System.out.println("\n--- Performance Tests ---");
        summary.append("\n--- Performance ---\n");
        StringBuilder perfSummary = new StringBuilder();
        perfSummary.append("shape,type,time_ms\n");


        int perf_m = 1024;
        int perf_k = 1024;
        int perf_n = 1024;

        Random rand = new Random(54321);
        double[][] A_perf = randomMatrix(perf_m, perf_k, rand);
        double[][] B_perf = randomMatrix(perf_k, perf_n, rand);

        // Warmup
        for (int i = 0; i < WARMUP_ITERATIONS; i++) {
            Gemm.run(A_perf, B_perf);
            GemmParallel.run(A_perf, B_perf);
        }

        // Sequential benchmark
        long totalSeqTime = 0;
        for (int i = 0; i < BENCHMARK_ITERATIONS; i++) {
            long startTime = System.nanoTime();
            Gemm.run(A_perf, B_perf);
            long endTime = System.nanoTime();
            totalSeqTime += (endTime - startTime);
        }
        double avgSeqTime = (totalSeqTime / 1e6) / BENCHMARK_ITERATIONS;
        System.out.printf("Sequential average time: %.2f ms\n", avgSeqTime);
        summary.append("Sequential average time: ").append(String.format("%.2f", avgSeqTime)).append(" ms\n");
        perfSummary.append(String.format("%dx%dx%d,sequential,%.2f\n", perf_m, perf_k, perf_n, avgSeqTime));


        // Parallel benchmark
        long totalParTime = 0;
        for (int i = 0; i < BENCHMARK_ITERATIONS; i++) {
            long startTime = System.nanoTime();
            GemmParallel.run(A_perf, B_perf);
            long endTime = System.nanoTime();
            totalParTime += (endTime - startTime);
        }
        double avgParTime = (totalParTime / 1e6) / BENCHMARK_ITERATIONS;
        System.out.printf("Parallel average time:   %.2f ms\n", avgParTime);
        summary.append("Parallel average time:   ").append(String.format("%.2f", avgParTime)).append(" ms\n");
        perfSummary.append(String.format("%dx%dx%d,parallel,%.2f\n", perf_m, perf_k, perf_n, avgParTime));

        double speedup = avgSeqTime / avgParTime;
        System.out.printf("Speedup: %.2fx\n", speedup);
        summary.append("Speedup: ").append(String.format("%.2f", speedup)).append("x\n");

        try {
            java.nio.file.Files.write(java.nio.file.Paths.get("run_summary.txt"), summary.toString().getBytes());
            java.nio.file.Files.write(java.nio.file.Paths.get("perf.txt"), perfSummary.toString().getBytes());
        } catch (java.io.IOException e) {
            System.err.println("Failed to write summary files.");
            e.printStackTrace();
        }

        if (!allTestsPassed) {
            System.exit(1);
        }
    }
}
