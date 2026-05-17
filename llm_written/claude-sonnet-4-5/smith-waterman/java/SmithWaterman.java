import java.util.concurrent.*;
import java.util.ArrayList;
import java.util.List;

public class SmithWaterman {
    private int matchScore;
    private int mismatchScore;
    private int gapScore;
    
    // Minimum matrix size to use parallel processing
    // Anti-diagonal parallelization has high overhead, only worthwhile for very large matrices
    private static final long MIN_SIZE_FOR_PARALLEL = 2_000_000L;
    
    // Reusable thread pool
    private static final ForkJoinPool THREAD_POOL = new ForkJoinPool(Runtime.getRuntime().availableProcessors());

    public SmithWaterman(int matchScore, int mismatchScore, int gapScore) {
        this.matchScore = matchScore;
        this.mismatchScore = mismatchScore;
        this.gapScore = gapScore;
    }

    public int[][] constructMatrix(String query, String reference) {
        int n = query.length() + 1;
        int m = reference.length() + 1;

        // Small/medium input threshold: use sequential for efficiency
        if ((long)n * m < MIN_SIZE_FOR_PARALLEL) {
            return constructMatrixSequential(query, reference);
        }

        // Initialize matrix with zeros
        int[][] H = new int[n][m];
        
        // Use anti-diagonal wavefront parallelization
        // Cells on the same anti-diagonal (i+j = constant) are independent
        int numCores = Runtime.getRuntime().availableProcessors();
        
        // Process anti-diagonals sequentially, parallelize within each anti-diagonal
        for (int antidiag = 2; antidiag < n + m - 1; antidiag++) {
            final int ad = antidiag;
            
            // Determine range of valid (i,j) pairs on this anti-diagonal
            int iStart = Math.max(1, ad - m + 1);
            int iEnd = Math.min(n - 1, ad - 1);
            int numCells = iEnd - iStart + 1;
            
            // Chunk size: divide cells among workers with reasonable granularity
            int minChunkSize = 64; // Minimum cells per task to amortize overhead
            int desiredTasks = Math.min(numCores, numCells / minChunkSize);
            if (desiredTasks < 1) desiredTasks = 1;
            
            int chunkSize = (numCells + desiredTasks - 1) / desiredTasks;
            
            // If only one chunk or very small, do it sequentially
            if (chunkSize >= numCells || desiredTasks <= 1) {
                for (int i = iStart; i <= iEnd; i++) {
                    int j = ad - i;
                    computeCell(H, query, reference, i, j);
                }
            } else {
                // Parallel processing of chunks on this anti-diagonal
                List<Future<?>> futures = new ArrayList<>();
                
                for (int chunkStart = iStart; chunkStart <= iEnd; chunkStart += chunkSize) {
                    final int cs = chunkStart;
                    final int ce = Math.min(iEnd, chunkStart + chunkSize - 1);
                    
                    Future<?> future = THREAD_POOL.submit(() -> {
                        for (int i = cs; i <= ce; i++) {
                            int j = ad - i;
                            computeCell(H, query, reference, i, j);
                        }
                    });
                    futures.add(future);
                }
                
                // Wait for all chunks in this anti-diagonal to complete
                try {
                    for (Future<?> future : futures) {
                        future.get();
                    }
                } catch (InterruptedException | ExecutionException e) {
                    throw new RuntimeException("Parallel execution failed", e);
                }
            }
        }

        return H;
    }

    private void computeCell(int[][] H, String query, String reference, int i, int j) {
        int scoreDiagonal = H[i - 1][j - 1] + 
            (query.charAt(i - 1) == reference.charAt(j - 1) ? matchScore : mismatchScore);
        
        int scoreUp = H[i - 1][j] + gapScore;
        int scoreLeft = H[i][j - 1] + gapScore;
        
        H[i][j] = Math.max(0, Math.max(scoreDiagonal, Math.max(scoreUp, scoreLeft)));
    }

    private int[][] constructMatrixSequential(String query, String reference) {
        int n = query.length() + 1;
        int m = reference.length() + 1;

        // Initialize matrix with zeros
        int[][] H = new int[n][m];

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

            if (currentScore == 0) {
                break;
            }

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

        // Reverse the strings
        alignedA.reverse();
        alignedB.reverse();

        double percentageIdentity = (totalAlignment > 0) 
            ? ((double) totalMatch / totalAlignment) * 100.0 
            : 0.0;

        return new AlignmentResult(
            alignedA.toString(), 
            alignedB.toString(), 
            score, 
            percentageIdentity
        );
    }

    public AlignmentResult findAlignment(String query, String reference) {
        int[][] H = constructMatrix(query, reference);
        return traceback(H, query, reference);
    }

    // Inner class to hold alignment results
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
