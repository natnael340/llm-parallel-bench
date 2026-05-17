#include "smith_waterman.h"
#include <algorithm>
#include <cstddef>
#include <vector>
#include <string>
#include <tuple>
#include <utility>
#include <cstdlib>

#ifdef _OPENMP
#include <omp.h>
#endif

// Helper: clamp threads to available cores (if OpenMP present)
static int bounded_thread_count() {
#ifdef _OPENMP
    int procs = omp_get_num_procs();
    int max_t = omp_get_max_threads();
    if (procs <= 0) procs = 1;
    if (max_t <= 0) max_t = 1;
    int t = procs < max_t ? procs : max_t;
    if (t < 1) t = 1;
    return t;
#else
    return 1;
#endif
}

SmithWaterman::SmithWaterman(int match, int mismatch, int gap)
    : matchScore(match), mismatchScore(mismatch), gapScore(gap) {}

std::vector<std::vector<int>> SmithWaterman::constructMatrix(
    const std::string& query,
    const std::string& reference) {

    const int n = static_cast<int>(query.length()) + 1;
    const int m = static_cast<int>(reference.length()) + 1;

    std::vector<std::vector<int>> H(n, std::vector<int>(m, 0));

    // Early exits and tiny-input sequential fast path
    if (n <= 1 || m <= 1) {
        return H;
    }

    // Total DP cells excluding the first row/col
    const long long work = static_cast<long long>(n - 1) * static_cast<long long>(m - 1);

    // Threshold for switching to parallel wavefront (avoid overhead on tiny cases)
    const long long PAR_THRESHOLD = 20000; // ~20k cells

    int threads = bounded_thread_count();

    bool do_parallel = (work >= PAR_THRESHOLD) && (threads > 1);

#ifndef _OPENMP
    do_parallel = false;
#endif

    if (!do_parallel) {
        // Sequential baseline fill (row-major)
        for (int i = 1; i < n; ++i) {
            for (int j = 1; j < m; ++j) {
                int scoreDiagonal = H[i-1][j-1] + (query[i-1] == reference[j-1] ? matchScore : mismatchScore);
                int scoreUp = H[i-1][j] + gapScore;
                int scoreLeft = H[i][j-1] + gapScore;
                H[i][j] = std::max({0, scoreDiagonal, scoreUp, scoreLeft});
            }
        }
        return H;
    }

#ifdef _OPENMP
    // Parallel wavefront fill along anti-diagonals (k = i + j)
    // Dependencies: each cell depends on (i-1,j-1), (i-1,j), (i,j-1) ∈ previous anti-diagonals.
    // We rely on the implicit barrier at the end of each omp for to separate diagonals.
    omp_set_num_threads(threads);

#pragma omp parallel default(none) shared(H, query, reference, n, m)
    {
        for (int k = 2; k <= (n - 1) + (m - 1); ++k) {
            int i_start = std::max(1, k - (m - 1));
            int i_end = std::min(n - 1, k - 1);
#pragma omp for schedule(static)
            for (int i = i_start; i <= i_end; ++i) {
                int j = k - i;
                // Safe because all dependencies are on diagonal k-1
                int scoreDiagonal = H[i-1][j-1] + (query[i-1] == reference[j-1] ? matchScore : mismatchScore);
                int scoreUp = H[i-1][j] + gapScore;
                int scoreLeft = H[i][j-1] + gapScore;
                H[i][j] = std::max({0, scoreDiagonal, scoreUp, scoreLeft});
            }
            // implicit barrier here (end of omp for) ensures diagonal order
        }
    }
#endif

    return H;
}

std::pair<int, int> SmithWaterman::findHighestScore(
    const std::vector<std::vector<int>>& H) {

    int maxScore = 0;
    std::pair<int, int> maxPos = {0, 0};

    for (int i = 0; i < static_cast<int>(H.size()); ++i) {
        for (int j = 0; j < static_cast<int>(H[i].size()); ++j) {
            int v = H[i][j];
            if (v > maxScore) {
                maxScore = v;
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

    std::string alignedA;
    std::string alignedB;

    auto [i, j] = findHighestScore(H);
    int score = H[i][j];

    int totalMatch = 0;
    int totalAlignment = 0;

    while (i > 0 && j > 0) {
        int currentScore = H[i][j];
        if (currentScore == 0) break;

        int diagonalScore = H[i-1][j-1];
        int upScore = H[i-1][j];
        int leftScore = H[i][j-1];

        int expectedDiagonal = diagonalScore + (query[i-1] == reference[j-1] ? matchScore : mismatchScore);

        if (currentScore == expectedDiagonal) {
            alignedA.push_back(query[i-1]);
            alignedB.push_back(reference[j-1]);
            ++totalAlignment;
            if (query[i-1] == reference[j-1]) ++totalMatch;
            --i; --j;
        } else if (currentScore == upScore + gapScore) {
            alignedA.push_back(query[i-1]);
            alignedB.push_back('-');
            ++totalAlignment;
            --i;
        } else if (currentScore == leftScore + gapScore) {
            alignedA.push_back('-');
            alignedB.push_back(reference[j-1]);
            ++totalAlignment;
            --j;
        } else {
            break;
        }
    }

    std::reverse(alignedA.begin(), alignedA.end());
    std::reverse(alignedB.begin(), alignedB.end());

    double percentageIdentity = (totalAlignment > 0)
        ? (static_cast<double>(totalMatch) / static_cast<double>(totalAlignment)) * 100.0
        : 0.0;

    return {alignedA, alignedB, score, percentageIdentity};
}

std::tuple<std::string, std::string, int, double> SmithWaterman::findAlignment(
    const std::string& query,
    const std::string& reference) {

    auto H = constructMatrix(query, reference);
    return traceback(H, query, reference);
}
