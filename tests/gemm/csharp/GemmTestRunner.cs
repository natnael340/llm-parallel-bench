using System.Diagnostics;

namespace GemmBenchmark;

public static class GemmTestRunner
{
    private static int _passed = 0;
    private static int _failed = 0;

    public static void Main(string[] args)
    {
        Console.WriteLine("Running GEMM Tests...\n");

        // Identity and basic tests
        Test("Identity left multiplication", TestIdentityLeft);
        Test("Identity right multiplication", TestIdentityRight);
        Test("Zero matrices yield zero", TestZeroMatricesYieldZero);

        // Alpha/Beta parameter tests
        Test("Alpha zero with C=null", TestAlphaZeroWithCNull);
        Test("Alpha zero with C, beta=1 preserves C", TestAlphaZeroWithCBetaOnePreservesC);
        Test("Alpha zero with beta scales once", TestAlphaZeroWithBetaScalesOnce);
        Test("Beta zero ignores input C", TestBetaZeroIgnoresInputC);
        Test("Beta one accumulates into C", TestBetaOneAccumulatesIntoC);
        Test("Negative alpha and beta", TestNegativeAlphaAndBeta);

        // Shape tests
        Test("Rectangular tall skinny", TestRectangularTallSkinny);
        Test("Rectangular short fat", TestRectangularShortFat);
        Test("Single row times single column (scalar)", TestSingleRowTimesSingleColumn);
        Test("Row vector times matrix", TestRowVectorTimesMatrix);
        Test("Matrix times column vector", TestMatrixTimesColumnVector);

        // General correctness tests
        Test("General random compare reference", TestGeneralRandomCompareReference);
        Test("Not multiple of block sizes", TestNotMultipleOfBlockSizes);
        Test("Block sizes one matches naive", TestBlockSizesOneMatchesNaive);
        Test("Block sizes larger than dims", TestBlockSizesLargerThanDims);

        // Object identity and mutation tests
        Test("In-place C object identity", TestInPlaceCObjectIdentity);
        Test("C created when null", TestCCreatedWhenNull);

        // Validation tests
        Test("Dimension mismatch raises", TestDimensionMismatchRaises);
        Test("Invalid C shape raises", TestInvalidCShapeRaises);
        Test("Ragged A rejected", TestRaggedARejected);
        Test("Ragged B rejected", TestRaggedBRejected);

        // Special values
        Test("NaN propagation", TestNaNPropagation);
        Test("Infinity propagation", TestInfinityPropagation);

        // Accumulation tests
        Test("Repeat calls accumulate with beta=1", TestRepeatCallsAccumulateWithBetaOne);
        Test("Alpha scaling is linear", TestAlphaScalingLinear);

        // Summary
        Console.WriteLine("\n========================================");
        Console.WriteLine($"Results: {_passed} passed, {_failed} failed, {_passed + _failed} total");
        Console.WriteLine("========================================");

        if (_failed > 0)
        {
            Console.WriteLine($"{_failed} test(s) failed — skipping benchmark");
            Environment.Exit(1);
        }

        TestPerformanceSpeed();
    }

    private static void Test(string name, Action testFn)
    {
        try
        {
            testFn();
            Console.WriteLine($"[PASS] {name}");
            _passed++;
        }
        catch (Exception e)
        {
            Console.WriteLine($"[FAIL] {name}");
            Console.WriteLine($"       {e.Message}");
            _failed++;
        }
    }

    // ==================== Helpers ====================

    private static double[][] MakeMatrix(int rows, int cols, double fill = 0.0)
    {
        var result = new double[rows][];
        for (int i = 0; i < rows; i++)
        {
            result[i] = new double[cols];
            for (int j = 0; j < cols; j++)
                result[i][j] = fill;
        }
        return result;
    }

    private static double[][] MakeRandomMatrix(int rows, int cols, double lo = -1.0, double hi = 1.0, int seed = 0)
    {
        var rng = new Random(seed);
        var result = new double[rows][];
        for (int i = 0; i < rows; i++)
        {
            result[i] = new double[cols];
            for (int j = 0; j < cols; j++)
                result[i][j] = lo + rng.NextDouble() * (hi - lo);
        }
        return result;
    }

    private static double[][] MakeIdentity(int n)
    {
        var result = MakeMatrix(n, n, 0.0);
        for (int i = 0; i < n; i++)
            result[i][i] = 1.0;
        return result;
    }

