
import concurrent.futures
import os
from typing import List, Tuple

# This helper function must be at the top level of the module
# to be pickleable by multiprocessing.
def _find_max_in_chunk(args: Tuple[List[List[int]], int]) -> Tuple[int, Tuple[int, int]]:
    """
    Finds the maximum value and its position in a chunk of a matrix.
    
    Args:
        args: A tuple containing:
            - matrix_chunk (List[List[int]]): A list of rows from the matrix.
            - start_row_index (int): The starting row index of this chunk in the original matrix.

    Returns:
        A tuple containing the maximum score and its (row, col) position.
    """
    matrix_chunk, start_row_index = args
    max_score = -1
    max_pos = (0, 0)
    
    # Iterate through the given chunk to find the local maximum
    for i, row in enumerate(matrix_chunk):
        try:
            # Find the max value in the row and its index
            row_max_val = max(row)
            if row_max_val > max_score:
                max_score = row_max_val
                # Find the first occurrence of the max value in the row
                j = row.index(row_max_val)
                max_pos = (start_row_index + i, j)
        except ValueError:
            # Row is empty, continue
            pass
            
    return max_score, max_pos

class SmithWaterman:
    def __init__(self, matchScore: int, mismatchScore: int, gapScore: int):
        self.matchScore = matchScore
        self.mismatchScore = mismatchScore
        self.gapScore = gapScore
    
    def constructMatrix(self, query: str, reference: str) -> List[List[int]]:
        n = len(query) + 1
        m = len(reference) + 1
        H = [[0 for _ in range(m)] for _ in range(n)]

        for i in range(1, n):
            for j in range(1, m):
                scoreDiagonal = H[i-1][j-1] + (self.matchScore if query[i-1] == reference[j-1] else self.mismatchScore)
                scoreUp = H[i-1][j] + self.gapScore
                scoreLeft = H[i][j-1] + self.gapScore
                H[i][j] = max(0, scoreDiagonal, scoreUp, scoreLeft)

        return H
    
    def _findHighestScore_sequential(self, H: List[List[int]]) -> Tuple[int, int]:
        """The original sequential implementation."""
        maxScore = 0
        maxPos = (0, 0)
        for i in range(len(H)):
            for j in range(len(H[i])):
                if H[i][j] > maxScore:
                    maxScore = H[i][j]
                    maxPos = (i, j)
        return maxPos

    def findHighestScore(self, H: List[List[int]]) -> Tuple[int, int]:
        """
        Finds the highest score in the matrix using a parallel approach.
        Falls back to a sequential implementation for small matrices.
        """
        n_rows = len(H)
        if n_rows == 0 or len(H[0]) == 0:
            return (0, 0)

        # Fallback for small matrices where parallelization overhead is not worth it.
        # Threshold: 100 rows or less, or fewer than 100,000 cells.
        if n_rows < 100 or (n_rows * len(H[0])) < 100000:
            return self._findHighestScore_sequential(H)

        num_workers = min(os.cpu_count() or 1, n_rows)
        chunk_size = (n_rows + num_workers - 1) // num_workers  # Ceiling division

        tasks = []
        for i in range(0, n_rows, chunk_size):
            end_row = min(i + chunk_size, n_rows)
            chunk = H[i:end_row]
            tasks.append((chunk, i))

        global_max_score = -1
        global_max_pos = (0, 0)

        # The main process is guarded by `if __name__ == "__main__":` in the runner.
        with concurrent.futures.ProcessPoolExecutor(max_workers=num_workers) as executor:
            # executor.map is deterministic in the order of results for the same input order.
            results = executor.map(_find_max_in_chunk, tasks)
            
            for local_max_score, local_max_pos in results:
                if local_max_score > global_max_score:
                    global_max_score = local_max_score
                    global_max_pos = local_max_pos
        
        return global_max_pos

    def traceback(self, H: List[List[int]], query: str, reference: str, start_pos: Tuple[int, int]) -> Tuple[str, str, int, float]:
        """
        Performs the traceback step from a given starting position.
        Note: This method is now decoupled from findHighestScore.
        """
        # Handle empty cases immediately
        if not query or not reference:
            return "", "", 0, 0.0

        alignedA = []
        alignedB = []

        i, j = start_pos
        
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

            match_val = self.matchScore if query[i-1] == reference[j-1] else self.mismatchScore
            if currentScore == diagonalScore + match_val:
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
        """
        Performs the full Smith-Waterman alignment, using the parallelized
        findHighestScore method.
        """
        if not query or not reference:
            return "", "", 0, 0.0
            
        H = self.constructMatrix(query, reference)
        start_pos = self.findHighestScore(H)
        return self.traceback(H, query, reference, start_pos)
