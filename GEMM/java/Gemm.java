public class Gemm {

    public static int[] getSize(double[][] matrix) {
        return new int[]{matrix.length, matrix[0].length};
    }

    public static void validateMatrix(double[][] matrix, String name) {
        if (matrix == null || matrix.length == 0) {
            throw new IllegalArgumentException(name + " must be a non-empty array of rows.");
        }
        if (matrix[0] == null || matrix[0].length == 0) {
            throw new IllegalArgumentException(name + " must have at least one column.");
        }
        int cols = matrix[0].length;
        for (int r = 0; r < matrix.length; r++) {
            if (matrix[r] == null) {
                throw new IllegalArgumentException(name + " row " + r + " is null.");
            }
            if (matrix[r].length != cols) {
                throw new IllegalArgumentException(name + " is ragged: row " + r + " has " +
                    matrix[r].length + " cols, expected " + cols + ".");
            }
        }
    }

    public static double[][] zeros(int rows, int cols) {
        return new double[rows][cols];
    }

    public static double[][] transpose(double[][] matrix) {
        int rows = matrix.length;
        int cols = matrix[0].length;
        double[][] result = new double[cols][rows];
        for (int j = 0; j < cols; j++) {
            for (int i = 0; i < rows; i++) {
                result[j][i] = matrix[i][j];
            }
        }
        return result;
    }

    public static double[][] packMatrix(double[][] matrix, int a0, int a1, int b0, int b1) {
        int rows = b1 - b0;
        int len = a1 - a0;
        double[][] result = new double[rows][len];
        for (int i = 0; i < rows; i++) {
            System.arraycopy(matrix[b0 + i], a0, result[i], 0, len);
        }
        return result;
    }

    private static void partialMatmul(
            double[][] A,
            double[][] B,
            double[][] C,
            double alpha,
            int m0,
            int n0,
            int kb) {
        for (int iOff = 0; iOff < A.length; iOff++) {
            double[] Aik = A[iOff];
            double[] Ci = C[m0 + iOff];

            for (int jOff = 0; jOff < B.length; jOff++) {
                double[] Bjk = B[jOff];
                double s = 0.0;

                for (int k = 0; k < kb; k++) {
                    s += Aik[k] * Bjk[k];
                }

                Ci[n0 + jOff] += alpha * s;
            }
        }
    }

    /**
     * Compute C := alpha * A * B + beta * C
     *
     * @param A     m x k matrix
     * @param B     k x n matrix
     * @param alpha Multiplier for A*B
     * @param C     Optional m x n accumulation buffer (created if null)
     * @param beta  Multiplier for existing C (applied only if C is provided)
     * @param MB    Tile size for M dimension
     * @param NB    Tile size for N dimension
     * @param KB    Tile size for K dimension
     * @return m x n result matrix (C)
     */
    public static double[][] run(
            double[][] A,
            double[][] B,
            double alpha,
            double[][] C,
            double beta,
            int MB,
            int NB,
            int KB) {
        validateMatrix(A, "A");
        validateMatrix(B, "B");

        int[] sizeA = getSize(A);
        int m = sizeA[0], k = sizeA[1];
        int[] sizeB = getSize(B);
        int k2 = sizeB[0], n = sizeB[1];

        if (k != k2) {
            throw new IllegalArgumentException("Shape mismatch: A is (" + m + "," + k + "), B is (" + k2 + "," + n + ").");
        }

        if (C == null) {
            C = zeros(m, n);
        } else {
            validateMatrix(C, "C");
            int[] sizeC = getSize(C);
            int m2 = sizeC[0], n2 = sizeC[1];
            if (m2 != m || n2 != n) {
                throw new IllegalArgumentException("C has shape (" + m2 + "," + n2 + "); expected (" + m + "," + n + ").");
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

        double[][] Bt = transpose(B);

        for (int n0 = 0; n0 < n; n0 += NB) {
            int n1 = Math.min(n0 + NB, n);

            for (int k0 = 0; k0 < k; k0 += KB) {
                int k1 = Math.min(k0 + KB, k);
                double[][] Bpack = packMatrix(Bt, k0, k1, n0, n1);

                for (int m0 = 0; m0 < m; m0 += MB) {
                    int m1 = Math.min(m0 + MB, m);
                    double[][] Apack = packMatrix(A, k0, k1, m0, m1);

                    int kb = k1 - k0;
                    partialMatmul(Apack, Bpack, C, alpha, m0, n0, kb);
                }
            }
        }

        return C;
    }

    // Convenience overloads
    public static double[][] run(double[][] A, double[][] B) {
        return run(A, B, 1.0, null, 0.0, 64, 64, 64);
    }

    public static double[][] run(double[][] A, double[][] B, double alpha) {
        return run(A, B, alpha, null, 0.0, 64, 64, 64);
    }

    public static double[][] run(double[][] A, double[][] B, double alpha, double[][] C, double beta) {
        return run(A, B, alpha, C, beta, 64, 64, 64);
    }
}
