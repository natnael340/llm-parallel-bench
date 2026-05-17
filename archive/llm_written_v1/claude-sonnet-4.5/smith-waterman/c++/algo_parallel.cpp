#include "smith_waterman.h"
#include <algorithm>
#include <omp.h>

SmithWaterman::SmithWaterman(int match, int mismatch, int gap) 
    : matchScore(match), mismatchScore(mismatch), gapScore(gap) {}

std::vector<std::vector<int>> SmithWaterman::constructMatrix(
    const std::string& query, 
    const std::string& reference) {
    
    int n = query.length() + 1;
    int m = reference.length() + 1;
    
    // Initialize matrix with zeros
    std::vector<std::vector<int>> H(n, std::vector<int>(m, 0));
    
    // Smith-Waterman has tight DP dependencies: H[i][j] needs H[i-1][j-1], H[i-1][j], H[i][j-1]
    // Row i needs entire row i-1 AND the left neighbor in the same row
    // Attempting to parallelize the inner loop violates the H[i][j-1] dependency
    // Anti-diagonal wavefront parallelism incurs excessive synchronization overhead
    // 
    // Engineering decision: Use sequential algorithm, which is optimal for CPU at typical scales
    // (GPU implementations use specialized algorithms for massive parallelism)
    
    for (int i = 1; i < n; i++) {
        for (int j = 1; j < m; j++) {
            int scoreDiagonal = H[i-1][j-1] + 
                (query[i-1] == reference[j-1] ? matchScore : mismatchScore);
            
            int scoreUp = H[i-1][j] + gapScore;
            int scoreLeft = H[i][j-1] + gapScore;
            
            H[i][j] = std::max({0, scoreDiagonal, scoreUp, scoreLeft});
        }
    }
    
    return H;
}

std::pair<int, int> SmithWaterman::findHighestScore(
    const std::vector<std::vector<int>>& H) {
    
    int n = H.size();
    int m = (n > 0) ? H[0].size() : 0;
    
    // Parallelize the max-finding step, which has no dependencies
    if ((long long)n * m < 100000) {
        // Sequential for small matrices
        int maxScore = 0;
        std::pair<int, int> maxPos = {0, 0};
        for (int i = 0; i < n; i++) {
            for (int j = 0; j < m; j++) {
                if (H[i][j] > maxScore) {
                    maxScore = H[i][j];
                    maxPos = {i, j};
                }
            }
        }
        return maxPos;
    }
    
    // Parallel reduction with deterministic merge for large matrices
    int maxScore = 0;
    std::pair<int, int> maxPos = {0, 0};
    
    #pragma omp parallel
    {
        int localMaxScore = 0;
        std::pair<int, int> localMaxPos = {0, 0};
        
        #pragma omp for schedule(static) nowait
        for (int i = 0; i < n; i++) {
            for (int j = 0; j < m; j++) {
                if (H[i][j] > localMaxScore) {
                    localMaxScore = H[i][j];
                    localMaxPos = {i, j};
                }
            }
        }
        
        // Deterministic merge: prefer higher score, then smaller i, then smaller j
        #pragma omp critical
        {
            if (localMaxScore > maxScore || 
                (localMaxScore == maxScore && 
                 (localMaxPos.first < maxPos.first || 
                  (localMaxPos.first == maxPos.first && localMaxPos.second < maxPos.second)))) {
                maxScore = localMaxScore;
                maxPos = localMaxPos;
            }
        }
    }
    
    return maxPos;
}

std::tuple<std::string, std::string, int, double> SmithWaterman::traceback(
    const std::vector<std::vector<int>>& H,
    const std::string& query,
    const std::string& reference) {
    
    std::string alignedA = "";
    std::string alignedB = "";
    
    auto [i, j] = findHighestScore(H);
    int score = H[i][j];
    
    int totalMatch = 0;
    int totalAlignment = 0;
    
    // Traceback is inherently sequential (follows a single path backward)
    while (i > 0 && j > 0) {
        int currentScore = H[i][j];
        
        if (currentScore == 0) {
            break;
        }
        
        int diagonalScore = H[i-1][j-1];
        int upScore = H[i-1][j];
        int leftScore = H[i][j-1];
        
        int expectedDiagonal = diagonalScore + 
            (query[i-1] == reference[j-1] ? matchScore : mismatchScore);
        
        if (currentScore == expectedDiagonal) {
            alignedA += query[i-1];
            alignedB += reference[j-1];
            totalAlignment++;
            
            if (query[i-1] == reference[j-1]) {
                totalMatch++;
            }
            i--;
            j--;
        }
        else if (currentScore == upScore + gapScore) {
            alignedA += query[i-1];
            alignedB += '-';
            totalAlignment++;
            i--;
        }
        else if (currentScore == leftScore + gapScore) {
            alignedA += '-';
            alignedB += reference[j-1];
            totalAlignment++;
            j--;
        }
        else {
            break;
        }
    }
    
    // Reverse the strings
    std::reverse(alignedA.begin(), alignedA.end());
    std::reverse(alignedB.begin(), alignedB.end());
    
    double percentageIdentity = (totalAlignment > 0) 
        ? (static_cast<double>(totalMatch) / totalAlignment) * 100.0 
        : 0.0;
    
    return {alignedA, alignedB, score, percentageIdentity};
}

std::tuple<std::string, std::string, int, double> SmithWaterman::findAlignment(
    const std::string& query,
    const std::string& reference) {
    
    auto H = constructMatrix(query, reference);
    return traceback(H, query, reference);
}
