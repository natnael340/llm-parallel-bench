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
	"time"
)

// buildString creates a pseudo-random DNA-like string of length n using a fixed seed.
func buildString(n int, seed int64) string {
	r := rand.New(rand.NewSource(seed))
	alphabet := []rune{'A', 'C', 'G', 'T'}
	var sb strings.Builder
	sb.Grow(n)
	for i := 0; i < n; i++ {
		sb.WriteRune(alphabet[r.Intn(len(alphabet))])
	}
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

	// Sequential
	start := time.Now()
	a1, b1, s1, id1 := sw.FindAlignment(q, r)
	seqDur := time.Since(start)
	h1 := hashResult(a1, b1, s1, id1)

	// Parallel (run twice to check determinism)
	start = time.Now()
	a2, b2, s2, id2 := sw.FindAlignmentParallel(q, r, workers)
	parDur1 := time.Since(start)
	h2 := hashResult(a2, b2, s2, id2)

	a3, b3, s3, id3 := sw.FindAlignmentParallel(q, r, workers)
	h3 := hashResult(a3, b3, s3, id3)

	// Compare correctness
	if h1 != h2 {
		return "", fmt.Errorf("mismatch seq vs par: N=(%d,%d) seq=%s par=%s", n, m, h1, h2)
	}
	// Determinism
	if h2 != h3 {
		return "", fmt.Errorf("non-deterministic parallel result: N=(%d,%d) par1=%s par2=%s", n, m, h2, h3)
	}

	line := fmt.Sprintf("OK N=(%d,%d) seq=%v par=%v hash=%s cores=%d\n", n, m, seqDur, parDur1, h2, workers)

	// Perf gate for sufficiently large inputs
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
	os.WriteFile(summaryPath, []byte(""), 0o644)
	os.WriteFile(perfPath, []byte(""), 0o644)

	sw := NewSmithWaterman(2, -1, -2)

	// Scenarios: edge/small/medium/large
	cases := [][2]int{
		{0, 0},
		{1, 1},
		{8, 7},
		{64, 64},
		{256, 256},
		{1024, 1536},
	}

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

	if failed {
		os.Exit(1)
	}
}

func mustRead(path string) []byte {
	b, _ := os.ReadFile(path)
	return b
}
