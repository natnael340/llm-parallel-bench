using System;
using System.Collections.Concurrent;
using System.Diagnostics;
using System.Threading.Tasks;

namespace GemmBenchmark
{
    public static class Gemm
    {
        public static (int rows, int cols) GetSize(double[][] matrix)
        {
            return (matrix.Length, matrix[0].Length);
        }

        public static void ValidateMatrix(double[][] matrix, string name = "Matrix")
        {
            if (matrix == null || matrix.Length == 0)
                throw new ArgumentException($"{name} must be a non-empty array of rows.");

            if (matrix[0] == null || matrix[0].Length == 0)
                throw new ArgumentException($"{name} must have at least one column.");

            int cols = matrix[0].Length;
            for (int r = 0; r < matrix.Length; r++)
            {
                if (matrix[r] == null)
                    throw new ArgumentException($"{name} row {r} is null.");
                if (matrix[r].Length != cols)
                    throw new ArgumentException($"{name} is ragged: row {r} has {matrix[r].Length} cols, expected {cols}.");
            }
        }

        public static double[][] Zeros(int rows, int cols)
        {
            var result = new double[rows][];
            for (int i = 0; i < rows; i++)
            {
                result[i] = new double[cols];
            }
            return result;
        }

        public static double[][] Transpose(double[][] matrix)
        {
            int rows = matrix.Length;
            int cols = matrix[0].Length;
            var result = new double[cols][];
            for (int j = 0; j < cols; j++)
            {
                result[j] = new double[rows];
                for (int i = 0; i < rows; i++)
                {
                    result[j][i] = matrix[i][j];
                }
            }
            return result;
        }

        public static double[][] PackMatrix(double[][] matrix, int a0, int a1, int b0, int b1)
        {
            int rows = b1 - b0;
            var result = new double[rows][];
            for (int i = 0; i < rows; i++)
            {
                int len = a1 - a0;
                result[i] = new double[len];
                Array.Copy(matrix[b0 + i], a0, result[i], 0, len);
            }
            return result;
        }

        private static void PartialMatmul(
            double[][] A,
            double[][] B,
            double[][] C,
            double alpha,
            int m0,
            int n0,
            int kb)
        {
            for (int iOff = 0; iOff < A.Length; iOff++)
            {
                double[] Aik = A[iOff];
                double[] Ci = C[m0 + iOff];

                for (int jOff = 0; jOff < B.Length; jOff++)
                {
                    double[] Bjk = B[jOff];
                    double s = 0.0;

                    for (int k = 0; k < kb; k++)
                    {
                        s += Aik[k] * Bjk[k];
                    }

                    Ci[n0 + jOff] += alpha * s;
                }
            }
        }

        // Sequential baseline identical to the provided code path
        public static double[][] RunSequential(
            double[][] A,
            double[][] B,
            double alpha = 1.0,
            double[][]? C = null,
            double beta = 0.0,
            int MB = 64,
            int NB = 64,
            int KB = 64)
        {
            ValidateMatrix(A, "A");
            ValidateMatrix(B, "B");

            var (m, k) = GetSize(A);
            var (k2, n) = GetSize(B);

            if (k != k2)
                throw new ArgumentException($"Shape mismatch: A is ({m},{k}), B is ({k2},{n}).");

            if (C == null)
            {
                C = Zeros(m, n);
            }
            else
            {
                ValidateMatrix(C, "C");
                var (m2, n2) = GetSize(C);
                if (m2 != m || n2 != n)
                    throw new ArgumentException($"C has shape ({m2},{n2}); expected ({m},{n}).");

                if (beta != 1.0)
                {
                    for (int i = 0; i < m; i++)
                    {
                        for (int j = 0; j < n; j++)
                        {
                            C[i][j] *= beta;
                        }
                    }
                }
            }

            if (alpha == 0.0)
                return C!;

            double[][] Bt = Transpose(B);

            for (int n0 = 0; n0 < n; n0 += NB)
            {
                int n1 = Math.Min(n0 + NB, n);

                for (int k0 = 0; k0 < k; k0 += KB)
                {
                    int k1 = Math.Min(k0 + KB, k);
                    double[][] Bpack = PackMatrix(Bt, k0, k1, n0, n1);

                    for (int m0 = 0; m0 < m; m0 += MB)
                    {
                        int m1 = Math.Min(m0 + MB, m);
                        double[][] Apack = PackMatrix(A, k0, k1, m0, m1);

                        int kb = k1 - k0;
                        PartialMatmul(Apack, Bpack, C!, alpha, m0, n0, kb);
                    }
                }
            }

            return C!;
        }

