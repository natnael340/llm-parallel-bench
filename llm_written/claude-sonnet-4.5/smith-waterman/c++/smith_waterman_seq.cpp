#include "smith_waterman.h"
#include <algorithm>

SmithWaterman::SmithWaterman(int match, int mismatch, int gap) 
    : matchScore(match), mismatchScore(mismatch), gapScore(gap) {}

std::vector<std::vector<int>> SmithWaterman::constructMatrix(
    const std::string& query, 
    const std::string& reference) {
    
    int n = query.length() + 1;
    int m = reference.length() + 1;
    
    // Initialize matrix with zeros
    std::vector<std::vector<int>> H(n, std::vector<int>(m, 0));
    
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
    
    int maxScore = 0;
    std::pair<int, int> maxPos = {0, 0};
    
    for (int i = 0; i < H.size(); i++) {
        for (int j = 0; j < H[i].size(); j++) {
            if (H[i][j] > maxScore) {
                maxScore = H[i][j];
                maxPos = {i, j};
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
