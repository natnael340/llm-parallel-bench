package llm_written

import (
	"crypto/sha256"
	"encoding/binary"
	"flag"
	"fmt"
	"math"
	"os"
	"runtime"
	"time"
)

// hashMatrix computes a SHA256 hash of the matrix for determinism checking.
func hashMatrix(m Matrix) string {
	h := sha256.New()
	for _, row := range m {
		for _, val := range row {
			binary.Write(h, binary.LittleEndian, val)
		}
	}
	return fmt.Sprintf("%x", h.Sum(nil))
}

// matricesEqual checks if two matrices are exactly equal.
func matricesEqual(a, b Matrix) bool {
	if len(a) != len(b) {
		return false
	}
	for i := range a {
		if len(a[i]) != len(b[i]) {
			return false
		}
		for j := range a[i] {
			if a[i][j] != b[i][j] {
				return false
			}
		}
	}
	return true
}

// copyMatrix creates a deep copy of a matrix.
func copyMatrix(m Matrix) Matrix {
	if m == nil {
		return nil
	}
	rows, cols := getSize(m)
	out := generateMatrix(rows, cols)
	for i := 0; i < rows; i++ {
		copy(out[i], m[i])
	}
	return out
}

// createTestMatrix creates a test matrix with predictable values.
func createTestMatrix(rows, cols int, seed float64) Matrix {
	m := generateMatrix(rows, cols)
	for i := 0; i < rows; i++ {
		for j := 0; j < cols; j++ {
			m[i][j] = seed + float64(i*cols+j)*0.1
		}
	}
	return m
}

// TestCase represents a single test case.
type TestCase struct {
	name        string
	m, k, n     int
	alpha       float64
	beta        float64
	useBetaInit bool
}

var testCases = []TestCase{
	{"edge_1x1", 1, 1, 1, 1.0, 0.0, false},
	{"edge_1xN", 1, 4, 8, 1.0, 0.0, false},
	{"edge_Mx1", 8, 4, 1, 1.0, 0.0, false},
	{"small_8x8", 8, 8, 8, 1.0, 0.0, false},
	{"small_16x16", 16, 16, 16, 1.0, 0.0, false},
	{"small_alpha_beta", 16, 16, 16, 2.0, 0.5, true},
	{"medium_128x128", 128, 128, 128, 1.0, 0.0, false},
	{"medium_tall", 256, 64, 128, 1.0, 0.0, false},
	{"medium_wide", 64, 128, 256, 1.0, 0.0, false},
	{"large_512x512", 512, 512, 512, 1.0, 0.0, false},
}

func runCorrectnessTests() (int, int, []string) {
	passed := 0
	failed := 0
	var details []string

	fmt.Println("=== Correctness Tests ===")
	for _, tc := range testCases {
		A := createTestMatrix(tc.m, tc.k, 1.0)
		B := createTestMatrix(tc.k, tc.n, 2.0)

		var CSeq, CPar Matrix
		var err error

		// Sequential
		if tc.useBetaInit {
			CSeq = createTestMatrix(tc.m, tc.n, 3.0)
		}
		CSeqCopy := copyMatrix(CSeq)
		CSeq, err = GemmSequential(A, B, tc.alpha, CSeqCopy, tc.beta, 0, 0, 0)
		if err != nil {
			fmt.Printf("  [FAIL] %s: sequential error: %v\n", tc.name, err)
			failed++
			details = append(details, fmt.Sprintf("FAIL: %s (sequential error)", tc.name))
			continue
		}

		// Parallel
		if tc.useBetaInit {
			CPar = createTestMatrix(tc.m, tc.n, 3.0)
		}
		CParCopy := copyMatrix(CPar)
		CPar, err = Gemm(A, B, tc.alpha, CParCopy, tc.beta, 0, 0, 0)
		if err != nil {
			fmt.Printf("  [FAIL] %s: parallel error: %v\n", tc.name, err)
			failed++
			details = append(details, fmt.Sprintf("FAIL: %s (parallel error)", tc.name))
			continue
		}

		// Compare
		if matricesEqual(CSeq, CPar) {
			fmt.Printf("  [PASS] %s\n", tc.name)
			passed++
			details = append(details, fmt.Sprintf("PASS: %s", tc.name))
		} else {
			fmt.Printf("  [FAIL] %s: outputs differ\n", tc.name)
			failed++
			details = append(details, fmt.Sprintf("FAIL: %s (outputs differ)", tc.name))

			// Show first difference
			for i := 0; i < len(CSeq) && i < 5; i++ {
				for j := 0; j < len(CSeq[i]) && j < 5; j++ {
					if CSeq[i][j] != CPar[i][j] {
						fmt.Printf("    First diff at [%d][%d]: seq=%.6f, par=%.6f\n",
							i, j, CSeq[i][j], CPar[i][j])
						goto nextTest
					}
				}
			}
		nextTest:
		}
	}

	fmt.Printf("\nCorrectness: %d passed, %d failed\n\n", passed, failed)
	return passed, failed, details
}

