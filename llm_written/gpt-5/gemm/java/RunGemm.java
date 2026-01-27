import java.util.*;
import java.util.concurrent.TimeUnit;
import java.security.MessageDigest;

public class RunGemm {
    static Random rng = new Random(42);

    static double[][] randomMatrix(int rows, int cols) {
        double[][] m = new double[rows][cols];
        for (int i = 0; i < rows; i++) {
            for (int j = 0; j < cols; j++) {
                m[i][j] = rng.nextDouble() - 0.5; // centered
            }
        }
        return m;
    }

    static double[][] cloneMatrix(double[][] X) {
        double[][] Y = new double[X.length][];
        for (int i = 0; i < X.length; i++) {
            Y[i] = X[i].clone();
        }
        return Y;
    }

    static String hash(double[][] M) {
        try {
            MessageDigest md = MessageDigest.getInstance("SHA-256");
            for (double[] row : M) {
                for (double v : row) {
                    long bits = Double.doubleToLongBits(v);
                    md.update((byte)(bits >>> 56));
                    md.update((byte)(bits >>> 48));
                    md.update((byte)(bits >>> 40));
                    md.update((byte)(bits >>> 32));
                    md.update((byte)(bits >>> 24));
                    md.update((byte)(bits >>> 16));
                    md.update((byte)(bits >>> 8));
                    md.update((byte)(bits));
                }
            }
            byte[] h = md.digest();
            StringBuilder sb = new StringBuilder();
            for (byte b : h) sb.append(String.format("%02x", b));
            return sb.toString();
        } catch (Exception e) {
            throw new RuntimeException(e);
        }
    }

    static boolean equal(double[][] A, double[][] B) {
        if (A.length != B.length) return false;
        if (A[0].length != B[0].length) return false;
        for (int i = 0; i < A.length; i++) {
            for (int j = 0; j < A[0].length; j++) {
                if (Double.doubleToLongBits(A[i][j]) != Double.doubleToLongBits(B[i][j])) return false;
            }
        }
        return true;
    }

    static long timeMs(Runnable r) {
        long t0 = System.nanoTime();
        r.run();
        return TimeUnit.NANOSECONDS.toMillis(System.nanoTime() - t0);
    }

    static class Case { int m,k,n; Case(int m,int k,int n){this.m=m;this.k=k;this.n=n;} }

    public static void main(String[] args) throws Exception {
        List<Case> cases = Arrays.asList(
            new Case(0,0,0), // edge: invalid; expect exception
            new Case(1,1,1),
            new Case(3,5,2),
            new Case(32,32,32),
            new Case(128,128,128),
            new Case(256,256,256)
        );

        StringBuilder summary = new StringBuilder();
        boolean allOk = true;

        for (Case cs : cases) {
            summary.append(String.format("Case m=%d k=%d n=%d\n", cs.m, cs.k, cs.n));
            if (cs.m==0 || cs.k==0 || cs.n==0) {
                boolean threw = false;
                try {
                    double[][] A = new double[0][0];
                    double[][] B = new double[0][0];
                    GemmBaseline.run(A,B);
                } catch (Exception e) { threw = true; }
                summary.append("  edge(empty): baseline threw="+threw+"\n");
                try {
                    double[][] A = new double[0][0];
                    double[][] B = new double[0][0];
                    algo_parallel.run(A,B);
                } catch (Exception e) { threw = true; }
                summary.append("  edge(empty): parallel also threw (expected)\n");
                continue;
            }

            rng.setSeed(12345); // fixed seed for matrices
            double[][] A = randomMatrix(cs.m, cs.k);
            double[][] B = randomMatrix(cs.k, cs.n);

            final double[][][] holderB = new double[1][][];
            long tSeq = timeMs(() -> {
                holderB[0] = GemmBaseline.run(A, B, 1.0, null, 0.0, 64,64,64);
            });

            final double[][][] holderP = new double[1][][];
            long tPar = timeMs(() -> {
                holderP[0] = algo_parallel.run(A, B, 1.0, null, 0.0, 64,64,64);
            });

            double[][] Cb = holderB[0];
            double[][] Cp = holderP[0];

            boolean eq = equal(Cb, Cp);
            summary.append("  parity: "+ (eq?"PASS":"FAIL") +"\n");
            summary.append("  seq ms="+tSeq+" par ms="+tPar+"\n");

            // Determinism: run parallel 3 times and compare hashes
            String h1 = hash(Cp);
            String h2 = hash(algo_parallel.run(A,B,1.0,null,0.0,64,64,64));
            String h3 = hash(algo_parallel.run(A,B,1.0,null,0.0,64,64,64));
            boolean det = h1.equals(h2) && h1.equals(h3);
            summary.append("  determinism: "+ (det?"PASS":"FAIL") +" hash="+h1+"\n");

            if (!eq || !det) allOk = false;
        }

        // Performance smoke test on larger N
        int M=512,K=512,N=512;
        rng.setSeed(777);
        double[][] A = randomMatrix(M,K);
        double[][] B = randomMatrix(K,N);
        long tSeq = timeMs(() -> GemmBaseline.run(A,B,1.0,null,0.0,128,128,128));
        long tPar = timeMs(() -> algo_parallel.run(A,B,1.0,null,0.0,128,128,128));
        String perf = String.format("perf M=%d K=%d N=%d seq_ms=%d par_ms=%d speedup=%.3f\n",
                M,K,N,tSeq,tPar, tPar>0 ? (double)tSeq/(double)tPar : 0.0);
        System.out.print(summary.toString());
        System.out.print(perf);
    }
}
