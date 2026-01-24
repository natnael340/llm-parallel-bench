import java.util.*;

public class GemmTestRunner {
    private static int passed = 0;
    private static int failed = 0;

    public static void main(String[] args) {
        System.out.println("Running GEMM Tests...\n");

        // Identity and basic tests
        test("Identity left multiplication", GemmTestRunner::testIdentityLeft);
        test("Identity right multiplication", GemmTestRunner::testIdentityRight);
        test("Zero matrices yield zero", GemmTestRunner::testZeroMatricesYieldZero);

        // Alpha/Beta parameter tests
        test("Alpha zero with C=null", GemmTestRunner::testAlphaZeroWithCNull);
        test("Alpha zero with C, beta=1 preserves C", GemmTestRunner::testAlphaZeroWithCBetaOnePreservesC);
        test("Alpha zero with beta scales once", GemmTestRunner::testAlphaZeroWithBetaScalesOnce);
        test("Beta zero ignores input C", GemmTestRunner::testBetaZeroIgnoresInputC);
        test("Beta one accumulates into C", GemmTestRunner::testBetaOneAccumulatesIntoC);
        test("Negative alpha and beta", GemmTestRunner::testNegativeAlphaAndBeta);

        // Shape tests
        test("Rectangular tall skinny", GemmTestRunner::testRectangularTallSkinny);
        test("Rectangular short fat", GemmTestRunner::testRectangularShortFat);
        test("Single row times single column (scalar)", GemmTestRunner::testSingleRowTimesSingleColumn);
        test("Row vector times matrix", GemmTestRunner::testRowVectorTimesMatrix);
        test("Matrix times column vector", GemmTestRunner::testMatrixTimesColumnVector);

        // General correctness tests
        test("General random compare reference", GemmTestRunner::testGeneralRandomCompareReference);
        test("Not multiple of block sizes", GemmTestRunner::testNotMultipleOfBlockSizes);
        test("Block sizes one matches naive", GemmTestRunner::testBlockSizesOneMatchesNaive);
        test("Block sizes larger than dims", GemmTestRunner::testBlockSizesLargerThanDims);

        // Object identity and mutation tests
        test("In-place C object identity", GemmTestRunner::testInPlaceCObjectIdentity);
        test("C created when null", GemmTestRunner::testCCreatedWhenNull);

        // Validation tests
        test("Dimension mismatch raises", GemmTestRunner::testDimensionMismatchRaises);
        test("Invalid C shape raises", GemmTestRunner::testInvalidCShapeRaises);
        test("Ragged A rejected", GemmTestRunner::testRaggedARejected);
        test("Ragged B rejected", GemmTestRunner::testRaggedBRejected);

        // Special values
        test("NaN propagation", GemmTestRunner::testNaNPropagation);
        test("Infinity propagation", GemmTestRunner::testInfinityPropagation);

        // Accumulation tests
        test("Repeat calls accumulate with beta=1", GemmTestRunner::testRepeatCallsAccumulateWithBetaOne);
        test("Alpha scaling is linear", GemmTestRunner::testAlphaScalingLinear);

        // Performance test
        test("Performance speed test", GemmTestRunner::testPerformanceSpeed);

        // Summary
        System.out.println("\n========================================");
        System.out.printf("Results: %d passed, %d failed, %d total%n", passed, failed, passed + failed);
        System.out.println("========================================");

        if (failed > 0) {
            System.exit(1);
        }
    }

    private static void test(String name, Runnable testFn) {
        try {
            testFn.run();
            System.out.println("[PASS] " + name);
            passed++;
        } catch (AssertionError e) {
            System.out.println("[FAIL] " + name);
            System.out.println("       " + e.getMessage());
            failed++;
        } catch (Exception e) {
            System.out.println("[FAIL] " + name);
            System.out.println("       Exception: " + e.getMessage());
            failed++;
        }
    }

    // ==================== Helpers ====================

    private static double[][] makeMatrix(int rows, int cols, double fill) {
        double[][] result = new double[rows][cols];
        for (int i = 0; i < rows; i++) {
            Arrays.fill(result[i], fill);
        }
        return result;
    }

    private static double[][] makeRandomMatrix(int rows, int cols, double lo, double hi, int seed) {
        Random rng = new Random(seed);
        double[][] result = new double[rows][cols];
        for (int i = 0; i < rows; i++) {
            for (int j = 0; j < cols; j++) {
                result[i][j] = lo + rng.nextDouble() * (hi - lo);
            }
        }
        return result;
    }

    private static double[][] makeIdentity(int n) {
        double[][] result = new double[n][n];
        for (int i = 0; i < n; i++) {
            result[i][i] = 1.0;
        }
        return result;
    }