        /// <summary>
        /// Deterministic parallel GEMM: C := alpha * A * B + beta * C
        /// Strategy: For each (n0,k0) tile, we parallelize independent m-tiles. This avoids write conflicts.
        /// Combine order is fixed by the serial n0 and k0 loops.
        /// </summary>
        public static double[][] Run(
            double[][] A,
            double[][] B,
            double alpha = 1.0,
            double[][]? C = null,
            double beta = 0.0,
            int MB = 64,
            int NB = 64,
            int KB = 64,
            int? maxDegree = null,
            long smallNFlops = 1_000_000) // fallback threshold in FLOPs (~2mnk)
        {
            ValidateMatrix(A, "A");
            ValidateMatrix(B, "B");

            var (m, k) = GetSize(A);
            var (k2, n) = GetSize(B);

            if (k != k2)
                throw new ArgumentException($"Shape mismatch: A is ({m},{k}), B is ({k2},{n}).");

            if (C == null)
            {
                C = Zeros(m, n);
            }
            else
            {
                ValidateMatrix(C, "C");
                var (m2, n2) = GetSize(C);
                if (m2 != m || n2 != n)
                    throw new ArgumentException($"C has shape ({m2},{n2}); expected ({m},{n}).");

                if (beta != 1.0)
                {
                    for (int i = 0; i < m; i++)
                    {
                        for (int j = 0; j < n; j++)
                        {
                            C[i][j] *= beta;
                        }
                    }
                }
            }

            if (alpha == 0.0)
                return C!;

            // Small-N fallback to sequential to avoid overheads
            long approxFlops = (long)m * n * k;
            if (approxFlops <= smallNFlops)
            {
                return RunSequential(A, B, alpha, C, 1.0 /*beta already applied above*/, MB, NB, KB);
            }

            double[][] Bt = Transpose(B); // read-only after built

            // Fixed degree of parallelism, bounded by CPU cores
            int degree = Math.Max(1, Math.Min(Environment.ProcessorCount, maxDegree ?? Environment.ProcessorCount));
            var po = new ParallelOptions { MaxDegreeOfParallelism = degree };

            for (int n0 = 0; n0 < n; n0 += NB)
            {
                int n1 = Math.Min(n0 + NB, n);

                for (int k0 = 0; k0 < k; k0 += KB)
                {
                    int k1 = Math.Min(k0 + KB, k);
                    double[][] Bpack = PackMatrix(Bt, k0, k1, n0, n1); // shared read-only within this scope
                    int kb = k1 - k0;

                    // Parallelize across m-tiles; each worker owns disjoint row stripes of C
                    int tileCount = (m + MB - 1) / MB;
                    // Create a deterministic set of tile start indices
                    int[] mStarts = new int[tileCount];
                    for (int t = 0, s = 0; t < tileCount; t++, s += MB) mStarts[t] = s;

                    Parallel.For(0, tileCount, po, t =>
                    {
                        int m0 = mStarts[t];
                        int m1 = Math.Min(m0 + MB, m);
                        double[][] Apack = PackMatrix(A, k0, k1, m0, m1); // private to worker
                        PartialMatmul(Apack, Bpack, C!, alpha, m0, n0, kb);
                    });
                }
            }

            return C!;
        }
    }
}