    private static double[][] DeepCopy(double[][] matrix)
    {
        var result = new double[matrix.Length][];
        for (int i = 0; i < matrix.Length; i++)
        {
            result[i] = new double[matrix[i].Length];
            Array.Copy(matrix[i], result[i], matrix[i].Length);
        }
        return result;
    }

    private static void MatAlmostEqual(double[][] X, double[][] Y, double tol = 1e-9)
    {
        if (X.Length != Y.Length)
            throw new Exception($"Row count mismatch: {X.Length} vs {Y.Length}");
        if (X[0].Length != Y[0].Length)
            throw new Exception($"Column count mismatch: {X[0].Length} vs {Y[0].Length}");

        for (int i = 0; i < X.Length; i++)
        {
            for (int j = 0; j < X[0].Length; j++)
            {
                double x = X[i][j], y = Y[i][j];
                if (double.IsNaN(x) || double.IsNaN(y))
                {
                    if (!(double.IsNaN(x) && double.IsNaN(y)))
                        throw new Exception($"NaN mismatch at [{i}][{j}]: {x} vs {y}");
                }
                else if (Math.Abs(x - y) > tol)
                {
                    throw new Exception($"Value mismatch at [{i}][{j}]: {x} vs {y} (diff={Math.Abs(x - y)})");
                }
            }
        }
    }

    private static double[][] NaiveGemm(double[][] A, double[][] B, double alpha = 1.0, double[][]? C = null, double beta = 0.0)
    {
        int m = A.Length, k = A[0].Length;
        int k2 = B.Length, n = B[0].Length;

        if (k != k2)
            throw new Exception($"Dimension mismatch: A has {k} cols, B has {k2} rows");

        if (C == null)
        {
            C = MakeMatrix(m, n, 0.0);
        }
        else
        {
            if (C.Length != m || C[0].Length != n)
                throw new Exception("C dimensions don't match");
            if (beta != 1.0)
            {
                for (int i = 0; i < m; i++)
                    for (int j = 0; j < n; j++)
                        C[i][j] *= beta;
            }
        }

        if (alpha == 0.0)
            return C;

        for (int i = 0; i < m; i++)
        {
            for (int kk = 0; kk < k; kk++)
            {
                double a = alpha * A[i][kk];
                if (a == 0.0) continue;
                for (int j = 0; j < n; j++)
                {
                    C[i][j] += a * B[kk][j];
                }
            }
        }
        return C;
    }

    // ==================== Tests ====================

    private static void TestIdentityLeft()
    {
        int m = 3, n = 4;
        var I = MakeIdentity(m);
        var B = MakeRandomMatrix(m, n, seed: 1);
        var outM = BenchImpl.Run(I, B, alpha: 1.0, C: null, beta: 0.0);
        MatAlmostEqual(outM, B);
    }

    private static void TestIdentityRight()
    {
        int m = 3, k = 5;
        int n = k;
        var A = MakeRandomMatrix(m, k, seed: 2);
        var I = MakeIdentity(n);
        var outM = BenchImpl.Run(A, I, alpha: 1.0, C: null, beta: 0.0);
        MatAlmostEqual(outM, A);
    }

    private static void TestZeroMatricesYieldZero()
    {
        int m = 4, k = 3, n = 5;
        var A = MakeMatrix(m, k, 0.0);
        var B = MakeMatrix(k, n, 0.0);
        var outM = BenchImpl.Run(A, B, alpha: 1.0, C: null, beta: 0.0);
        MatAlmostEqual(outM, MakeMatrix(m, n, 0.0));
    }

    private static void TestAlphaZeroWithCNull()
    {
        int m = 2, k = 3, n = 4;
        var A = MakeRandomMatrix(m, k, seed: 3);
        var B = MakeRandomMatrix(k, n, seed: 4);
        var outM = BenchImpl.Run(A, B, alpha: 0.0, C: null, beta: 0.0);
        MatAlmostEqual(outM, MakeMatrix(m, n, 0.0));
    }

    private static void TestAlphaZeroWithCBetaOnePreservesC()
    {
        int m = 3, k = 3, n = 2;
        var A = MakeRandomMatrix(m, k, seed: 5);
        var B = MakeRandomMatrix(k, n, seed: 6);
        var C = MakeRandomMatrix(m, n, seed: 7);
        var CCopy = DeepCopy(C);
        var outM = BenchImpl.Run(A, B, alpha: 0.0, C: C, beta: 1.0);
        if (!ReferenceEquals(outM, C))
            throw new Exception("Output should be same object as C");
        MatAlmostEqual(outM, CCopy);
    }

