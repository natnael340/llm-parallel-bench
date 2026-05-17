#ifndef SMITH_WATERMAN_H
#define SMITH_WATERMAN_H

#include <string>
#include <vector>
#include <tuple>

class SmithWaterman {
private:
    int matchScore;
    int mismatchScore;
    int gapScore;

    std::vector<std::vector<int>> constructMatrix(
        const std::string& query, 
        const std::string& reference);
    
    std::pair<int, int> findHighestScore(
        const std::vector<std::vector<int>>& H);
    
    std::tuple<std::string, std::string, int, double> traceback(
        const std::vector<std::vector<int>>& H,
        const std::string& query,
        const std::string& reference);

public:
    SmithWaterman(int match = 2, int mismatch = -1, int gap = -1);
    
    std::tuple<std::string, std::string, int, double> findAlignment(
        const std::string& query,
        const std::string& reference);
};

#endif