    private static double[][] deepCopy(double[][] matrix) {
        double[][] result = new double[matrix.length][];
        for (int i = 0; i < matrix.length; i++) {
            result[i] = Arrays.copyOf(matrix[i], matrix[i].length);
        }
        return result;
    }

    private static void matAlmostEqual(double[][] X, double[][] Y, double tol) {
        if (X.length != Y.length) {
            throw new AssertionError("Row count mismatch: " + X.length + " vs " + Y.length);
        }
        if (X[0].length != Y[0].length) {
            throw new AssertionError("Column count mismatch: " + X[0].length + " vs " + Y[0].length);
        }
        for (int i = 0; i < X.length; i++) {
            for (int j = 0; j < X[0].length; j++) {
                double x = X[i][j], y = Y[i][j];
                if (Double.isNaN(x) || Double.isNaN(y)) {
                    if (!(Double.isNaN(x) && Double.isNaN(y))) {
                        throw new AssertionError("NaN mismatch at [" + i + "][" + j + "]: " + x + " vs " + y);
                    }
                } else if (Math.abs(x - y) > tol) {
                    throw new AssertionError("Value mismatch at [" + i + "][" + j + "]: " + x + " vs " + y + " (diff=" + Math.abs(x - y) + ")");
                }
            }
        }
    }

    private static void matAlmostEqual(double[][] X, double[][] Y) {
        matAlmostEqual(X, Y, 1e-9);
    }

    private static double[][] naiveGemm(double[][] A, double[][] B, double alpha, double[][] C, double beta) {
        int m = A.length, k = A[0].length;
        int k2 = B.length, n = B[0].length;

        if (k != k2) {
            throw new AssertionError("Dimension mismatch: A has " + k + " cols, B has " + k2 + " rows");
        }

        if (C == null) {
            C = makeMatrix(m, n, 0.0);
        } else {
            if (C.length != m || C[0].length != n) {
                throw new AssertionError("C dimensions don't match");
            }
            if (beta != 1.0) {
                for (int i = 0; i < m; i++) {
                    for (int j = 0; j < n; j++) {
                        C[i][j] *= beta;
                    }
                }
            }
        }

        if (alpha == 0.0) {
            return C;
        }

        for (int i = 0; i < m; i++) {
            for (int kk = 0; kk < k; kk++) {
                double a = alpha * A[i][kk];
                if (a == 0.0) continue;
                for (int j = 0; j < n; j++) {
                    C[i][j] += a * B[kk][j];
                }
            }
        }
        return C;
    }

    // ==================== Tests ====================

    private static void testIdentityLeft() {
        int m = 3, n = 4;
        double[][] I = makeIdentity(m);
        double[][] B = makeRandomMatrix(m, n, -1.0, 1.0, 1);
        double[][] out = Gemm.run(I, B, 1.0, null, 0.0);
        matAlmostEqual(out, B);
    }

    private static void testIdentityRight() {
        int m = 3, k = 5;
        int n = k;
        double[][] A = makeRandomMatrix(m, k, -1.0, 1.0, 2);
        double[][] I = makeIdentity(n);
        double[][] out = Gemm.run(A, I, 1.0, null, 0.0);
        matAlmostEqual(out, A);
    }

    private static void testZeroMatricesYieldZero() {
        int m = 4, k = 3, n = 5;
        double[][] A = makeMatrix(m, k, 0.0);
        double[][] B = makeMatrix(k, n, 0.0);
        double[][] out = Gemm.run(A, B, 1.0, null, 0.0);
        matAlmostEqual(out, makeMatrix(m, n, 0.0));
    }

    private static void testAlphaZeroWithCNull() {
        int m = 2, k = 3, n = 4;
        double[][] A = makeRandomMatrix(m, k, -1.0, 1.0, 3);
        double[][] B = makeRandomMatrix(k, n, -1.0, 1.0, 4);
        double[][] out = Gemm.run(A, B, 0.0, null, 0.0);
        matAlmostEqual(out, makeMatrix(m, n, 0.0));
    }

    private static void testAlphaZeroWithCBetaOnePreservesC() {
        int m = 3, k = 3, n = 2;
        double[][] A = makeRandomMatrix(m, k, -1.0, 1.0, 5);
        double[][] B = makeRandomMatrix(k, n, -1.0, 1.0, 6);
        double[][] C = makeRandomMatrix(m, n, -1.0, 1.0, 7);
        double[][] CCopy = deepCopy(C);
        double[][] out = Gemm.run(A, B, 0.0, C, 1.0);
        if (out != C) {
            throw new AssertionError("Output should be same object as C");
        }
        matAlmostEqual(out, CCopy);
    }