    private static void TestAlphaZeroWithBetaScalesOnce()
    {
        int m = 3, k = 7, n = 4;
        var A = MakeRandomMatrix(m, k, seed: 8);
        var B = MakeRandomMatrix(k, n, seed: 9);
        var C = MakeRandomMatrix(m, n, seed: 10);
        var CCopy = DeepCopy(C);
        double beta = 2.5;
        var outM = BenchImpl.Run(A, B, alpha: 0.0, C: C, beta: beta, MB: 2, NB: 3, KB: 1);
        if (!ReferenceEquals(outM, C))
            throw new Exception("Output should be same object as C");
        var expected = MakeMatrix(m, n);
        for (int i = 0; i < m; i++)
            for (int j = 0; j < n; j++)
                expected[i][j] = beta * CCopy[i][j];
        MatAlmostEqual(outM, expected);
    }

    private static void TestBetaZeroIgnoresInputC()
    {
        int m = 4, k = 3, n = 5;
        var A = MakeRandomMatrix(m, k, seed: 11);
        var B = MakeRandomMatrix(k, n, seed: 12);
        var C = MakeMatrix(m, n, 7.0);
        var outM = BenchImpl.Run(A, B, alpha: 1.0, C: C, beta: 0.0);
        var refM = NaiveGemm(A, B, alpha: 1.0, C: MakeMatrix(m, n, 0.0), beta: 0.0);
        MatAlmostEqual(outM, refM);
    }

    private static void TestBetaOneAccumulatesIntoC()
    {
        int m = 3, k = 4, n = 2;
        var A = MakeRandomMatrix(m, k, seed: 13);
        var B = MakeRandomMatrix(k, n, seed: 14);
        var C = MakeRandomMatrix(m, n, seed: 15);
        var Cref = DeepCopy(C);
        var outM = BenchImpl.Run(A, B, alpha: 0.5, C: C, beta: 1.0);
        var refM = NaiveGemm(A, B, alpha: 0.5, C: Cref, beta: 1.0);
        MatAlmostEqual(outM, refM);
    }

    private static void TestNegativeAlphaAndBeta()
    {
        int m = 2, k = 3, n = 2;
        var A = MakeRandomMatrix(m, k, seed: 16);
        var B = MakeRandomMatrix(k, n, seed: 17);
        var C = MakeRandomMatrix(m, n, seed: 18);
        var Cref = DeepCopy(C);
        var outM = BenchImpl.Run(A, B, alpha: -1.0, C: C, beta: -0.5);
        var refM = NaiveGemm(A, B, alpha: -1.0, C: Cref, beta: -0.5);
        MatAlmostEqual(outM, refM);
    }

    private static void TestRectangularTallSkinny()
    {
        int m = 10, k = 2, n = 7;
        var A = MakeRandomMatrix(m, k, seed: 19);
        var B = MakeRandomMatrix(k, n, seed: 20);
        var outM = BenchImpl.Run(A, B);
        var refM = NaiveGemm(A, B);
        MatAlmostEqual(outM, refM);
    }

    private static void TestRectangularShortFat()
    {
        int m = 3, k = 8, n = 20;
        var A = MakeRandomMatrix(m, k, seed: 21);
        var B = MakeRandomMatrix(k, n, seed: 22);
        var outM = BenchImpl.Run(A, B, MB: 2, NB: 7, KB: 3);
        var refM = NaiveGemm(A, B);
        MatAlmostEqual(outM, refM);
    }

    private static void TestSingleRowTimesSingleColumn()
    {
        int m = 1, k = 5, n = 1;
        var A = MakeRandomMatrix(m, k, seed: 23);
        var B = MakeRandomMatrix(k, n, seed: 24);
        var outM = BenchImpl.Run(A, B);
        var refM = NaiveGemm(A, B);
        MatAlmostEqual(outM, refM);
    }

    private static void TestRowVectorTimesMatrix()
    {
        int m = 1, k = 6, n = 4;
        var A = MakeRandomMatrix(m, k, seed: 25);
        var B = MakeRandomMatrix(k, n, seed: 26);
        var outM = BenchImpl.Run(A, B, MB: 1, NB: 3, KB: 2);
        var refM = NaiveGemm(A, B);
        MatAlmostEqual(outM, refM);
    }

