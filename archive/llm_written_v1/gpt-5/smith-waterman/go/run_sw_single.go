package main

import (
	"crypto/sha256"
	"encoding/hex"
	"flag"
	"fmt"
	"math/rand"
	"os"
	"path/filepath"
	"runtime"
	"strings"
	"sync"
	"time"
)

// ====== Implementation (duplicated here for single-file run convenience) ======

type SmithWaterman struct {
	matchScore    int
	mismatchScore int
	gapScore      int
}

func NewSmithWaterman(match, mismatch, gap int) *SmithWaterman {
	return &SmithWaterman{matchScore: match, mismatchScore: mismatch, gapScore: gap}
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

// Sequential DP
func (sw *SmithWaterman) ConstructMatrix(query, reference string) [][]int {
	n := len(query) + 1
	m := len(reference) + 1
	H := make([][]int, n)
	for i := range H { H[i] = make([]int, m) }
	for i := 1; i < n; i++ {
		for j := 1; j < m; j++ {
			var scoreDiag int
			if query[i-1] == reference[j-1] { scoreDiag = H[i-1][j-1] + sw.matchScore } else { scoreDiag = H[i-1][j-1] + sw.mismatchScore }
			scoreUp := H[i-1][j] + sw.gapScore
			scoreLeft := H[i][j-1] + sw.gapScore
			H[i][j] = maxInt(0, scoreDiag, scoreUp, scoreLeft)
		}
	}
	return H
}

// Parallel DP using anti-diagonals
func (sw *SmithWaterman) ConstructMatrixParallel(query, reference string, workers int) [][]int {
	n := len(query) + 1
	m := len(reference) + 1
	H := make([][]int, n)
	for i := range H { H[i] = make([]int, m) }
	cells := (n - 1) * (m - 1)
	if cells <= 8192 { return sw.ConstructMatrix(query, reference) }
	if workers <= 0 { workers = runtime.NumCPU() }
	if workers > 64 { workers = 64 }
	kMin := 2
	kMax := (n - 1) + (m - 1)
	for k := kMin; k <= kMax; k++ {
		iStart := 1
		if k-(m-1) > iStart { iStart = k - (m - 1) }
		iEnd := n - 1
		if k-1 < iEnd { iEnd = k - 1 }
		count := iEnd - iStart + 1
		if count <= 0 { continue }
		p := workers
		if count < p { p = count }
		base := count / p
		rem := count % p
		var wg sync.WaitGroup
		wg.Add(p)
		for t := 0; t < p; t++ {
			startOffset := t*base + minInt(t, rem)
			segLen := base
			if t < rem { segLen++ }
			segIStart := iStart + startOffset
			segIEnd := segIStart + segLen - 1
			go func(i0, i1, k int) {
				defer wg.Done()
				for i := i0; i <= i1; i++ {
					j := k - i
					var scoreDiag int
					if query[i-1] == reference[j-1] { scoreDiag = H[i-1][j-1] + sw.matchScore } else { scoreDiag = H[i-1][j-1] + sw.mismatchScore }
					scoreUp := H[i-1][j] + sw.gapScore
					scoreLeft := H[i][j-1] + sw.gapScore
					H[i][j] = maxInt(0, scoreDiag, scoreUp, scoreLeft)
				}
			}(segIStart, segIEnd, k)
		}
		wg.Wait()
	}
	return H
}

func (sw *SmithWaterman) FindHighestScore(H [][]int) (int, int) {
	maxScore := 0
	maxI, maxJ := 0, 0
	n, m := len(H), len(H[0])
	for i := 0; i < n; i++ {
		for j := 0; j < m; j++ {
			if H[i][j] > maxScore { maxScore = H[i][j]; maxI = i; maxJ = j }
		}
	}
	return maxI, maxJ
}

func (sw *SmithWaterman) Traceback(H [][]int, query, reference string) (string, string, int, float64) {
	i, j := sw.FindHighestScore(H)
	score := H[i][j]
	alignedA, alignedB := "", ""
	totalMatches, totalAlignments := 0, 0
	for i > 0 && j > 0 {
		currentScore := H[i][j]
		if currentScore == 0 { break }
		diagonalScore := H[i-1][j-1]
		upScore := H[i-1][j]
		leftScore := H[i][j-1]
		var matchOrMismatchScore int
		if query[i-1] == reference[j-1] { matchOrMismatchScore = sw.matchScore } else { matchOrMismatchScore = sw.mismatchScore }
		if currentScore == diagonalScore+matchOrMismatchScore {
			alignedA = string(query[i-1]) + alignedA
			alignedB = string(reference[j-1]) + alignedB
			totalAlignments++
			if query[i-1] == reference[j-1] { totalMatches++ }
			i--; j--
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
		} else { break }
	}
	var identity float64
	if totalAlignments > 0 { identity = (float64(totalMatches) / float64(totalAlignments)) * 100 } else { identity = 0 }
	return alignedA, alignedB, score, identity
}

func (sw *SmithWaterman) FindAlignment(q, r string) (string, string, int, float64) {
	H := sw.ConstructMatrix(q, r)
	return sw.Traceback(H, q, r)
}

func (sw *SmithWaterman) FindAlignmentParallel(q, r string, workers int) (string, string, int, float64) {
	H := sw.ConstructMatrixParallel(q, r, workers)
	return sw.Traceback(H, q, r)
}

// ====== Test runner and evidence ======

func buildString(n int, seed int64) string {
	r := rand.New(rand.NewSource(seed))
	alphabet := []rune{'A', 'C', 'G', 'T'}
	var sb strings.Builder
	sb.Grow(n)
	for i := 0; i < n; i++ { sb.WriteRune(alphabet[r.Intn(len(alphabet))]) }
	return sb.String()
}

func hashResult(a, b string, score int, id float64) string {
	data := fmt.Sprintf("%s|%s|%d|%.6f", a, b, score, id)
	sum := sha256.Sum256([]byte(data))
	return hex.EncodeToString(sum[:])
}

func runCase(n, m int, sw *SmithWaterman, workers int) (string, error) {
	q := buildString(n, 42)
	r := buildString(m, 99)
	start := time.Now()
	a1, b1, s1, id1 := sw.FindAlignment(q, r)
	seqDur := time.Since(start)
	h1 := hashResult(a1, b1, s1, id1)
	start = time.Now()
	a2, b2, s2, id2 := sw.FindAlignmentParallel(q, r, workers)
	parDur1 := time.Since(start)
	h2 := hashResult(a2, b2, s2, id2)
	a3, b3, s3, id3 := sw.FindAlignmentParallel(q, r, workers)
	h3 := hashResult(a3, b3, s3, id3)
	if h1 != h2 {
		return "", fmt.Errorf("mismatch seq vs par: N=(%d,%d) seq=%s par=%s", n, m, h1, h2)
	}
	if h2 != h3 {
		return "", fmt.Errorf("non-deterministic parallel result: N=(%d,%d) par1=%s par2=%s", n, m, h2, h3)
	}
	line := fmt.Sprintf("OK N=(%d,%d) seq=%v par=%v hash=%s cores=%d\n", n, m, seqDur, parDur1, h2, workers)
	// Perf gate
	if n*m >= 200000 && workers > 1 {
		spd := float64(seqDur) / float64(parDur1)
		line += fmt.Sprintf("SPEEDUP N=(%d,%d) seq=%v par=%v speedup=%.2f\n", n, m, seqDur, parDur1, spd)
	}
	return line, nil
}

func main() {
	workers := flag.Int("workers", runtime.NumCPU(), "number of parallel workers")
	flag.Parse()
	_ = os.MkdirAll("evidence", 0o755)
	summaryPath := filepath.Join("evidence", "run_summary.txt")
	perfPath := filepath.Join("evidence", "perf.txt")
	// Truncate files
	os.WriteFile(summaryPath, []byte(""), 0o644)
	os.WriteFile(perfPath, []byte(""), 0o644)

	sw := NewSmithWaterman(2, -1, -2)
	cases := [][2]int{{0,0},{1,1},{8,7},{64,64},{256,256},{512,800}}
	var failed bool
	for _, c := range cases {
		line, err := runCase(c[0], c[1], sw, *workers)
		if err != nil {
			fmt.Fprintln(os.Stderr, "FAIL:", err)
			failed = true
			line = fmt.Sprintf("FAIL N=(%d,%d) %v\n", c[0], c[1], err)
		}
		fmt.Print(line)
		// Append to evidence files
		os.WriteFile(summaryPath, append(mustRead(summaryPath), []byte(line)...), 0o644)
		if strings.HasPrefix(line, "SPEEDUP") || strings.Contains(line, "speedup=") {
			os.WriteFile(perfPath, append(mustRead(perfPath), []byte(line)...), 0o644)
		}
	}
	if failed { os.Exit(1) }
}

func mustRead(path string) []byte {
	b, _ := os.ReadFile(path)
	return b
}
