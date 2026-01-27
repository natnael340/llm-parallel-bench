using System;
using System.Collections.Generic;
using System.Threading.Tasks;

namespace SmithWatermanAlignment
{
    public class SmithWatermanParallel
    {
        private readonly int matchScore;
        private readonly int mismatchScore;
        private readonly int gapScore;
        private const int BlockSize = 64; // Tunable parameter for performance

        public SmithWatermanParallel(int match, int mismatch, int gap)
        {
            matchScore = match;
            mismatchScore = mismatch;
            gapScore = gap;
        }

        public int[][] ConstructMatrix(string query, string reference)
        {
            int n = query.Length + 1;
            int m = reference.Length + 1;

            if (n <= 1 || m <= 1) return new int[n][];

            // Fallback for inputs smaller than a single block
            if (n < BlockSize || m < BlockSize)
            {
                return new SmithWaterman(matchScore, mismatchScore, gapScore).ConstructMatrix(query, reference);
            }

            int[][] H = new int[n][];
            for (int i = 0; i < n; i++)
            {
                H[i] = new int[m];
            }

            int numBlocksN = (n + BlockSize - 1) / BlockSize;
            int numBlocksM = (m + BlockSize - 1) / BlockSize;

            for (int k = 0; k < numBlocksN + numBlocksM - 1; k++)
            {
                var blocksToProcess = new List<Tuple<int, int>>();
                for (int i = 0; i < numBlocksN; i++)
                {
                    int j = k - i;
                    if (j >= 0 && j < numBlocksM)
                    {
                        blocksToProcess.Add(new Tuple<int, int>(i, j));
                    }
                }
                
                Parallel.ForEach(blocksToProcess, new ParallelOptions { MaxDegreeOfParallelism = Environment.ProcessorCount }, block =>
                {
                    ComputeBlock(block.Item1, block.Item2, H, query, reference, n, m);
                });
            }

            return H;
        }

        private void ComputeBlock(int blockI, int blockJ, int[][] H, string query, string reference, int n, int m)
        {
            int iStart = blockI * BlockSize;
            int iEnd = Math.Min(iStart + BlockSize, n);

            int jStart = blockJ * BlockSize;
            int jEnd = Math.Min(jStart + BlockSize, m);
            
            // Adjust start to 1 since score at 0 is always 0
            iStart = Math.Max(1, iStart);
            jStart = Math.Max(1, jStart);

            for (int i = iStart; i < iEnd; i++)
            {
                for (int j = jStart; j < jEnd; j++)
                {
                    int scoreDiagonal = H[i - 1][j - 1] +
                        (query[i - 1] == reference[j - 1] ? matchScore : mismatchScore);

                    int scoreUp = H[i - 1][j] + gapScore;
                    int scoreLeft = H[i][j - 1] + gapScore;

                    H[i][j] = Math.Max(0, Math.Max(scoreDiagonal, Math.Max(scoreUp, scoreLeft)));
                }
            }
        }
        
        public (int, int) FindHighestScore(int[][] H)
        {
            int maxScore = 0;
            int maxI = 0;
            int maxJ = 0;

            for (int i = 0; i < H.Length; i++)
            {
                if (H[i] == null) continue;
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
            if (i == 0 && j == 0) return ("", "", 0, 0.0);

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
                    if (query[i - 1] == reference[j - 1]) totalMatch++;
                    i--;
                    j--;
                }
                else if (currentScore == upScore + gapScore)
                {
                    alignedA.Add(query[i - 1]);
                    alignedB.Add('-');
                    i--;
                }
                else
                {
                    alignedA.Add('-');
                    alignedB.Add(reference[j - 1]);
                    j--;
                }
                totalAlignment++;
            }

            alignedA.Reverse();
            alignedB.Reverse();
            double percentageIdentity = (totalAlignment > 0) ? ((double)totalMatch / totalAlignment) * 100.0 : 0.0;
            return (new string(alignedA.ToArray()), new string(alignedB.ToArray()), score, percentageIdentity);
        }

        public (string, string, int, double) FindAlignment(string query, string reference)
        {
            int[][] H = ConstructMatrix(query, reference);
            return Traceback(H, query, reference);
        }
    }
}
