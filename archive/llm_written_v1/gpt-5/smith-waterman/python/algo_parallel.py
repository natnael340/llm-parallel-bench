import os
from typing import List, Tuple

# Try to import NumPy; fall back to pure Python sequential if unavailable
try:
    import numpy as np
except Exception:  # pragma: no cover
    np = None


# ----------------- Baseline (sequential) implementation -----------------
class SmithWatermanSequential:
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

    def findHighestScore(self, H: List[List[int]]) -> Tuple[int, int]:
        maxScore = 0
        maxPos = (0, 0)
        for i in range(len(H)):
            for j in range(len(H[i])):
                if H[i][j] > maxScore:
                    maxScore = H[i][j]
                    maxPos = (i, j)
        return maxPos

    def traceback(self, H: List[List[int]], query: str, reference: str) -> Tuple[str, str, float, int]:
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


# ----------------- Parallel (vectorized anti-diagonal) implementation -----------------
class SmithWatermanParallel(SmithWatermanSequential):
    def __init__(self, matchScore: int, mismatchScore: int, gapScore: int,
                 max_workers: int | None = None,  # unused; kept for API symmetry
                 small_n_threshold: int = 64):
        super().__init__(matchScore, mismatchScore, gapScore)
        self.max_workers = max_workers or (os.cpu_count() or 1)
        self.small_n_threshold = small_n_threshold

    def constructMatrix(self, query: str, reference: str) -> List[List[int]]:
        # Fallback to sequential if NumPy not available or tiny inputs
        n = len(query) + 1
        m = len(reference) + 1
        if np is None or max(n, m) <= self.small_n_threshold:
            return super().constructMatrix(query, reference)

        # Use NumPy arrays for fast vectorized anti-diagonal updates
        H = np.zeros((n, m), dtype=np.int32)
        q_arr = np.array(list(query), dtype='U1') if len(query) > 0 else np.array([], dtype='U1')
        r_arr = np.array(list(reference), dtype='U1') if len(reference) > 0 else np.array([], dtype='U1')

        # Iterate over anti-diagonals s = i + j
        for s in range(2, (n - 1) + (m - 1) + 1):
            i_start = max(1, s - (m - 1))
            i_end = min(n - 1, s - 1)
            L = i_end - i_start + 1
            if L <= 0:
                continue

            i_idx = np.arange(i_start, i_end + 1, dtype=np.int32)
            j_idx = s - i_idx

            up_vals = H[i_idx - 1, j_idx]
            left_vals = H[i_idx, j_idx - 1]
            diag_vals = H[i_idx - 1, j_idx - 1]

            # Characters at these positions (note: convert to 0-based indices for strings)
            q_chars = q_arr[i_idx - 1]
            r_chars = r_arr[j_idx - 1]
            eq = (q_chars == r_chars)
            match_scores = np.where(eq, self.matchScore, self.mismatchScore).astype(np.int32)

            cand1 = diag_vals + match_scores
            cand2 = up_vals + self.gapScore
            cand3 = left_vals + self.gapScore
            zeros = np.zeros(L, dtype=np.int32)

            vals = np.maximum(np.maximum(cand1, cand2), np.maximum(cand3, zeros))

            H[i_idx, j_idx] = vals

        # Convert to list of lists of ints for API compatibility
        return H.tolist()


# Small CLI utility when run directly for quick manual check
if __name__ == "__main__":
    seq = SmithWatermanSequential(2, -1, -2)
    par = SmithWatermanParallel(2, -1, -2)
    a = "ACACACTA"
    b = "AGCACACA"
    Hs = seq.constructMatrix(a, b)
    Hp = par.constructMatrix(a, b)
    print("Seq vs Par matrices equal:", Hs == Hp)
    print("Seq alignment:", seq.findAlignment(a, b))
    print("Par alignment:", par.findAlignment(a, b))
