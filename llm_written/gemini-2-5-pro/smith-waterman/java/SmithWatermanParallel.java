import java.util.concurrent.ForkJoinPool;
import java.util.stream.IntStream;

public class SmithWatermanParallel {
    private final int matchScore;
    private final int mismatchScore;
    private final int gapScore;
    private final ForkJoinPool forkJoinPool;
    // Increased threshold: parallelism is only beneficial for very large matrices.
    private static final int SEQUENTIAL_THRESHOLD = 2000 * 2000; 

    public SmithWatermanParallel(int matchScore, int mismatchScore, int gapScore) {
        this.matchScore = matchScore;
        this.mismatchScore = mismatchScore;
        this.gapScore = gapScore;
        // Bounded to the number of available processors
        this.forkJoinPool = new ForkJoinPool(Runtime.getRuntime().availableProcessors());
    }

    public int[][] constructMatrix(String query, String reference) {
        int n = query.length() + 1;
        int m = reference.length() + 1;
        int[][] H = new int[n][m];

        // Fallback for small inputs
        if ((long) n * m < SEQUENTIAL_THRESHOLD) {
            return constructMatrixSequential(query, reference, H);
        }

        // The number of anti-diagonals is n + m - 1
        for (int k = 1; k < n + m - 1; k++) {
            final int current_k = k;
            // The range of i for a given anti-diagonal k
            int i_start = Math.max(1, current_k - m + 1);
            int i_end = Math.min(n, current_k + 1);

            // Execute the calculation for the current anti-diagonal in parallel
            forkJoinPool.submit(() -> {
                IntStream.range(i_start, i_end).parallel().forEach(i -> {
                    int j = current_k - i + 1;
                    if (j > 0 && j < m) {
                        int scoreDiagonal = H[i - 1][j - 1] +
                                (query.charAt(i - 1) == reference.charAt(j - 1) ? matchScore : mismatchScore);
                        int scoreUp = H[i - 1][j] + gapScore;
                        int scoreLeft = H[i][j - 1] + gapScore;
                        H[i][j] = Math.max(0, Math.max(scoreDiagonal, Math.max(scoreUp, scoreLeft)));
                    }
                });
            }).join(); // Wait for the current anti-diagonal to complete before starting the next
        }

        return H;
    }

    private int[][] constructMatrixSequential(String query, String reference, int[][] H) {
        int n = H.length;
        int m = H[0].length;
        for (int i = 1; i < n; i++) {
            for (int j = 1; j < m; j++) {
                int scoreDiagonal = H[i - 1][j - 1] +
                        (query.charAt(i - 1) == reference.charAt(j - 1) ? matchScore : mismatchScore);
                int scoreUp = H[i - 1][j] + gapScore;
                int scoreLeft = H[i][j - 1] + gapScore;
                H[i][j] = Math.max(0, Math.max(scoreDiagonal, Math.max(scoreUp, scoreLeft)));
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
            int expectedDiagonal = diagonalScore +
                    (query.charAt(i - 1) == reference.charAt(j - 1) ? matchScore : mismatchScore);

            if (currentScore == expectedDiagonal) {
                alignedA.append(query.charAt(i - 1));
                alignedB.append(reference.charAt(j - 1));
                totalAlignment++;
                if (query.charAt(i - 1) == reference.charAt(j - 1)) {
                    totalMatch++;
                }
                i--;
                j--;
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
    
    public void shutdown() {
        forkJoinPool.shutdown();
    }

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

        @Override
        public boolean equals(Object obj) {
            if (this == obj) return true;
            if (obj == null || getClass() != obj.getClass()) return false;
            AlignmentResult that = (AlignmentResult) obj;
            return score == that.score &&
                   Double.compare(that.identity, identity) == 0 &&
                   alignedA.equals(that.alignedA) &&
                   alignedB.equals(that.alignedB);
        }

        @Override
        public String toString() {
            return "AlignmentResult{" +
                   "alignedA='" + alignedA + '\'' +
                   ", alignedB='" + alignedB + '\'' +
                   ", score=" + score +
                   ", identity=" + identity +
                   '}';
        }
    }
}
