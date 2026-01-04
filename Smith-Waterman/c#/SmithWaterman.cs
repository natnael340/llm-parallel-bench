using System;
using System.Collections.Generic;
using System.Linq;

namespace SmithWatermanAlignment
{
    public class SmithWaterman
    {
        private int matchScore;
        private int mismatchScore;
        private int gapScore;

        public SmithWaterman(int match, int mismatch, int gap)
        {
            matchScore = match;
            mismatchScore = mismatch;
            gapScore = gap;
        }

        public int[][] ConstructMatrix(string query, string reference)
        {
            int n = query.Length + 1;
            int m = reference.Length + 1;

            // Initialize matrix with zeros
            int[][] H = new int[n][];
            for (int i = 0; i < n; i++)
            {
                H[i] = new int[m];
            }

            for (int i = 1; i < n; i++)
            {
                for (int j = 1; j < m; j++)
                {
                    int scoreDiagonal = H[i - 1][j - 1] +
                        (query[i - 1] == reference[j - 1] ? matchScore : mismatchScore);

                    int scoreUp = H[i - 1][j] + gapScore;
                    int scoreLeft = H[i][j - 1] + gapScore;

                    H[i][j] = Math.Max(0, Math.Max(scoreDiagonal, Math.Max(scoreUp, scoreLeft)));
                }
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

                if (currentScore == 0)
                {
                    break;
                }

                int diagonalScore = H[i - 1][j - 1];
                int upScore = H[i - 1][j];
                int leftScore = H[i][j - 1];

                int expectedDiagonal = diagonalScore +
                    (query[i - 1] == reference[j - 1] ? matchScore : mismatchScore);

                if (currentScore == expectedDiagonal)
                {
                    alignedA.Add(query[i - 1]);
                    alignedB.Add(reference[j - 1]);
                    totalAlignment++;

                    if (query[i - 1] == reference[j - 1])
                    {
                        totalMatch++;
                    }
                    i--;
                    j--;
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

            // Reverse the lists
            alignedA.Reverse();
            alignedB.Reverse();

            double percentageIdentity = (totalAlignment > 0)
                ? ((double)totalMatch / totalAlignment) * 100.0
                : 0.0;

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