#include "smith_waterman_parallel.h"
#include "smith_waterman_sequential.h" 
#include <algorithm>
#include <vector>
#include <omp.h>

SmithWaterman::SmithWaterman(int match, int mismatch, int gap) 
    : matchScore(match), mismatchScore(mismatch), gapScore(gap) {}

std::vector<std::vector<int>> SmithWaterman::constructMatrix(
    const std::string& query, 
    const std::string& reference) {
    
    int n = query.length() + 1;
    int m = reference.length() + 1;
    
    std::vector<std::vector<int>> H(n, std::vector<int>(m, 0));

    // Parallelize along anti-diagonals
    for (int k = 1; k < n + m - 1; ++k) {
        #pragma omp parallel for schedule(static)
        for (int i = std::max(1, k - m + 1); i < std::min(n, k + 1); ++i) {
            int j = k - i + 1;
            if (j > 0 && j < m) {
                int scoreDiagonal = H[i-1][j-1] + 
                    (query[i-1] == reference[j-1] ? matchScore : mismatchScore);
                
                int scoreUp = H[i-1][j] + gapScore;
                int scoreLeft = H[i][j-1] + gapScore;
                
                H[i][j] = std::max({0, scoreDiagonal, scoreUp, scoreLeft});
            }
        }
    }
    
    return H;
}

std::pair<int, int> SmithWaterman::findHighestScore(
    const std::vector<std::vector<int>>& H) {
    
    int maxScore = -1; // Start with -1 to handle all-zero matrix correctly
    std::pair<int, int> maxPos = {0, 0};
    int n = H.size();
    if (n == 0) return maxPos;
    int m = H[0].size();

    #pragma omp parallel
    {
        int localMaxScore = -1;
        std::pair<int, int> localMaxPos = {0, 0};

        #pragma omp for collapse(2) schedule(static)
        for (int i = 0; i < n; i++) {
            for (int j = 0; j < m; j++) {
                if (H[i][j] > localMaxScore) {
                    localMaxScore = H[i][j];
                    localMaxPos = {i, j};
                }
            }
        }

        #pragma omp critical
        {
            if (localMaxScore > maxScore) {
                maxScore = localMaxScore;
                maxPos = localMaxPos;
            } else if (localMaxScore == maxScore) {
                // Deterministic tie-breaking
                if (localMaxPos.first < maxPos.first || 
                   (localMaxPos.first == maxPos.first && localMaxPos.second < maxPos.second)) {
                    maxPos = localMaxPos;
                }
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
    if (i == 0 && j == 0) { // Handle empty or no-alignment case
        return {"", "", 0, 0.0};
    }
    int score = H[i][j];
    
    int totalMatch = 0;
    int totalAlignment = 0;
    
    while (i > 0 && j > 0 && H[i][j] != 0) {
        int currentScore = H[i][j];
        
        int diagonalScore = H[i-1][j-1];
        int upScore = H[i-1][j];
        int leftScore = H[i][j-1];
        
        // Deterministic traceback priority: Diagonal > Up > Left
        if (currentScore == diagonalScore + (query[i-1] == reference[j-1] ? matchScore : mismatchScore)) {
            alignedA += query[i-1];
            alignedB += reference[j-1];
            if (query[i-1] == reference[j-1]) totalMatch++;
            i--; j--;
        } else if (currentScore == upScore + gapScore) {
            alignedA += query[i-1];
            alignedB += '-';
            i--;
        } else { // Must be leftScore + gapScore
            alignedA += '-';
            alignedB += reference[j-1];
            j--;
        }
        totalAlignment++;
    }
    
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
    
    // Safety switch for small inputs where parallel overhead is too high
    if (query.length() < 250 || reference.length() < 250) {
        SmithWatermanSequential sw_seq(matchScore, mismatchScore, gapScore);
        return sw_seq.findAlignment(query, reference);
    }

    auto H = constructMatrix(query, reference);
    return traceback(H, query, reference);
}
