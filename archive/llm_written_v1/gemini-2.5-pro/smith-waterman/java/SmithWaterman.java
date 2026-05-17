public class SmithWaterman {
    private int matchScore;
    private int mismatchScore;
    private int gapScore;

    public SmithWaterman(int matchScore, int mismatchScore, int gapScore) {
        this.matchScore = matchScore;
        this.mismatchScore = mismatchScore;
        this.gapScore = gapScore;
    }

    public int[][] constructMatrix(String query, String reference) {
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