func runDeterminismTests() (bool, []string) {
	fmt.Println("=== Determinism Tests ===")
	var details []string
	allDeterministic := true

	// Test on medium and large cases
	testSizes := []struct {
		name    string
		m, k, n int
	}{
		{"medium_128x128", 128, 128, 128},
		{"large_256x256", 256, 256, 256},
	}

	for _, ts := range testSizes {
		A := createTestMatrix(ts.m, ts.k, 1.0)
		B := createTestMatrix(ts.k, ts.n, 2.0)

		// Run 3 times
		var hashes [3]string
		for run := 0; run < 3; run++ {
			C, err := Gemm(A, B, 1.0, nil, 0.0, 0, 0, 0)
			if err != nil {
				fmt.Printf("  [FAIL] %s run %d: error: %v\n", ts.name, run+1, err)
				allDeterministic = false
				details = append(details, fmt.Sprintf("FAIL: %s run %d (error)", ts.name, run+1))
				continue
			}
			hashes[run] = hashMatrix(C)
		}

		// Compare hashes
		if hashes[0] == hashes[1] && hashes[1] == hashes[2] {
			fmt.Printf("  [PASS] %s: all 3 runs identical\n", ts.name)
			fmt.Printf("    Hash: %s\n", hashes[0][:16]+"...")
			details = append(details, fmt.Sprintf("PASS: %s (hash: %s)", ts.name, hashes[0][:16]))
		} else {
			fmt.Printf("  [FAIL] %s: runs differ\n", ts.name)
			fmt.Printf("    Run 1: %s\n", hashes[0][:16]+"...")
			fmt.Printf("    Run 2: %s\n", hashes[1][:16]+"...")
			fmt.Printf("    Run 3: %s\n", hashes[2][:16]+"...")
			allDeterministic = false
			details = append(details, fmt.Sprintf("FAIL: %s (non-deterministic)", ts.name))
		}
	}

	if allDeterministic {
		fmt.Println("\nDeterminism: PASS\n")
	} else {
		fmt.Println("\nDeterminism: FAIL\n")
	}

	return allDeterministic, details
}

