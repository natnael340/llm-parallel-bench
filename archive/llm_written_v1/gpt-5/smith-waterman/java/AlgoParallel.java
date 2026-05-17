import java.util.concurrent.*;
import java.util.concurrent.atomic.AtomicReference;

// Parallel Smith-Waterman (local alignment, linear gap)
public class AlgoParallel {
    private final int matchScore;
    private final int mismatchScore;
    private final int gapScore;
    private final int maxWorkers; // cap to available processors
    private final long seqThresholdCells; // tiny-input sequential fallback threshold

    public AlgoParallel(int matchScore, int mismatchScore, int gapScore) {
        this(matchScore, mismatchScore, gapScore,
                Math.max(1, Runtime.getRuntime().availableProcessors()),
                50_000L);
    }

    public AlgoParallel(int matchScore, int mismatchScore, int gapScore, int maxWorkers, long seqThresholdCells) {
        this.matchScore = matchScore;
        this.mismatchScore = mismatchScore;
        this.gapScore = gapScore;
        this.maxWorkers = Math.max(1, maxWorkers);
        this.seqThresholdCells = Math.max(0L, seqThresholdCells);
    }

    // Deterministic anti-diagonal wavefront parallelization with reusable worker threads and barrier
    public int[][] constructMatrix(String query, String reference) {
        final int n = query.length() + 1; // rows
        final int m = reference.length() + 1; // cols
        final int[][] H = new int[n][m];

        // trivial/edge: empty sequences or tiny problems → sequential
        long cells = (long) (n - 1) * (m - 1);
        if (cells <= seqThresholdCells || maxWorkers == 1) {
            return constructMatrixSequential(query, reference);
        }

        final char[] A = query.toCharArray();
        final char[] B = reference.toCharArray();

        final int usableWorkers = Math.max(1, Math.min(maxWorkers, Runtime.getRuntime().availableProcessors()));
        final ExecutorService pool = Executors.newFixedThreadPool(usableWorkers);
        final CyclicBarrier barrier = new CyclicBarrier(usableWorkers);
        final AtomicReference<Throwable> errorRef = new AtomicReference<>(null);
        final int maxD = (n - 1) + (m - 1);

        for (int wid = 0; wid < usableWorkers; wid++) {
            final int workerId = wid;
            pool.execute(() -> {
                try {
                    for (int d = 2; d <= maxD; d++) {
                        final int iStart = Math.max(1, d - (m - 1));
                        final int iEnd = Math.min(n - 1, d - 1);
                        final int diagLen = Math.max(0, iEnd - iStart + 1);
                        // stripe this diagonal by workerId
                        for (int k = workerId; k < diagLen; k += usableWorkers) {
                            int i = iStart + k;
                            int j = d - i;
                            int scoreDiagonal = H[i - 1][j - 1] + (A[i - 1] == B[j - 1] ? matchScore : mismatchScore);
                            int scoreUp = H[i - 1][j] + gapScore;
                            int scoreLeft = H[i][j - 1] + gapScore;
                            int v = scoreDiagonal;
                            if (scoreUp > v) v = scoreUp;
                            if (scoreLeft > v) v = scoreLeft;
                            H[i][j] = Math.max(0, v);
                        }
                        barrier.await(); // end of diagonal
                    }
                } catch (Throwable t) {
                    errorRef.compareAndSet(null, t);
                    // try to trip barrier so others can exit
                    try { barrier.await(1, TimeUnit.MILLISECONDS); } catch (Exception ignored) {}
                }
            });
        }

        pool.shutdown();
        try {
            boolean done = pool.awaitTermination(5, TimeUnit.MINUTES);
            if (!done) throw new RuntimeException("Parallel SW timeout");
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            throw new RuntimeException("Parallel SW interrupted", e);
        }

        Throwable err = errorRef.get();
        if (err != null) {
            if (err instanceof RuntimeException) throw (RuntimeException) err;
            throw new RuntimeException(err);
        }

        return H;
    }

    // Sequential fallback used for very small problems
    private int[][] constructMatrixSequential(String query, String reference) {
        int n = query.length() + 1;
        int m = reference.length() + 1;
        int[][] H = new int[n][m];
        char[] A = query.toCharArray();
        char[] B = reference.toCharArray();
        for (int i = 1; i < n; i++) {
            for (int j = 1; j < m; j++) {
                int scoreDiagonal = H[i - 1][j - 1] + (A[i - 1] == B[j - 1] ? matchScore : mismatchScore);
                int scoreUp = H[i - 1][j] + gapScore;
                int scoreLeft = H[i][j - 1] + gapScore;
                int v = scoreDiagonal;
                if (scoreUp > v) v = scoreUp;
                if (scoreLeft > v) v = scoreLeft;
                H[i][j] = Math.max(0, v);
            }
        }
        return H;
    }

    public int[] findHighestScore(int[][] H) {
        int maxScore = 0;
        int maxI = 0;
        int maxJ = 0;
        for (int i = 0; i < H.length; i++) {
            for (int j = 0; j < H[i].length; j++) {
                if (H[i][j] > maxScore) {
                    maxScore = H[i][j];
                    maxI = i;
                    maxJ = j;
                }
            }
        }
        return new int[]{maxI, maxJ};
    }

    public AlignmentResult traceback(int[][] H, String query, String reference) {
        StringBuilder alignedA = new StringBuilder();
        StringBuilder alignedB = new StringBuilder();

        int[] maxPos = findHighestScore(H);
        int i = maxPos[0];
        int j = maxPos[1];
        int score = H[i][j];

        int totalMatch = 0;
        int totalAlignment = 0;

        while (i > 0 && j > 0) {
            int currentScore = H[i][j];
            if (currentScore == 0) break;

            int diagonalScore = H[i - 1][j - 1];
            int upScore = H[i - 1][j];
            int leftScore = H[i][j - 1];

            int expectedDiagonal = diagonalScore + (query.charAt(i - 1) == reference.charAt(j - 1) ? matchScore : mismatchScore);

            if (currentScore == expectedDiagonal) {
                alignedA.append(query.charAt(i - 1));
                alignedB.append(reference.charAt(j - 1));
                totalAlignment++;
                if (query.charAt(i - 1) == reference.charAt(j - 1)) totalMatch++;
                i--; j--;
            } else if (currentScore == upScore + gapScore) {
                alignedA.append(query.charAt(i - 1));
                alignedB.append('-');
                totalAlignment++;
                i--;
            } else if (currentScore == leftScore + gapScore) {
                alignedA.append('-');
                alignedB.append(reference.charAt(j - 1));
                totalAlignment++;
                j--;
            } else {
                break;
            }
        }

        alignedA.reverse();
        alignedB.reverse();

        double percentageIdentity = (totalAlignment > 0) ? ((double) totalMatch / totalAlignment) * 100.0 : 0.0;

        return new AlignmentResult(alignedA.toString(), alignedB.toString(), score, percentageIdentity);
    }

    public AlignmentResult findAlignment(String query, String reference) {
        int[][] H = constructMatrix(query, reference);
        return traceback(H, query, reference);
    }

    // Same result container as sequential version
    public static class AlignmentResult {
        public final String alignedA;
        public final String alignedB;
        public final int score;
        public final double identity;
        public AlignmentResult(String alignedA, String alignedB, int score, double identity) {
            this.alignedA = alignedA;
            this.alignedB = alignedB;
            this.score = score;
            this.identity = identity;
        }
    }
}