    private static void TestMatrixTimesColumnVector()
    {
        int m = 7, k = 5, n = 1;
        var A = MakeRandomMatrix(m, k, seed: 27);
        var B = MakeRandomMatrix(k, n, seed: 28);
        var outM = BenchImpl.Run(A, B, MB: 4, NB: 1, KB: 3);
        var refM = NaiveGemm(A, B);
        MatAlmostEqual(outM, refM);
    }

    private static void TestGeneralRandomCompareReference()
    {
        int m = 9, k = 11, n = 8;
        var A = MakeRandomMatrix(m, k, seed: 29);
        var B = MakeRandomMatrix(k, n, seed: 30);
        var C = MakeRandomMatrix(m, n, seed: 31);
        var outM = BenchImpl.Run(A, B, alpha: 1.2, C: DeepCopy(C), beta: 0.7, MB: 4, NB: 5, KB: 3);
        var refM = NaiveGemm(A, B, alpha: 1.2, C: C, beta: 0.7);
        MatAlmostEqual(outM, refM);
    }

    private static void TestNotMultipleOfBlockSizes()
    {
        int m = 13, k = 17, n = 19;
        var A = MakeRandomMatrix(m, k, seed: 32);
        var B = MakeRandomMatrix(k, n, seed: 33);
        var outM = BenchImpl.Run(A, B, MB: 5, NB: 6, KB: 7);
        var refM = NaiveGemm(A, B);
        MatAlmostEqual(outM, refM);
    }

    private static void TestBlockSizesOneMatchesNaive()
    {
        int m = 5, k = 6, n = 4;
        var A = MakeRandomMatrix(m, k, seed: 34);
        var B = MakeRandomMatrix(k, n, seed: 35);
        var outM = BenchImpl.Run(A, B, MB: 1, NB: 1, KB: 1);
        var refM = NaiveGemm(A, B);
        MatAlmostEqual(outM, refM);
    }

    private static void TestBlockSizesLargerThanDims()
    {
        int m = 4, k = 3, n = 2;
        var A = MakeRandomMatrix(m, k, seed: 36);
        var B = MakeRandomMatrix(k, n, seed: 37);
        var outM = BenchImpl.Run(A, B, MB: 128, NB: 128, KB: 128);
        var refM = NaiveGemm(A, B);
        MatAlmostEqual(outM, refM);
    }

    private static void TestInPlaceCObjectIdentity()
    {
        int m = 3, k = 3, n = 3;
        var A = MakeRandomMatrix(m, k, seed: 38);
        var B = MakeRandomMatrix(k, n, seed: 39);
        var C = MakeRandomMatrix(m, n, seed: 40);
        var outM = BenchImpl.Run(A, B, alpha: 0.3, C: C, beta: 0.4);
        if (!ReferenceEquals(outM, C))
            throw new Exception("Output should be same object as C (mutated in place)");
    }

    private static void TestCCreatedWhenNull()
    {
        int m = 2, k = 3, n = 2;
        var A = MakeRandomMatrix(m, k, seed: 41);
        var B = MakeRandomMatrix(k, n, seed: 42);
        var outM = BenchImpl.Run(A, B);
        if (ReferenceEquals(outM, A) || ReferenceEquals(outM, B))
            throw new Exception("Output should be a new object");
        if (outM.Length != m || outM[0].Length != n)
            throw new Exception($"Wrong dimensions: {outM.Length}x{outM[0].Length}, expected {m}x{n}");
    }

    private static void TestDimensionMismatchRaises()
    {
        var A = MakeRandomMatrix(3, 4, seed: 43);
        var B = MakeRandomMatrix(5, 2, seed: 44);
        try
        {
            BenchImpl.Run(A, B);
            throw new Exception("Expected ArgumentException");
        }
        catch (ArgumentException) { }
    }

    private static void TestInvalidCShapeRaises()
    {
        var A = MakeRandomMatrix(3, 2, seed: 45);
        var B = MakeRandomMatrix(2, 4, seed: 46);
        var C = MakeRandomMatrix(2, 4, seed: 47);
        try
        {
            BenchImpl.Run(A, B, C: C);
            throw new Exception("Expected ArgumentException");
        }
        catch (ArgumentException) { }
    }

