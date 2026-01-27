using System;
using System.Collections.Generic;
using System.Threading.Tasks;

namespace SmithWatermanAlignment
{
    // Parallel implementation using tiled anti-diagonal (wavefront) parallelism
    public class SmithWaterman
    {
        private readonly int matchScore;
        private readonly int mismatchScore;
        private readonly int gapScore;
        // Sequential fallback threshold (cells). Conservative to avoid overhead on small problems.
        private readonly int smallThresholdCells = 1_000_000; // 1M cells
        private readonly int tile = 128; // tile size for blocked wavefront

        public SmithWaterman(int match, int mismatch, int gap)
        {
            matchScore = match;
            mismatchScore = mismatch;
            gapScore = gap;
        }

        public int[][] ConstructMatrix(string query, string reference)
        {
            int n = query.Length + 1; // rows
            int m = reference.Length + 1; // cols

            // Use dense 2D array for better locality; convert to jagged at end
            int[,] H2 = new int[n, m];

            // Cache string data to local char arrays for faster repeated access
            var qArr = query.ToCharArray();
            var rArr = reference.ToCharArray();

            int cells = (n - 1) * (m - 1);
            int maxWorkers = Math.Max(1, Environment.ProcessorCount);
            var opts = new ParallelOptions { MaxDegreeOfParallelism = maxWorkers };

            // Sequential fast path for small inputs or single core
            if (cells <= smallThresholdCells || maxWorkers == 1)
            {
                for (int i = 1; i < n; i++)
                {
                    for (int j = 1; j < m; j++)
                    {
                        int scoreDiagonal = H2[i - 1, j - 1] + (qArr[i - 1] == rArr[j - 1] ? matchScore : mismatchScore);
                        int scoreUp = H2[i - 1, j] + gapScore;
                        int scoreLeft = H2[i, j - 1] + gapScore;
                        int best = scoreDiagonal;
                        if (scoreUp > best) best = scoreUp;
                        if (scoreLeft > best) best = scoreLeft;
                        if (best < 0) best = 0;
                        H2[i, j] = best;
                    }
                }
            }
            else
            {
                // Blocked wavefront over tiles
                int B = tile;
                int nBlocks = (n - 1 + B - 1) / B; // number of blocks covering rows 1..n-1
                int mBlocks = (m - 1 + B - 1) / B; // covering cols 1..m-1

                // Iterate tile anti-diagonals
                for (int td = 0; td <= (nBlocks - 1) + (mBlocks - 1); td++)
                {
                    int biStart = Math.Max(0, td - (mBlocks - 1));
                    int biEnd = Math.Min(nBlocks - 1, td);
                    int len = biEnd - biStart + 1;
                    if (len <= 0) continue;

                    Parallel.For(0, len, opts, t =>
                    {
                        int bi = biStart + t;
                        int bj = td - bi;
                        int i0 = 1 + bi * B;
                        int i1 = Math.Min(n - 1, i0 + B - 1);
                        int j0 = 1 + bj * B;
                        int j1 = Math.Min(m - 1, j0 + B - 1);

                        // Compute this tile sequentially (respecting in-tile dependencies)
                        for (int i = i0; i <= i1; i++)
                        {
                            int qi = i - 1;
                            for (int j = j0; j <= j1; j++)
                            {
                                int scoreDiagonal = H2[i - 1, j - 1] + (qArr[qi] == rArr[j - 1] ? matchScore : mismatchScore);
                                int scoreUp = H2[i - 1, j] + gapScore;
                                int scoreLeft = H2[i, j - 1] + gapScore;
                                int best = scoreDiagonal;
                                if (scoreUp > best) best = scoreUp;
                                if (scoreLeft > best) best = scoreLeft;
                                if (best < 0) best = 0;
                                H2[i, j] = best;
                            }
                        }
                    });
                    // Barrier at end of Parallel.For per tile diagonal
                }
            }

            // Convert to jagged array for external API compatibility
            int[][] H = new int[n][];
            for (int i = 0; i < n; i++)
            {
                H[i] = new int[m];
                for (int j = 0; j < m; j++) H[i][j] = H2[i, j];
            }

            return H;
        }

        public (int, int) FindHighestScore(int[][] H)
        {
            int maxScore = 0;
            int maxI = 0;
            int maxJ = 0;

            for (int i = 0; i < H.Length; i++)
            {
                for (int j = 0; j < H[i].Length; j++)
                {
                    if (H[i][j] > maxScore)
                    {
                        maxScore = H[i][j];
                        maxI = i;
                        maxJ = j;
                    }
                }
            }

            return (maxI, maxJ);
        }

        public (string, string, int, double) Traceback(int[][] H, string query, string reference)
        {
            List<char> alignedA = new List<char>();
            List<char> alignedB = new List<char>();

            var (i, j) = FindHighestScore(H);
            int score = H[i][j];

            int totalMatch = 0;
            int totalAlignment = 0;

            while (i > 0 && j > 0)
            {
                int currentScore = H[i][j];
                if (currentScore == 0) break;

                int diagonalScore = H[i - 1][j - 1];
                int upScore = H[i - 1][j];
                int leftScore = H[i][j - 1];

                int expectedDiagonal = diagonalScore + (query[i - 1] == reference[j - 1] ? matchScore : mismatchScore);

                if (currentScore == expectedDiagonal)
                {
                    alignedA.Add(query[i - 1]);
                    alignedB.Add(reference[j - 1]);
                    totalAlignment++;
                    if (query[i - 1] == reference[j - 1]) totalMatch++;
                    i--; j--;
                }
                else if (currentScore == upScore + gapScore)
                {
                    alignedA.Add(query[i - 1]);
                    alignedB.Add('-');
                    totalAlignment++;
                    i--;
                }
                else if (currentScore == leftScore + gapScore)
                {
                    alignedA.Add('-');
                    alignedB.Add(reference[j - 1]);
                    totalAlignment++;
                    j--;
                }
                else
                {
                    break;
                }
            }

            alignedA.Reverse();
            alignedB.Reverse();

            double percentageIdentity = (totalAlignment > 0) ? ((double)totalMatch / totalAlignment) * 100.0 : 0.0;

            string alignedAString = new string(alignedA.ToArray());
            string alignedBString = new string(alignedB.ToArray());

            return (alignedAString, alignedBString, score, percentageIdentity);
        }

        public (string, string, int, double) FindAlignment(string query, string reference)
        {
            int[][] H = ConstructMatrix(query, reference);
            return Traceback(H, query, reference);
        }
    }
}
