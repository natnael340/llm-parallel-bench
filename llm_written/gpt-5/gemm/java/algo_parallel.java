import java.util.*;
import java.util.concurrent.*;

public class algo_parallel {
    // Utility methods (copied/adapted from baseline to keep API local)
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

    private static int clampPositive(int v, int def) {
        return v > 0 ? v : def;
    }

    /**
     * Compute C := alpha * A * B + beta * C
     * Parallel version with bounded worker pool and deterministic tiling.
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

        // Small-N fallback to baseline order to avoid thread overhead
        long work = (long) m * (long) n * (long) k;
        final long SEQ_THRESHOLD = 500_000L; // tuned for overhead break-even
        if (work <= SEQ_THRESHOLD) {
            return GemmBaseline.run(A, B, alpha, C, 1.0 /* beta already applied above if needed */, MB, NB, KB);
        }

        // Bound tile sizes to sane minimums
        MB = clampPositive(MB, 64);
        NB = clampPositive(NB, 64);
        KB = clampPositive(KB, 64);

        final double[][] Bt = transpose(B);

        final int nBlocks = (n + NB - 1) / NB;
        final int mBlocks = (m + MB - 1) / MB;
        final int kBlocks = (k + KB - 1) / KB;

        // Pre-pack B tiles by (n-block, k-block). Shared read-only across tasks.
        final double[][][][] Bpacks = new double[nBlocks][][][]; // [nb][kb][rows=NB'][cols=KB']
        for (int nbIdx = 0; nbIdx < nBlocks; nbIdx++) {
            int n0 = nbIdx * NB;
            int n1 = Math.min(n0 + NB, n);
            Bpacks[nbIdx] = new double[kBlocks][][];
            for (int kbIdx = 0; kbIdx < kBlocks; kbIdx++) {
                int k0b = kbIdx * KB;
                int k1b = Math.min(k0b + KB, k);
                Bpacks[nbIdx][kbIdx] = packMatrix(Bt, k0b, k1b, n0, n1);
            }
        }

        // Fixed worker count
        int cores = Runtime.getRuntime().availableProcessors();
        int maxWorkers = Math.max(1, cores);
        ExecutorService pool = Executors.newFixedThreadPool(maxWorkers);

        List<Callable<Void>> tasks = new ArrayList<>(mBlocks * nBlocks);

        // Deterministic task creation order: nb major, then mb
        for (int nbIdx = 0; nbIdx < nBlocks; nbIdx++) {
            final int nbFinal = nbIdx;
            final int n0 = nbIdx * NB;
            final int n1 = Math.min(n0 + NB, n);
            for (int mbIdx = 0; mbIdx < mBlocks; mbIdx++) {
                final int m0 = mbIdx * MB;
                final int m1 = Math.min(m0 + MB, m);
                final int KBfinal = KB;
                final int kFinal = k;
                final int kBlocksFinal = kBlocks;
                final double alphaFinal = alpha;
                final double[][] CFinal = C;
                final double[][][][] BpacksFinal = Bpacks;

                tasks.add(() -> {
                    for (int kbIdx = 0; kbIdx < kBlocksFinal; kbIdx++) {
                        int k0b = kbIdx * KBfinal;
                        int k1b = Math.min(k0b + KBfinal, kFinal);
                        double[][] Bpack = BpacksFinal[nbFinal][kbIdx]; // shared read-only
                        double[][] Apack = packMatrix(A, k0b, k1b, m0, m1);
                        int kbLen = k1b - k0b;
                        partialMatmul(Apack, Bpack, CFinal, alphaFinal, m0, n0, kbLen);
                    }
                    return null;
                });
            }
        }

        try {
            List<Future<Void>> fs = pool.invokeAll(tasks);
            for (Future<Void> f : fs) {
                f.get();
            }
        } catch (InterruptedException ie) {
            Thread.currentThread().interrupt();
            throw new RuntimeException("Parallel GEMM interrupted", ie);
        } catch (ExecutionException ee) {
            throw new RuntimeException("Parallel GEMM execution failed", ee.getCause());
        } finally {
            pool.shutdown();
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