func runPerformanceTests() []string {
	fmt.Println("=== Performance Tests ===")
	var details []string

	sizes := []int{256, 512}

	for _, size := range sizes {
		fmt.Printf("Testing %dx%d matrix...\n", size, size)
		A := createTestMatrix(size, size, 1.0)
		B := createTestMatrix(size, size, 2.0)

		// Sequential
		startSeq := time.Now()
		CSeq, err := GemmSequential(A, B, 1.0, nil, 0.0, 0, 0, 0)
		durSeq := time.Since(startSeq)
		if err != nil {
			fmt.Printf("  Sequential error: %v\n", err)
			continue
		}

		// Parallel (run 3 times, take best)
		var durPar time.Duration = math.MaxInt64
		var CPar Matrix
		for run := 0; run < 3; run++ {
			start := time.Now()
			CPar, err = Gemm(A, B, 1.0, nil, 0.0, 0, 0, 0)
			dur := time.Since(start)
			if err != nil {
				fmt.Printf("  Parallel run %d error: %v\n", run+1, err)
				continue
			}
			if dur < durPar {
				durPar = dur
			}
		}

		// Verify correctness
		if !matricesEqual(CSeq, CPar) {
			fmt.Printf("  [FAIL] Outputs differ!\n")
			details = append(details, fmt.Sprintf("FAIL: %dx%d (outputs differ)", size, size))
			continue
		}

		speedup := float64(durSeq) / float64(durPar)
		cores := runtime.NumCPU()
		efficiency := speedup / float64(cores) * 100.0

		fmt.Printf("  Sequential: %.2f ms\n", float64(durSeq.Microseconds())/1000.0)
		fmt.Printf("  Parallel:   %.2f ms\n", float64(durPar.Microseconds())/1000.0)
		fmt.Printf("  Speedup:    %.2fx\n", speedup)
		fmt.Printf("  Cores:      %d\n", cores)
		fmt.Printf("  Efficiency: %.1f%%\n", efficiency)

		details = append(details, fmt.Sprintf("%dx%d: seq=%.2fms, par=%.2fms, speedup=%.2fx, cores=%d, eff=%.1f%%",
			size, size,
			float64(durSeq.Microseconds())/1000.0,
			float64(durPar.Microseconds())/1000.0,
			speedup, cores, efficiency))
	}

	fmt.Println()
	return details
}

func main() {
	perfFlag := flag.Bool("perf", false, "Run performance tests")
	detFlag := flag.Bool("determinism", false, "Run determinism tests only")
	flag.Parse()

	var summaryLines []string
	exitCode := 0

	if *detFlag {
		// Determinism only
		detPass, detDetails := runDeterminismTests()
		summaryLines = append(summaryLines, "=== Determinism Test Results ===")
		summaryLines = append(summaryLines, detDetails...)
		if detPass {
			summaryLines = append(summaryLines, "\nOverall: PASS")
		} else {
			summaryLines = append(summaryLines, "\nOverall: FAIL")
			exitCode = 1
		}
	} else if *perfFlag {
		// Performance tests
		perfDetails := runPerformanceTests()
		summaryLines = append(summaryLines, "=== Performance Test Results ===")
		summaryLines = append(summaryLines, perfDetails...)

		// Write to perf.txt
		perfFile, err := os.Create("perf.txt")
		if err != nil {
			fmt.Printf("Error creating perf.txt: %v\n", err)
		} else {
			for _, line := range perfDetails {
				fmt.Fprintln(perfFile, line)
			}
			perfFile.Close()
			fmt.Println("Performance results written to perf.txt")
		}
	} else {
		// Default: correctness + determinism
		corrPass, corrFail, corrDetails := runCorrectnessTests()
		detPass, detDetails := runDeterminismTests()

		summaryLines = append(summaryLines, "=== Test Summary ===")
		summaryLines = append(summaryLines, "")
		summaryLines = append(summaryLines, "Correctness Tests:")
		summaryLines = append(summaryLines, corrDetails...)
		summaryLines = append(summaryLines, fmt.Sprintf("\nCorrectness: %d passed, %d failed", corrPass, corrFail))
		summaryLines = append(summaryLines, "")
		summaryLines = append(summaryLines, "Determinism Tests:")
		summaryLines = append(summaryLines, detDetails...)
		if detPass {
			summaryLines = append(summaryLines, "\nDeterminism: PASS")
		} else {
			summaryLines = append(summaryLines, "\nDeterminism: FAIL")
		}
		summaryLines = append(summaryLines, "")
		if corrFail == 0 && detPass {
			summaryLines = append(summaryLines, "Overall: PASS")
		} else {
			summaryLines = append(summaryLines, "Overall: FAIL")
			exitCode = 1
		}
	}

	// Write summary
	summaryFile, err := os.Create("run_summary.txt")
	if err != nil {
		fmt.Printf("Error creating run_summary.txt: %v\n", err)
		os.Exit(1)
	}
	for _, line := range summaryLines {
		fmt.Fprintln(summaryFile, line)
	}
	summaryFile.Close()
	fmt.Println("Summary written to run_summary.txt")

	os.Exit(exitCode)
}
