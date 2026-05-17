#ifndef SMITH_WATERMAN_PARALLEL_H
#define SMITH_WATERMAN_PARALLEL_H

#include <iostream>
#include <string>
#include <vector>
#include <tuple>

class SmithWaterman {
public:
    SmithWaterman(int match, int mismatch, int gap);

    std::tuple<std::string, std::string, int, double> findAlignment(
        const std::string& query,
        const std::string& reference);

    std::vector<std::vector<int>> constructMatrix(
        const std::string& query,
        const std::string& reference);

    
    std::pair<int, int> findHighestScore(
    const std::vector<std::vector<int>>& H);

    std::tuple<std::string, std::string, int, double> traceback(
        const std::vector<std::vector<int>>& H,
        const std::string& query,
        const std::string& reference);

private:

    int matchScore;
    int mismatchScore;
    int gapScore;
};

#endif // SMITH_WATERMAN_PARALLEL_H