    private static void testAlphaZeroWithBetaScalesOnce() {
        int m = 3, k = 7, n = 4;
        double[][] A = makeRandomMatrix(m, k, -1.0, 1.0, 8);
        double[][] B = makeRandomMatrix(k, n, -1.0, 1.0, 9);
        double[][] C = makeRandomMatrix(m, n, -1.0, 1.0, 10);
        double[][] CCopy = deepCopy(C);
        double beta = 2.5;
        double[][] out = Gemm.run(A, B, 0.0, C, beta, 2, 3, 1);
        if (out != C) {
            throw new AssertionError("Output should be same object as C");
        }
        double[][] expected = makeMatrix(m, n, 0.0);
        for (int i = 0; i < m; i++) {
            for (int j = 0; j < n; j++) {
                expected[i][j] = beta * CCopy[i][j];
            }
        }
        matAlmostEqual(out, expected);
    }

    private static void testBetaZeroIgnoresInputC() {
        int m = 4, k = 3, n = 5;
        double[][] A = makeRandomMatrix(m, k, -1.0, 1.0, 11);
        double[][] B = makeRandomMatrix(k, n, -1.0, 1.0, 12);
        double[][] C = makeMatrix(m, n, 7.0);
        double[][] out = Gemm.run(A, B, 1.0, C, 0.0);
        double[][] ref = naiveGemm(A, B, 1.0, makeMatrix(m, n, 0.0), 0.0);
        matAlmostEqual(out, ref);
    }

    private static void testBetaOneAccumulatesIntoC() {
        int m = 3, k = 4, n = 2;
        double[][] A = makeRandomMatrix(m, k, -1.0, 1.0, 13);
        double[][] B = makeRandomMatrix(k, n, -1.0, 1.0, 14);
        double[][] C = makeRandomMatrix(m, n, -1.0, 1.0, 15);
        double[][] Cref = deepCopy(C);
        double[][] out = Gemm.run(A, B, 0.5, C, 1.0);
        double[][] ref = naiveGemm(A, B, 0.5, Cref, 1.0);
        matAlmostEqual(out, ref);
    }

    private static void testNegativeAlphaAndBeta() {
        int m = 2, k = 3, n = 2;
        double[][] A = makeRandomMatrix(m, k, -1.0, 1.0, 16);
        double[][] B = makeRandomMatrix(k, n, -1.0, 1.0, 17);
        double[][] C = makeRandomMatrix(m, n, -1.0, 1.0, 18);
        double[][] Cref = deepCopy(C);
        double[][] out = Gemm.run(A, B, -1.0, C, -0.5);
        double[][] ref = naiveGemm(A, B, -1.0, Cref, -0.5);
        matAlmostEqual(out, ref);
    }

    private static void testRectangularTallSkinny() {
        int m = 10, k = 2, n = 7;
        double[][] A = makeRandomMatrix(m, k, -1.0, 1.0, 19);
        double[][] B = makeRandomMatrix(k, n, -1.0, 1.0, 20);
        double[][] out = Gemm.run(A, B);
        double[][] ref = naiveGemm(A, B, 1.0, null, 0.0);
        matAlmostEqual(out, ref);
    }

    private static void testRectangularShortFat() {
        int m = 3, k = 8, n = 20;
        double[][] A = makeRandomMatrix(m, k, -1.0, 1.0, 21);
        double[][] B = makeRandomMatrix(k, n, -1.0, 1.0, 22);
        double[][] out = Gemm.run(A, B, 1.0, null, 0.0, 2, 7, 3);
        double[][] ref = naiveGemm(A, B, 1.0, null, 0.0);
        matAlmostEqual(out, ref);
    }

    private static void testSingleRowTimesSingleColumn() {
        int m = 1, k = 5, n = 1;
        double[][] A = makeRandomMatrix(m, k, -1.0, 1.0, 23);
        double[][] B = makeRandomMatrix(k, n, -1.0, 1.0, 24);
        double[][] out = Gemm.run(A, B);
        double[][] ref = naiveGemm(A, B, 1.0, null, 0.0);
        matAlmostEqual(out, ref);
    }

    private static void testRowVectorTimesMatrix() {
        int m = 1, k = 6, n = 4;
        double[][] A = makeRandomMatrix(m, k, -1.0, 1.0, 25);
        double[][] B = makeRandomMatrix(k, n, -1.0, 1.0, 26);
        double[][] out = Gemm.run(A, B, 1.0, null, 0.0, 1, 3, 2);
        double[][] ref = naiveGemm(A, B, 1.0, null, 0.0);
        matAlmostEqual(out, ref);
    }

