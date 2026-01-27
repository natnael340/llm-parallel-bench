package main

type SmithWatermanSeq struct {
	matchScore    int
	mismatchScore int
	gapScore      int
}

func NewSmithWatermanSeq(match, mismatch, gap int) *SmithWatermanSeq {
	return &SmithWatermanSeq{
		matchScore:    match,
		mismatchScore: mismatch,
		gapScore:      gap,
	}
}

func (sw *SmithWatermanSeq) ConstructMatrix(query, reference string) [][]int {
	n := len(query) + 1
	m := len(reference) + 1

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

func (sw *SmithWatermanSeq) FindHighestScore(H [][]int) (int, int) {
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

func (sw *SmithWatermanSeq) Traceback(H [][]int, query, reference string) (string, string, int, float64) {
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

func (sw *SmithWatermanSeq) FindAlignment(query, reference string) (string, string, int, float64) {
	H := sw.ConstructMatrix(query, reference)
	return sw.Traceback(H, query, reference)
}
