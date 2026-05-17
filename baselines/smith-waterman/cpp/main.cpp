#include <iostream>
#include "smith_waterman.h"

int main() {
    std::string seqA = "AGCTGTA";
    std::string seqB = "GCTAGTA";
    
    int matchScore = 2;
    int mismatchScore = -1;
    int gapScore = -2;
    
    SmithWaterman sw(matchScore, mismatchScore, gapScore);
    
    auto [alignedA, alignedB, score, identity] = sw.findAlignment(seqA, seqB);
    
    std::cout << "Sequence A: " << alignedA << std::endl;
    std::cout << "Sequence B: " << alignedB << std::endl;
    std::cout << "Alignment score: " << score << std::endl;
    std::cout << "Identity: " << identity << "%" << std::endl;
    
    return 0;
}