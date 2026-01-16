package main

import (
	"runtime"
	"sync"
)

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

func max(values ...int) int {
	maxVal := 0
	for _, v := range values {
		if v > maxVal {
			maxVal = v
		}
	}
	return maxVal
}

func min(a, b int) int {
	if a < b {
		return a
	}
	return b
}

func (sw *SmithWaterman) ConstructMatrix(query, reference string) [][]int {
	n := len(query) + 1
	m := len(reference) + 1

	// Initialize scoring matrix
	H := make([][]int, n)
	for i := range H {
		H[i] = make([]int, m)
	}
	for i := 0; i < n; i++ {
		H[i][0] = 0
	}
	for j := 0; j < m; j++ {
		H[0][j] = 0
	}

	// Sequential threshold: only parallelize large matrices
	matrixSize := n * m
	if matrixSize < 250000 {
		// Fill the scoring matrix sequentially
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
				H[i][j] = max(0, scoreDiag, scoreUp, scoreLeft)
			}
		}
		return H
	}

	// Block-based wavefront parallelism with large blocks
	numWorkers := runtime.NumCPU()
	blockSize := 256 // Large blocks to amortize overhead
	
	nBlocks := (n-1 + blockSize - 1) / blockSize
	mBlocks := (m-1 + blockSize - 1) / blockSize

	// Process block wavefronts (block antidiagonals)
	for bk := 0; bk < nBlocks+mBlocks-1; bk++ {
		biStart := max(0, bk-(mBlocks-1))
		biEnd := min(bk, nBlocks-1)

		numBlocks := biEnd - biStart + 1
		if numBlocks <= 0 {
			continue
		}

		// Parallelize blocks within this wavefront
		effectiveWorkers := min(numWorkers, numBlocks)
		blocksPerWorker := (numBlocks + effectiveWorkers - 1) / effectiveWorkers

		var wg sync.WaitGroup
		wg.Add(effectiveWorkers)

		for w := 0; w < effectiveWorkers; w++ {
			workerStart := biStart + w*blocksPerWorker
			workerEnd := min(workerStart+blocksPerWorker-1, biEnd)

			if workerStart > biEnd {
				wg.Done()
				continue
			}

			go func(start, end int) {
				defer wg.Done()
				for bi := start; bi <= end; bi++ {
					bj := bk - bi

					// Compute bounds for this block
					iStart := bi*blockSize + 1
					iEnd := min((bi+1)*blockSize, n-1)
					jStart := bj*blockSize + 1
					jEnd := min((bj+1)*blockSize, m-1)

					// Fill this block
					for i := iStart; i <= iEnd; i++ {
						for j := jStart; j <= jEnd; j++ {
							var scoreDiag int
							if query[i-1] == reference[j-1] {
								scoreDiag = H[i-1][j-1] + sw.matchScore
							} else {
								scoreDiag = H[i-1][j-1] + sw.mismatchScore
							}
							scoreUp := H[i-1][j] + sw.gapScore
							scoreLeft := H[i][j-1] + sw.gapScore
							H[i][j] = max(0, scoreDiag, scoreUp, scoreLeft)
						}
					}
				}
			}(workerStart, workerEnd)
		}
		wg.Wait()
	}

	return H
}

func (sw *SmithWaterman) FindHighestScore(H [][]int) (int, int) {
	n, m := len(H), len(H[0])

	// Sequential threshold
	if n*m < 250000 {
		maxScore := 0
		maxI, maxJ := 0, 0
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

	// Parallel reduction over rows
	numWorkers := runtime.NumCPU()
	rowsPerWorker := (n + numWorkers - 1) / numWorkers

	type result struct {
		score int
		i     int
		j     int
	}
	results := make([]result, numWorkers)

	var wg sync.WaitGroup
	wg.Add(numWorkers)

	for w := 0; w < numWorkers; w++ {
		rowStart := w * rowsPerWorker
		rowEnd := min(rowStart+rowsPerWorker, n)

		if rowStart >= n {
			wg.Done()
			continue
		}

		go func(worker, start, end int) {
			defer wg.Done()
			localMax := 0
			localI, localJ := 0, 0
			for i := start; i < end; i++ {
				for j := 0; j < m; j++ {
					if H[i][j] > localMax {
						localMax = H[i][j]
						localI = i
						localJ = j
					}
				}
			}
			results[worker] = result{score: localMax, i: localI, j: localJ}
		}(w, rowStart, rowEnd)
	}
	wg.Wait()

	// Fixed-order merge: process workers in sequence
	maxScore := 0
	maxI, maxJ := 0, 0
	for w := 0; w < numWorkers; w++ {
		if results[w].score > maxScore {
			maxScore = results[w].score
			maxI = results[w].i
			maxJ = results[w].j
		}
	}

	return maxI, maxJ
}

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

func (sw *SmithWaterman) FindAlignment(query, reference string) (string, string, int, float64) {
	H := sw.ConstructMatrix(query, reference)
	return sw.Traceback(H, query, reference)
}
