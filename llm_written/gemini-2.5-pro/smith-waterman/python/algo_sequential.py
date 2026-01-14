from typing import List, Tuple

class SmithWaterman:
    def __init__(self, matchScore: int, mismatchScore: int, gapScore: int):
        self.matchScore = matchScore
        self.mismatchScore = mismatchScore
        self.gapScore = gapScore
    
    def constructMatrix(self, query: str, reference: str) -> List[List[int]]:
        n = len(query) + 1
        m = len(reference) + 1
        H = [[0 for _ in range (m)] for _ in range(n)]

        for i in range (1, n):
            for j in range(1, m):
                scoreDiagonal = H[i-1][j-1] + (self.matchScore if query[i-1] == reference[j-1] else self.mismatchScore)
                
                scoreUp = H[i-1][j] + self.gapScore
                scoreLeft = H[i][j-1] + self.gapScore

                H[i][j] = max(0, scoreDiagonal, scoreUp, scoreLeft)

        return H
    
    def findHighestScore(self, H: List[List[int]]) -> Tuple[int, int]:
        maxScore = 0
        maxPos = (0, 0)

        for i in range(len(H)):
            for j in range(len(H[i])):
                if H[i][j] > maxScore:
                    maxScore = H[i][j]
                    maxPos = (i, j)

        return maxPos

    def traceback(self, H: List[List[int]], query: str, reference: str) -> Tuple[str, str, int, float]:
        # Handle empty cases immediately
        if not query or not reference:
            return "", "", 0, 0.0
            
        alignedA = []
        alignedB = []

        i, j = self.findHighestScore(H)
        
        # If start position is (0,0), there's no alignment
        if i == 0 or j == 0:
            return "", "", 0, 0.0

        score = H[i][j]
        totalMatch = 0
        totalAlignment = 0

        while i > 0 and j > 0:
            currentScore = H[i][j]
            if currentScore == 0:
                break

            diagonalScore = H[i-1][j-1]
            upScore = H[i-1][j]
            leftScore = H[i][j-1]

            if currentScore == diagonalScore + (self.matchScore if query[i-1] == reference[j-1] else self.mismatchScore):
                alignedA.append(query[i-1])
                alignedB.append(reference[j-1])
                totalAlignment += 1
                if query[i-1] == reference[j-1]:
                    totalMatch += 1
                i -= 1
                j -= 1
            elif currentScore == upScore + self.gapScore:
                alignedA.append(query[i-1])
                alignedB.append('-')
                totalAlignment += 1
                i -= 1
            elif currentScore == leftScore + self.gapScore:
                alignedA.append('-')
                alignedB.append(reference[j-1])
                totalAlignment += 1
                j -= 1
            else:
                break

        alignedA.reverse()  
        alignedB.reverse()
        
        percentageIdentity = (totalMatch / totalAlignment) * 100 if totalAlignment > 0 else 0.0
        
        return ''.join(alignedA), ''.join(alignedB), int(score), float(percentageIdentity)
    
    def findAlignment(self, query: str, reference: str) -> Tuple[str, str, int, float]:
        if not query or not reference:
            return "", "", 0, 0.0
        
        H = self.constructMatrix(query, reference)
        
        return self.traceback(H, query, reference)