    private static void testMatrixTimesColumnVector() {
        int m = 7, k = 5, n = 1;
        double[][] A = makeRandomMatrix(m, k, -1.0, 1.0, 27);
        double[][] B = makeRandomMatrix(k, n, -1.0, 1.0, 28);
        double[][] out = Gemm.run(A, B, 1.0, null, 0.0, 4, 1, 3);
        double[][] ref = naiveGemm(A, B, 1.0, null, 0.0);
        matAlmostEqual(out, ref);
    }

    private static void testGeneralRandomCompareReference() {
        int m = 9, k = 11, n = 8;
        double[][] A = makeRandomMatrix(m, k, -1.0, 1.0, 29);
        double[][] B = makeRandomMatrix(k, n, -1.0, 1.0, 30);
        double[][] C = makeRandomMatrix(m, n, -1.0, 1.0, 31);
        double[][] out = Gemm.run(A, B, 1.2, deepCopy(C), 0.7, 4, 5, 3);
        double[][] ref = naiveGemm(A, B, 1.2, C, 0.7);
        matAlmostEqual(out, ref);
    }

    private static void testNotMultipleOfBlockSizes() {
        int m = 13, k = 17, n = 19;
        double[][] A = makeRandomMatrix(m, k, -1.0, 1.0, 32);
        double[][] B = makeRandomMatrix(k, n, -1.0, 1.0, 33);
        double[][] out = Gemm.run(A, B, 1.0, null, 0.0, 5, 6, 7);
        double[][] ref = naiveGemm(A, B, 1.0, null, 0.0);
        matAlmostEqual(out, ref);
    }

    private static void testBlockSizesOneMatchesNaive() {
        int m = 5, k = 6, n = 4;
        double[][] A = makeRandomMatrix(m, k, -1.0, 1.0, 34);
        double[][] B = makeRandomMatrix(k, n, -1.0, 1.0, 35);
        double[][] out = Gemm.run(A, B, 1.0, null, 0.0, 1, 1, 1);
        double[][] ref = naiveGemm(A, B, 1.0, null, 0.0);
        matAlmostEqual(out, ref);
    }

    private static void testBlockSizesLargerThanDims() {
        int m = 4, k = 3, n = 2;
        double[][] A = makeRandomMatrix(m, k, -1.0, 1.0, 36);
        double[][] B = makeRandomMatrix(k, n, -1.0, 1.0, 37);
        double[][] out = Gemm.run(A, B, 1.0, null, 0.0, 128, 128, 128);
        double[][] ref = naiveGemm(A, B, 1.0, null, 0.0);
        matAlmostEqual(out, ref);
    }

    private static void testInPlaceCObjectIdentity() {
        int m = 3, k = 3, n = 3;
        double[][] A = makeRandomMatrix(m, k, -1.0, 1.0, 38);
        double[][] B = makeRandomMatrix(k, n, -1.0, 1.0, 39);
        double[][] C = makeRandomMatrix(m, n, -1.0, 1.0, 40);
        double[][] out = Gemm.run(A, B, 0.3, C, 0.4);
        if (out != C) {
            throw new AssertionError("Output should be same object as C (mutated in place)");
        }
    }

    private static void testCCreatedWhenNull() {
        int m = 2, k = 3, n = 2;
        double[][] A = makeRandomMatrix(m, k, -1.0, 1.0, 41);
        double[][] B = makeRandomMatrix(k, n, -1.0, 1.0, 42);
        double[][] out = Gemm.run(A, B);
        if (out == A || out == B) {
            throw new AssertionError("Output should be a new object");
        }
        if (out.length != m || out[0].length != n) {
            throw new AssertionError("Wrong dimensions: " + out.length + "x" + out[0].length + ", expected " + m + "x" + n);
        }
    }

    private static void testDimensionMismatchRaises() {
        double[][] A = makeRandomMatrix(3, 4, -1.0, 1.0, 43);
        double[][] B = makeRandomMatrix(5, 2, -1.0, 1.0, 44);
        try {
            Gemm.run(A, B);
            throw new AssertionError("Expected IllegalArgumentException");
        } catch (IllegalArgumentException e) {
            // expected
        }
    }

    private static void testInvalidCShapeRaises() {
        double[][] A = makeRandomMatrix(3, 2, -1.0, 1.0, 45);
        double[][] B = makeRandomMatrix(2, 4, -1.0, 1.0, 46);
        double[][] C = makeRandomMatrix(2, 4, -1.0, 1.0, 47);
        try {
            Gemm.run(A, B, 1.0, C, 0.0);
            throw new AssertionError("Expected IllegalArgumentException");
        } catch (IllegalArgumentException e) {
            // expected
        }
    }