    private static void TestRaggedARejected()
    {
        var A = new double[][] { new double[] { 1.0, 2.0 }, new double[] { 3.0 } };
        var B = MakeRandomMatrix(2, 2, seed: 48);
        try
        {
            BenchImpl.Run(A, B);
            throw new Exception("Expected ArgumentException");
        }
        catch (ArgumentException) { }
    }

    private static void TestRaggedBRejected()
    {
        var A = MakeRandomMatrix(2, 2, seed: 49);
        var B = new double[][] { new double[] { 1.0 }, new double[] { 2.0, 3.0 } };
        try
        {
            BenchImpl.Run(A, B);
            throw new Exception("Expected ArgumentException");
        }
        catch (ArgumentException) { }
    }

    private static void TestNaNPropagation()
    {
        var A = new double[][] { new double[] { double.NaN, 1.0 }, new double[] { 2.0, 3.0 } };
        var B = new double[][] { new double[] { 4.0, 5.0 }, new double[] { 6.0, 7.0 } };
        var outM = BenchImpl.Run(A, B);
        if (!double.IsNaN(outM[0][0]) || !double.IsNaN(outM[0][1]))
            throw new Exception("NaN should propagate");
    }

    private static void TestInfinityPropagation()
    {
        var A = new double[][] { new double[] { double.PositiveInfinity, 0.0 }, new double[] { 0.0, 1.0 } };
        var B = new double[][] { new double[] { 1.0, 2.0 }, new double[] { 3.0, 4.0 } };
        var outM = BenchImpl.Run(A, B);
        if (!double.IsInfinity(outM[0][0]) || !double.IsInfinity(outM[0][1]))
            throw new Exception("Infinity should propagate");
    }

    private static void TestRepeatCallsAccumulateWithBetaOne()
    {
        int m = 3, k = 3, n = 3;
        var A = MakeRandomMatrix(m, k, seed: 51);
        var B = MakeRandomMatrix(k, n, seed: 52);
        var C = MakeMatrix(m, n, 0.0);
        BenchImpl.Run(A, B, alpha: 1.0, C: C, beta: 1.0);
        BenchImpl.Run(A, B, alpha: 1.0, C: C, beta: 1.0);
        var refOnce = NaiveGemm(A, B, alpha: 1.0, C: MakeMatrix(m, n, 0.0), beta: 1.0);
        var refTwice = NaiveGemm(A, B, alpha: 1.0, C: refOnce, beta: 1.0);
        MatAlmostEqual(C, refTwice);
    }

    private static void TestAlphaScalingLinear()
    {
        int m = 4, k = 5, n = 3;
        var A = MakeRandomMatrix(m, k, seed: 53);
        var B = MakeRandomMatrix(k, n, seed: 54);
        var C1 = BenchImpl.Run(A, B, alpha: 1.0, C: null, beta: 0.0);
        double s = 2.75;
        var C2 = BenchImpl.Run(A, B, alpha: s, C: null, beta: 0.0);
        var scaled = MakeMatrix(m, n);
        for (int i = 0; i < m; i++)
            for (int j = 0; j < n; j++)
                scaled[i][j] = s * C1[i][j];
        MatAlmostEqual(C2, scaled);
    }

    private static void TestPerformanceSpeed()
    {
        int m = 1024, k = 1024, n = 1024;
        // Per-language sweep-tuned tile sizes (see analysis/data/gemm sweep CSVs).
        const int MB = 32, NB = 32, KB = 128;
        var A = MakeRandomMatrix(m, k, seed: 10);
        var B = MakeRandomMatrix(k, n, seed: 12);

        int reps = Bench.Reps(5);
        int iters = Bench.Iters(5);

        var r = Bench.Run(() => BenchImpl.Run(A, B, alpha: 1.0, C: null, beta: 0.0, MB: MB, NB: NB, KB: KB),
                          reps, iters, 1);

        double gflops = (2.0 * m * n * k) / ((r.Mean / 1000.0) * 1e9);
        string label = $"GEMM {m}x{n}x{k} ({gflops:F3} GFLOPs) [iters={iters}, repeats={reps}]";
        Console.WriteLine(Bench.Format(label, r));

        var params_ = new Dictionary<string, object>
        {
            ["m"] = m, ["n"] = n, ["k"] = k, ["MB"] = MB, ["NB"] = NB, ["KB"] = KB,
        };
        Bench.WriteResult(Bench.Out(), r, "gemm", Bench.Impl(), params_);
    }
}
