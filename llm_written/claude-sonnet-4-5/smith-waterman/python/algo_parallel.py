from typing import List, Tuple
import os
import numpy as np
from concurrent.futures import ProcessPoolExecutor


def _find_max_in_rows(args):
    """Worker function to find max score in a subset of rows."""
    H_chunk, start_row, chunk_size = args
    maxScore = 0
    maxPos = (0, 0)
    
    for i in range(chunk_size):
        for j in range(len(H_chunk[i])):
            if H_chunk[i][j] > maxScore:
                maxScore = H_chunk[i][j]
                maxPos = (start_row + i, j)
    
    return (maxScore, maxPos)


class SmithWaterman:
    def __init__(self, matchScore: int, mismatchScore: int, gapScore: int, workers: int = None):
        self.matchScore = matchScore
        self.mismatchScore = mismatchScore
        self.gapScore = gapScore
        self.workers = workers if workers is not None else min(os.cpu_count() or 1, 8)
        self.SEQUENTIAL_THRESHOLD = 50  # For sequences shorter than this, stay fully sequential
    
    def constructMatrix(self, query: str, reference: str) -> List[List[int]]:
        """
        Construct scoring matrix using NumPy for better cache locality and vectorization.
        This is inherently sequential due to data dependencies, but NumPy provides
        significant speedup over pure Python loops.
        """
        n = len(query) + 1
        m = len(reference) + 1
        
        # Use NumPy for better performance
        H = np.zeros((n, m), dtype=np.int32)
        
        # Core DP loop - must be sequential due to dependencies
        # Each cell depends on: H[i-1][j-1], H[i-1][j], H[i][j-1]
        for i in range(1, n):
            for j in range(1, m):
                match = self.matchScore if query[i-1] == reference[j-1] else self.mismatchScore
                scoreDiagonal = H[i-1, j-1] + match
                scoreUp = H[i-1, j] + self.gapScore
                scoreLeft = H[i, j-1] + self.gapScore
                
                H[i, j] = max(0, scoreDiagonal, scoreUp, scoreLeft)
        
        # Convert back to list for API compatibility
        return H.tolist()
    
    def findHighestScore(self, H: List[List[int]]) -> Tuple[int, int]:
        """
        Find maximum score in matrix using parallel reduction.
        This is embarrassingly parallel - each worker scans a subset of rows.
        """
        n = len(H)
        
        # Sequential fallback for small matrices or when below threshold
        if n < self.SEQUENTIAL_THRESHOLD or n < self.workers * 4:
            return self._findHighestScore_sequential(H)
        
        # Convert to numpy for efficient slicing
        H_np = np.array(H, dtype=np.int32)
        
        # Parallel reduction: divide rows among workers
        chunk_size = max(1, n // self.workers)
        tasks = []
        
        for w in range(self.workers):
            start_row = w * chunk_size
            end_row = min(n, (w + 1) * chunk_size) if w < self.workers - 1 else n
            if start_row < end_row:
                # Extract chunk and pass as list to avoid pickling issues
                H_chunk = H_np[start_row:end_row].tolist()
                tasks.append((H_chunk, start_row, end_row - start_row))
        
        # Execute in parallel
        with ProcessPoolExecutor(max_workers=self.workers) as executor:
            results = list(executor.map(_find_max_in_rows, tasks))
        
        # Deterministic reduction: combine in worker order
        maxScore = 0
        maxPos = (0, 0)
        for score, pos in results:
            if score > maxScore:
                maxScore = score
                maxPos = pos
        
        return maxPos
    
    def _findHighestScore_sequential(self, H: List[List[int]]) -> Tuple[int, int]:
        """Sequential max-finding using NumPy for vectorization."""
        H_np = np.array(H, dtype=np.int32)
        maxScore = np.max(H_np)
        if maxScore == 0:
            return (0, 0)
        
        # Find first occurrence (deterministic)
        maxPos = np.unravel_index(np.argmax(H_np), H_np.shape)
        return (int(maxPos[0]), int(maxPos[1]))

    def traceback(self, H: List[List[int]], query: str, reference: str) -> Tuple[str, str, float, int]:
        """Traceback remains sequential (inherently serial path-dependent operation)."""
        alignedA = []
        alignedB = []

        i, j = self.findHighestScore(H)
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
        
        percentageIdentity = (totalMatch / totalAlignment) * 100 if totalAlignment > 0 else 0
        
        return ''.join(alignedA), ''.join(alignedB), score, percentageIdentity
    
    def findAlignment(self, query: str, reference: str) -> Tuple[str, str, float, int]:
        H = self.constructMatrix(query, reference)
        return self.traceback(H, query, reference)


if __name__ == "__main__":
    # Quick sanity check
    sw = SmithWaterman(matchScore=2, mismatchScore=-1, gapScore=-1, workers=2)
    aligned_a, aligned_b, score, identity = sw.findAlignment("ACGT", "ACGT")
    print(f"Alignment: {aligned_a} / {aligned_b}, Score: {score}, Identity: {identity}%")
