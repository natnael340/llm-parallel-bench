import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.Arrays;
import java.util.Random;

public class RunGemm {

    private static double[][] randMat(int rows, int cols, long seed) {
        Random r = new Random(seed);
        double[][] M = new double[rows][cols];
        for (int i = 0; i < rows; i++) {
            for (int j = 0; j < cols; j++) {
                M[i][j] = r.nextDouble() - 0.5;
            }
        }
        return M;
    }

    private static String hash(double[][] M) {
        try {
            MessageDigest md = MessageDigest.getInstance("SHA-256");
            for (double[] row : M) {
                for (double v : row) {
                    long bits = Double.doubleToLongBits(v);
                    md.update(new byte[]{
                            (byte) (bits >>> 56), (byte) (bits >>> 48), (byte) (bits >>> 40), (byte) (bits >>> 32),
                            (byte) (bits >>> 24), (byte) (bits >>> 16), (byte) (bits >>> 8), (byte) bits
                    });
                }
            }
            byte[] digest = md.digest();
            StringBuilder sb = new StringBuilder();
            for (byte b : digest) sb.append(String.format("%02x", b));
            return sb.toString();
        } catch (NoSuchAlgorithmException e) {
            throw new RuntimeException(e);
        }
    }

    private static double[][] clone2D(double[][] src) {
        double[][] dst = new double[src.length][];
        for (int i = 0; i < src.length; i++) dst[i] = Arrays.copyOf(src[i], src[i].length);
        return dst;
    }

    public static void main(String[] args) {
        try {
            StringBuilder summary = new StringBuilder();
            // Edge cases
            double[][] A1 = {{1}};
            double[][] B1 = {{2}};
            double[][] Cseq1 = Gemm.runSequential(A1, B1, 1.0, null, 0.0, 2, 2, 2);
            double[][] Cpar1 = Gemm.run(A1, B1, 1.0, null, 0.0, 2, 2, 2);
            boolean pass1 = Arrays.deepEquals(Cseq1, Cpar1);
            summary.append("Edge 1x1: ").append(pass1 ? "PASS" : "FAIL").append('\n');

            // Small
            double[][] A2 = randMat(8, 5, 42);
            double[][] B2 = randMat(5, 7, 24);
            double[][] Cseq2 = Gemm.runSequential(A2, B2, 1.0, null, 0.0, 4, 4, 4);
            double[][] Cpar2 = Gemm.run(A2, B2, 1.0, null, 0.0, 4, 4, 4);
            boolean pass2 = Arrays.deepEquals(Cseq2, Cpar2);
            summary.append("Small 8x5*5x7: ").append(pass2 ? "PASS" : "FAIL").append('\n');

            // Medium
            double[][] A3 = randMat(64, 64, 1);
            double[][] B3 = randMat(64, 64, 2);
            double[][] Cseq3 = Gemm.runSequential(A3, B3, 1.0, null, 0.0, 32, 32, 32);
            double[][] Cpar3 = Gemm.run(A3, B3, 1.0, null, 0.0, 32, 32, 32);
            boolean pass3 = Arrays.deepEquals(Cseq3, Cpar3);
            summary.append("Medium 64: ").append(pass3 ? "PASS" : "FAIL").append('\n');

            // Large (determinism and perf)
            int N = 512; // perf gate threshold
            double[][] A4 = randMat(N, N, 7);
            double[][] B4 = randMat(N, N, 9);

            long t0 = System.nanoTime();
            double[][] Cseq4 = Gemm.runSequential(A4, B4, 1.0, null, 0.0, 64, 64, 64);
            long t1 = System.nanoTime();

            long tp0 = System.nanoTime();
            double[][] Cpar4a = Gemm.run(A4, B4, 1.0, null, 0.0, 64, 64, 64);
            long tp1 = System.nanoTime();
            double[][] Cpar4b = Gemm.run(A4, B4, 1.0, null, 0.0, 64, 64, 64);
            long tp2 = System.nanoTime();

            boolean pass4 = Arrays.deepEquals(Cseq4, Cpar4a);
            String h1 = hash(Cpar4a);
            String h2 = hash(Cpar4b);
            boolean det = h1.equals(h2);

            summary.append("Large ").append(N).append(": ").append(pass4 ? "PASS" : "FAIL").append('\n');
            summary.append("Determinism: ").append(det ? "PASS" : "FAIL").append(" hash1=").append(h1).append(" hash2=").append(h2).append('\n');

            double tSeqMs = (t1 - t0) / 1e6;
            double tParMs = (tp1 - tp0) / 1e6;
            double speedup = tSeqMs / tParMs;
            summary.append(String.format("Perf: N=%d seq=%.2f ms par=%.2f ms speedup=%.2fx\n", N, tSeqMs, tParMs, speedup));

            System.out.print(summary.toString());
            // write to files
            java.nio.file.Files.writeString(java.nio.file.Path.of("run_summary.txt"), summary.toString());
            java.nio.file.Files.writeString(java.nio.file.Path.of("perf.txt"), String.format("N=%d seq_ms=%.2f par_ms=%.2f speedup=%.3f\n", N, tSeqMs, tParMs, speedup));
        } catch (Exception e) {
            e.printStackTrace();
            System.exit(1);
        }
    }
}
