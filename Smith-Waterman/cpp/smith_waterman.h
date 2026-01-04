#ifndef SMITH_WATERMAN_H
#define SMITH_WATERMAN_H

#include <vector>
#include <string>
#include <tuple>
#include <utility>

class SmithWaterman {
private:
    int matchScore;
    int mismatchScore;
    int gapScore;

public:
    SmithWaterman(int match, int mismatch, int gap);
    
    std::vector<std::vector<int>> constructMatrix(const std::string& query, 
                                                   const std::string& reference);
    
    std::pair<int, int> findHighestScore(const std::vector<std::vector<int>>& H);
    
    std::tuple<std::string, std::string, int, double> traceback(
        const std::vector<std::vector<int>>& H,
        const std::string& query,
        const std::string& reference);
    
    std::tuple<std::string, std::string, int, double> findAlignment(
        const std::string& query,
        const std::string& reference);
};

#endif