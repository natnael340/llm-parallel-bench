package main

import (
	"runtime"
	"sync"
)

// The SmithWaterman struct and NewSmithWaterman constructor remain the same.
// No changes are needed here.
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

// constructMatrixSequential is the original sequential implementation.
// It is correct and will be used by both sequential and parallel versions.
func (sw *SmithWaterman) constructMatrixSequential(query, reference string) [][]int {
	n := len(query) + 1
	m := len(reference) + 1

	H := make([][]int, n)
	for i := range H {
		H[i] = make([]int, m)
	}

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

// FindHighestScore is the parallelized version.
func (sw *SmithWaterman) FindHighestScore(H [][]int) (int, int) {
	n := len(H)
	if n == 0 {
		return 0, 0
	}
	m := len(H[0])
	if n*m == 0 {
		return 0, 0
	}

	// Fallback to sequential for small inputs to avoid overhead.
	if n*m < 4096 {
		return sw.findHighestScoreSequential(H)
	}

	numWorkers := runtime.NumCPU()
	if numWorkers > n {
		numWorkers = n
	}

	results := make(chan struct {
		maxScore int
		maxI     int
		maxJ     int
	}, numWorkers)
	var wg sync.WaitGroup

	chunkSize := (n + numWorkers - 1) / numWorkers

	for i := 0; i < numWorkers; i++ {
		startRow := i * chunkSize
		endRow := startRow + chunkSize
		if endRow > n {
			endRow = n
		}
		if startRow >= endRow {
			continue
		}

		wg.Add(1)
		go func(start, end int) {
			defer wg.Done()
			localMaxScore := -1
			localMaxI, localMaxJ := 0, 0
			for i := start; i < end; i++ {
				for j := 0; j < len(H[0]); j++ {
					if H[i][j] > localMaxScore {
						localMaxScore = H[i][j]
						localMaxI = i
						localMaxJ = j
					}
				}
			}
			if localMaxScore > -1 {
				results <- struct {
					maxScore int
					maxI     int
					maxJ     int
				}{localMaxScore, localMaxI, localMaxJ}
			}
		}(startRow, endRow)
	}

	wg.Wait()
	close(results)

	maxScore := 0
	maxI, maxJ := 0, 0
	for res := range results {
		if res.maxScore > maxScore {
			maxScore = res.maxScore
			maxI = res.maxI
			maxJ = res.maxJ
		}
	}

	return maxI, maxJ
}

// findHighestScoreSequential is the original sequential implementation for finding the max score.
func (sw *SmithWaterman) findHighestScoreSequential(H [][]int) (int, int) {
	maxScore := 0
	maxI, maxJ := 0, 0
	n := len(H)
    if n == 0 {
        return 0, 0
    }
    m := len(H[0])
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


// Traceback remains sequential as it has inherent dependencies.
// It now takes the starting i, j as arguments.
func (sw *SmithWaterman) Traceback(H [][]int, query, reference string, i, j int) (string, string, int, float64) {
	if i == 0 && j == 0 { // Handle empty matrix case
		return "", "", 0, 0.0
	}
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

func min(a, b int) int {
	if a < b {
		return a
	}
	return b
}
