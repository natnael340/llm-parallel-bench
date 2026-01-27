import java.util.concurrent.*;
import java.util.ArrayList;
import java.util.List;

/**
 * Parallel implementation of Smith-Waterman local sequence alignment algorithm.
 * Uses anti-diagonal wavefront parallelization with bounded thread pool.
 */
public class SmithWaterman {
    private int matchScore;
    private int mismatchScore;
    private int gapScore;
    
    // Minimum matrix size to use parallel processing (2M cells)
    // Below this threshold, coordination overhead exceeds speedup benefit
    private static final long MIN_SIZE_FOR_PARALLEL = 2_000_000L;
    
    // Reusable thread pool sized to available cores
    private static final ForkJoinPool THREAD_POOL = 
        new ForkJoinPool(Runtime.getRuntime().availableProcessors());

    public SmithWaterman(int matchScore, int mismatchScore, int gapScore) {
        this.matchScore = matchScore;
        this.mismatchScore = mismatchScore;
        this.gapScore = gapScore;
    }

    /**
     * Constructs the scoring matrix H using anti-diagonal wavefront parallelization.
     * Cells on the same anti-diagonal (i+j = constant) are independent and computed concurrently.
     * 
     * @param query the query sequence
     * @param reference the reference sequence
     * @return scoring matrix H[n][m] where n = query.length()+1, m = reference.length()+1
     */
    public int[][] constructMatrix(String query, String reference) {
        int n = query.length() + 1;
        int m = reference.length() + 1;

        // Small/medium input threshold: use sequential for efficiency
        if ((long)n * m < MIN_SIZE_FOR_PARALLEL) {
            return constructMatrixSequential(query, reference);
        }

        // Initialize matrix with zeros (first row and column remain zero)
        int[][] H = new int[n][m];
        
        int numCores = Runtime.getRuntime().availableProcessors();
        
        // Process anti-diagonals sequentially (anti-diagonal k = cells where i+j = k)
        // Within each anti-diagonal, cells are independent and processed in parallel
        for (int antidiag = 2; antidiag < n + m - 1; antidiag++) {
            final int ad = antidiag;
            
            // Determine valid (i,j) pairs on this anti-diagonal
            // i ranges from max(1, ad-m+1) to min(n-1, ad-1)
            int iStart = Math.max(1, ad - m + 1);
            int iEnd = Math.min(n - 1, ad - 1);
            int numCells = iEnd - iStart + 1;
            
            // Chunk cells to amortize task creation overhead
            // Minimum 64 cells per task to make parallelism worthwhile
            int minChunkSize = 64;
            int desiredTasks = Math.min(numCores, numCells / minChunkSize);
            if (desiredTasks < 1) desiredTasks = 1;
            
            int chunkSize = (numCells + desiredTasks - 1) / desiredTasks;
            
            // If only one chunk or very small, process sequentially
            if (chunkSize >= numCells || desiredTasks <= 1) {
                for (int i = iStart; i <= iEnd; i++) {
                    int j = ad - i;
                    computeCell(H, query, reference, i, j);
                }
            } else {
                // Parallel processing: submit chunks to thread pool
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
                
                // Wait for all chunks in this anti-diagonal to complete (barrier sync)
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

    /**
     * Computes a single cell H[i][j] based on three predecessors.
     */
    private void computeCell(int[][] H, String query, String reference, int i, int j) {
        // Score for diagonal move (match or mismatch)
        int scoreDiagonal = H[i - 1][j - 1] + 
            (query.charAt(i - 1) == reference.charAt(j - 1) ? matchScore : mismatchScore);
        
        // Score for vertical move (gap in reference)
        int scoreUp = H[i - 1][j] + gapScore;
        
        // Score for horizontal move (gap in query)
        int scoreLeft = H[i][j - 1] + gapScore;
        
        // Local alignment: allow starting fresh (score 0)
        H[i][j] = Math.max(0, Math.max(scoreDiagonal, Math.max(scoreUp, scoreLeft)));
    }

    /**
     * Sequential fallback for small matrices (below parallel threshold).
     */
    private int[][] constructMatrixSequential(String query, String reference) {
        int n = query.length() + 1;
        int m = reference.length() + 1;

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

    /**
     * Finds the position of the highest score in the matrix.
     * This is the starting point for traceback.
     */
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

    /**
     * Performs traceback from the highest score to reconstruct the alignment.
     * This step is inherently sequential (follows dependency chain backwards).
     */
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
                break; // Reached end of local alignment
            }

            int diagonalScore = H[i - 1][j - 1];
            int upScore = H[i - 1][j];
            int leftScore = H[i][j - 1];

            int expectedDiagonal = diagonalScore + 
                (query.charAt(i - 1) == reference.charAt(j - 1) ? matchScore : mismatchScore);

            // Determine which move was taken to reach current cell
            if (currentScore == expectedDiagonal) {
                // Diagonal move (match or mismatch)
                alignedA.append(query.charAt(i - 1));
                alignedB.append(reference.charAt(j - 1));
                totalAlignment++;

                if (query.charAt(i - 1) == reference.charAt(j - 1)) {
                    totalMatch++;
                }
                i--;
                j--;
            } else if (currentScore == upScore + gapScore) {
                // Vertical move (gap in reference)
                alignedA.append(query.charAt(i - 1));
                alignedB.append('-');
                totalAlignment++;
                i--;
            } else if (currentScore == leftScore + gapScore) {
                // Horizontal move (gap in query)
                alignedA.append('-');
                alignedB.append(reference.charAt(j - 1));
                totalAlignment++;
                j--;
            } else {
                break; // Shouldn't happen with correct scoring
            }
        }

        // Reverse strings (built backwards during traceback)
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

    /**
     * Main entry point: constructs matrix and performs traceback.
     */
    public AlignmentResult findAlignment(String query, String reference) {
        int[][] H = constructMatrix(query, reference);
        return traceback(H, query, reference);
    }

    /**
     * Result container holding aligned sequences, score, and identity percentage.
     */
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
