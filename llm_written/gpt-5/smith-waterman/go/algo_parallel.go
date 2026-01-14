package main

import (
	"runtime"
	"sync"
)

// SmithWaterman implements the Smith-Waterman local alignment algorithm parameters.
type SmithWaterman struct {
	matchScore    int
	mismatchScore int
	gapScore      int
}

func NewSmithWaterman(match, mismatch, gap int) *SmithWaterman {
	return &SmithWaterman{
		matchScore:    match,
		mismatchScore: mismatch,
		gapScore:      gap,
	}
}

func maxInt(values ...int) int {
	maxVal := values[0]
	for _, v := range values[1:] {
		if v > maxVal {
			maxVal = v
		}
	}
	return maxVal
}

func minInt(a, b int) int { if a < b { return a }; return b }

// ConstructMatrix builds the Smith-Waterman scoring matrix sequentially.
func (sw *SmithWaterman) ConstructMatrix(query, reference string) [][]int {
	n := len(query) + 1
	m := len(reference) + 1

	// Initialize scoring matrix
	H := make([][]int, n)
	for i := range H {
		H[i] = make([]int, m)
	}

	// Fill the scoring matrix (row-major)
	for i := 1; i < n; i++ {
		for j := 1; j < m; j++ {
			var scoreDiag int
			if query[i-1] == reference[j-1] {
				scoreDiag = H[i-1][j-1] + sw.matchScore
			} else {
				scoreDiag = H[i-1][j-1] + sw.mismatchScore
			}
			scoreUp := H[i-1][j] + sw.gapScore
			scoreLeft := H[i][j-1] + sw.gapScore
			H[i][j] = maxInt(0, scoreDiag, scoreUp, scoreLeft)
		}
	}

	return H
}

// ConstructMatrixParallel builds the scoring matrix using blocked wavefront parallelism.
func (sw *SmithWaterman) ConstructMatrixParallel(query, reference string, workers int) [][]int {
	n := len(query) + 1
	m := len(reference) + 1

	H := make([][]int, n)
	for i := range H {
		H[i] = make([]int, m)
	}

	cells := (n - 1) * (m - 1)
	if cells <= 65536 { // avoid overhead on small problems
		return sw.ConstructMatrix(query, reference)
	}

	if workers <= 0 {
		workers = runtime.NumCPU()
	}
	if workers > 64 { // safety cap
		workers = 64
	}

	// Blocked wavefront
	const B = 32 // tile size
	bi := (n - 1 + B - 1) / B // number of block rows
	bj := (m - 1 + B - 1) / B // number of block cols
	if bi == 0 || bj == 0 {
		return H
	}

	kMin := 0
	kMax := (bi - 1) + (bj - 1)

	for k := kMin; k <= kMax; k++ {
		// block row index range for this diagonal
		ibStart := 0
		if k-(bj-1) > ibStart {
			ibStart = k - (bj - 1)
		}
		ibEnd := bi - 1
		if k < ibEnd {
			ibEnd = k
		}
		nBlocks := ibEnd - ibStart + 1
		if nBlocks <= 0 {
			continue
		}

		p := workers
		if nBlocks < p {
			p = nBlocks
		}

		base := nBlocks / p
		rem := nBlocks % p

		var wg sync.WaitGroup
		wg.Add(p)
		for t := 0; t < p; t++ {
			startOffset := t*base + minInt(t, rem)
			segLen := base
			if t < rem {
				segLen++
			}
			segIbStart := ibStart + startOffset
			segIbEnd := segIbStart + segLen - 1

			go func(ib0, ib1, k int) {
				defer wg.Done()
				for ib := ib0; ib <= ib1; ib++ {
					jb := k - ib
					// Determine block's top-left cell (1-based within DP area)
					i0 := 1 + ib*B
					j0 := 1 + jb*B
					// Actual block sizes (edge blocks may be smaller)
					hi := minInt(B, (n-1)-(i0-1))
					wj := minInt(B, (m-1)-(j0-1))

					// Fill this tile sequentially in row-major order
					for i := i0; i < i0+hi; i++ {
						for j := j0; j < j0+wj; j++ {
							var scoreDiag int
							if query[i-1] == reference[j-1] {
								scoreDiag = H[i-1][j-1] + sw.matchScore
							} else {
								scoreDiag = H[i-1][j-1] + sw.mismatchScore
							}
							scoreUp := H[i-1][j] + sw.gapScore
							scoreLeft := H[i][j-1] + sw.gapScore
							H[i][j] = maxInt(0, scoreDiag, scoreUp, scoreLeft)
						}
					}
				}
			}(segIbStart, segIbEnd, k)
		}
		wg.Wait()
	}

	return H
}

// FindHighestScore scans the matrix to find the coordinates of the maximum score.
func (sw *SmithWaterman) FindHighestScore(H [][]int) (int, int) {
	maxScore := 0
	maxI, maxJ := 0, 0

	n, m := len(H), len(H[0])

	for i := 0; i < n; i++ {
		for j := 0; j < m; j++ {
			if H[i][j] > maxScore {
				maxScore = H[i][j]
				maxI = i
				maxJ = j
			}
		}
	}

	return maxI, maxJ
}

// Traceback reconstructs the best local alignment from the scoring matrix.
func (sw *SmithWaterman) Traceback(H [][]int, query, reference string) (string, string, int, float64) {
	// Find the maximum score in the matrix
	i, j := sw.FindHighestScore(H)
	score := H[i][j]

	alignedA := ""
	alignedB := ""

	totalMatches := 0
	totalAlignments := 0

	for i > 0 && j > 0 {
		currentScore := H[i][j]
		if currentScore == 0 {
			break
		}

		diagonalScore := H[i-1][j-1]
		upScore := H[i-1][j]
		leftScore := H[i][j-1]

		var matchOrMismatchScore int
		if query[i-1] == reference[j-1] {
			matchOrMismatchScore = sw.matchScore
		} else {
			matchOrMismatchScore = sw.mismatchScore
		}

		if currentScore == diagonalScore+matchOrMismatchScore {
			alignedA = string(query[i-1]) + alignedA
			alignedB = string(reference[j-1]) + alignedB
			totalAlignments++
			if query[i-1] == reference[j-1] {
				totalMatches++
			}
			i--
			j--
		} else if currentScore == upScore+sw.gapScore {
			alignedA = string(query[i-1]) + alignedA
			alignedB = "-" + alignedB
			totalAlignments++
			i--
		} else if currentScore == leftScore+sw.gapScore {
			alignedA = "-" + alignedA
			alignedB = string(reference[j-1]) + alignedB
			totalAlignments++
			j--
		} else {
			break
		}
	}

	var identity float64
	if totalAlignments > 0 {
		identity = (float64(totalMatches) / float64(totalAlignments)) * 100
	} else {
		identity = 0
	}

	return alignedA, alignedB, score, identity
}

// FindAlignment uses the sequential ConstructMatrix then Traceback.
func (sw *SmithWaterman) FindAlignment(query, reference string) (string, string, int, float64) {
	H := sw.ConstructMatrix(query, reference)
	return sw.Traceback(H, query, reference)
}

// FindAlignmentParallel uses the parallel matrix construction then Traceback.
func (sw *SmithWaterman) FindAlignmentParallel(query, reference string, workers int) (string, string, int, float64) {
	H := sw.ConstructMatrixParallel(query, reference, workers)
	return sw.Traceback(H, query, reference)
}