    private static void testRaggedARejected() {
        double[][] A = new double[][]{{1.0, 2.0}, {3.0}};
        double[][] B = makeRandomMatrix(2, 2, -1.0, 1.0, 48);
        try {
            Gemm.run(A, B);
            throw new AssertionError("Expected IllegalArgumentException");
        } catch (IllegalArgumentException e) {
            // expected
        }
    }

    private static void testRaggedBRejected() {
        double[][] A = makeRandomMatrix(2, 2, -1.0, 1.0, 49);
        double[][] B = new double[][]{{1.0}, {2.0, 3.0}};
        try {
            Gemm.run(A, B);
            throw new AssertionError("Expected IllegalArgumentException");
        } catch (IllegalArgumentException e) {
            // expected
        }
    }

    private static void testNaNPropagation() {
        double[][] A = new double[][]{{Double.NaN, 1.0}, {2.0, 3.0}};
        double[][] B = new double[][]{{4.0, 5.0}, {6.0, 7.0}};
        double[][] out = Gemm.run(A, B);
        if (!Double.isNaN(out[0][0]) || !Double.isNaN(out[0][1])) {
            throw new AssertionError("NaN should propagate");
        }
    }

    private static void testInfinityPropagation() {
        double[][] A = new double[][]{{Double.POSITIVE_INFINITY, 0.0}, {0.0, 1.0}};
        double[][] B = new double[][]{{1.0, 2.0}, {3.0, 4.0}};
        double[][] out = Gemm.run(A, B);
        if (!Double.isInfinite(out[0][0]) || !Double.isInfinite(out[0][1])) {
            throw new AssertionError("Infinity should propagate");
        }
    }

    private static void testRepeatCallsAccumulateWithBetaOne() {
        int m = 3, k = 3, n = 3;
        double[][] A = makeRandomMatrix(m, k, -1.0, 1.0, 51);
        double[][] B = makeRandomMatrix(k, n, -1.0, 1.0, 52);
        double[][] C = makeMatrix(m, n, 0.0);
        Gemm.run(A, B, 1.0, C, 1.0);
        Gemm.run(A, B, 1.0, C, 1.0);
        double[][] refOnce = naiveGemm(A, B, 1.0, makeMatrix(m, n, 0.0), 1.0);
        double[][] refTwice = naiveGemm(A, B, 1.0, refOnce, 1.0);
        matAlmostEqual(C, refTwice);
    }

    private static void testAlphaScalingLinear() {
        int m = 4, k = 5, n = 3;
        double[][] A = makeRandomMatrix(m, k, -1.0, 1.0, 53);
        double[][] B = makeRandomMatrix(k, n, -1.0, 1.0, 54);
        double[][] C1 = Gemm.run(A, B, 1.0, null, 0.0);
        double s = 2.75;
        double[][] C2 = Gemm.run(A, B, s, null, 0.0);
        double[][] scaled = makeMatrix(m, n, 0.0);
        for (int i = 0; i < m; i++) {
            for (int j = 0; j < n; j++) {
                scaled[i][j] = s * C1[i][j];
            }
        }
        matAlmostEqual(C2, scaled);
    }

    private static void testPerformanceSpeed() {
        int m = 512, k = 512, n = 512;
        double[][] A = makeRandomMatrix(m, k, -1.0, 1.0, 10);
        double[][] B = makeRandomMatrix(k, n, -1.0, 1.0, 12);

        // Warmup
        Gemm.run(A, B, 1.0, null, 0.0, 32, 32, 128);

        int iters = 5;
        int reps = 3;
        double[] times = new double[reps];

        for (int r = 0; r < reps; r++) {
            long startTime = System.nanoTime();
            for (int i = 0; i < iters; i++) {
                Gemm.run(A, B, 1.0, null, 0.0, 32, 32, 128);
            }
            long endTime = System.nanoTime();
            times[r] = (endTime - startTime) / 1_000_000.0 / iters;
        }

        double avg = 0;
        for (double t : times) avg += t;
        avg /= times.length;

        double variance = 0;
        for (double t : times) variance += (t - avg) * (t - avg);
        double sd = Math.sqrt(variance / times.length);

        double avgS = avg / 1000.0;
        double gflops = (2.0 * m * n * k) / (avgS * 1e9);

        System.out.printf("       (GEMM %dx%dx%d: %.2f ms/run +/- %.2f, %.3f GFLOPs)%n", m, n, k, avg, sd, gflops);
    }
}
