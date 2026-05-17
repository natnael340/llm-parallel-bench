package main

import (
	"crypto/sha256"
	"fmt"
	"os"
	"strings"
	"time"
)

func generateSequence(n int, pattern string) string {
	var sb strings.Builder
	for sb.Len() < n {
		sb.WriteString(pattern)
	}
	return sb.String()[:n]
}

func hashAlignment(alignedA, alignedB string, score int, identity float64) string {
	data := fmt.Sprintf("%s|%s|%d|%.6f", alignedA, alignedB, score, identity)
	hash := sha256.Sum256([]byte(data))
	return fmt.Sprintf("%x", hash)
}

type TestCase struct {
	name      string
	query     string
	reference string
}

func getTestCases() []TestCase {
	return []TestCase{
		{
			name:      "edge_empty",
			query:     "",
			reference: "",
		},
		{
			name:      "edge_one_empty",
			query:     "ACGT",
			reference: "",
		},
		{
			name:      "edge_single",
			query:     "A",
			reference: "A",
		},
		{
			name:      "small_exact_match",
			query:     "ACGTACGT",
			reference: "ACGTACGT",
		},
		{
			name:      "small_mismatch",
			query:     "ACGTACGT",
			reference: "TGCATGCA",
		},
		{
			name:      "small_partial",
			query:     "AGCTGACT",
			reference: "CGCTAGCT",
		},
		{
			name:      "medium_similar",
			query:     generateSequence(150, "ACGTACGT"),
			reference: generateSequence(150, "ACGTACGT"),
		},
		{
			name:      "medium_partial",
			query:     generateSequence(150, "AGCT"),
			reference: generateSequence(150, "CGTA"),
		},
		{
			name:      "large_similar",
			query:     generateSequence(500, "ACGTACGT"),
			reference: generateSequence(500, "ACGTACGT"),
		},
		{
			name:      "large_partial",
			query:     generateSequence(500, "AGCT"),
			reference: generateSequence(500, "CGTA"),
		},
	}
}

func main() {
	fmt.Println("=== Smith-Waterman Differential Test Suite ===\n")

	match := 2
	mismatch := -1
	gap := -1

	testCases := getTestCases()
	allPassed := true

	fmt.Println("Running correctness tests (sequential vs parallel)...")
	for _, tc := range testCases {
		// Sequential
		swSeq := NewSmithWatermanSeq(match, mismatch, gap)
		alignedA_seq, alignedB_seq, score_seq, identity_seq := swSeq.FindAlignment(tc.query, tc.reference)
		hashSeq := hashAlignment(alignedA_seq, alignedB_seq, score_seq, identity_seq)

		// Parallel
		swPar := NewSmithWaterman(match, mismatch, gap)
		alignedA_par, alignedB_par, score_par, identity_par := swPar.FindAlignment(tc.query, tc.reference)
		hashPar := hashAlignment(alignedA_par, alignedB_par, score_par, identity_par)

		passed := hashSeq == hashPar
		status := "✓ PASS"
		if !passed {
			status = "✗ FAIL"
			allPassed = false
		}

		fmt.Printf("  [%s] %s (q=%d, r=%d) - seq_hash=%s par_hash=%s\n",
			status, tc.name, len(tc.query), len(tc.reference), hashSeq[:8], hashPar[:8])

		if !passed {
			fmt.Printf("    SEQ: score=%d, identity=%.2f%%, alignA_len=%d, alignB_len=%d\n",
				score_seq, identity_seq, len(alignedA_seq), len(alignedB_seq))
			fmt.Printf("    PAR: score=%d, identity=%.2f%%, alignA_len=%d, alignB_len=%d\n",
				score_par, identity_par, len(alignedA_par), len(alignedB_par))
		}
	}

	fmt.Println("\nRunning determinism tests (parallel run twice)...")
	for _, tc := range testCases {
		// Skip tiny cases for determinism check
		if len(tc.query) < 10 {
			continue
		}

		swPar1 := NewSmithWaterman(match, mismatch, gap)
		alignedA1, alignedB1, score1, identity1 := swPar1.FindAlignment(tc.query, tc.reference)
		hash1 := hashAlignment(alignedA1, alignedB1, score1, identity1)

		swPar2 := NewSmithWaterman(match, mismatch, gap)
		alignedA2, alignedB2, score2, identity2 := swPar2.FindAlignment(tc.query, tc.reference)
		hash2 := hashAlignment(alignedA2, alignedB2, score2, identity2)

		passed := hash1 == hash2
		status := "✓ PASS"
		if !passed {
			status = "✗ FAIL"
			allPassed = false
		}

		fmt.Printf("  [%s] %s - run1=%s run2=%s\n", status, tc.name, hash1[:8], hash2[:8])
	}

	// Performance test on very large case
	fmt.Println("\nRunning performance test...")
	queryLarge := generateSequence(2000, "ACGTACGT")
	refLarge := generateSequence(2000, "ACGTACGT")

	swSeq := NewSmithWatermanSeq(match, mismatch, gap)
	startSeq := time.Now()
	_, _, scoreSeq, _ := swSeq.FindAlignment(queryLarge, refLarge)
	durationSeq := time.Since(startSeq).Seconds()

	swPar := NewSmithWaterman(match, mismatch, gap)
	startPar := time.Now()
	_, _, scorePar, _ := swPar.FindAlignment(queryLarge, refLarge)
	durationPar := time.Since(startPar).Seconds()

	speedup := durationSeq / durationPar
	fmt.Printf("  Large case (2000x2000): seq=%.4fs, par=%.4fs, speedup=%.2fx\n", durationSeq, durationPar, speedup)
	fmt.Printf("  Scores match: %v (seq=%d, par=%d)\n", scoreSeq == scorePar, scoreSeq, scorePar)

	// Write results to files
	summaryFile := "run_summary.txt"
	f, err := os.Create(summaryFile)
	if err != nil {
		fmt.Printf("Error creating summary file: %v\n", err)
		os.Exit(1)
	}
	defer f.Close()

	fmt.Fprintf(f, "Smith-Waterman Differential Test Results\n")
	fmt.Fprintf(f, "=========================================\n\n")
	fmt.Fprintf(f, "Correctness Tests:\n")
	for _, tc := range testCases {
		swSeq := NewSmithWatermanSeq(match, mismatch, gap)
		alignedA_seq, alignedB_seq, score_seq, identity_seq := swSeq.FindAlignment(tc.query, tc.reference)
		hashSeq := hashAlignment(alignedA_seq, alignedB_seq, score_seq, identity_seq)

		swPar := NewSmithWaterman(match, mismatch, gap)
		alignedA_par, alignedB_par, score_par, identity_par := swPar.FindAlignment(tc.query, tc.reference)
		hashPar := hashAlignment(alignedA_par, alignedB_par, score_par, identity_par)

		passed := hashSeq == hashPar
		status := "PASS"
		if !passed {
			status = "FAIL"
		}
		fmt.Fprintf(f, "  %s: %s (seq=%s, par=%s)\n", tc.name, status, hashSeq[:16], hashPar[:16])
	}

	fmt.Fprintf(f, "\nDeterminism Tests:\n")
	for _, tc := range testCases {
		if len(tc.query) < 10 {
			continue
		}

		swPar1 := NewSmithWaterman(match, mismatch, gap)
		alignedA1, alignedB1, score1, identity1 := swPar1.FindAlignment(tc.query, tc.reference)
		hash1 := hashAlignment(alignedA1, alignedB1, score1, identity1)

		swPar2 := NewSmithWaterman(match, mismatch, gap)
		alignedA2, alignedB2, score2, identity2 := swPar2.FindAlignment(tc.query, tc.reference)
		hash2 := hashAlignment(alignedA2, alignedB2, score2, identity2)

		passed := hash1 == hash2
		status := "PASS"
		if !passed {
			status = "FAIL"
		}
		fmt.Fprintf(f, "  %s: %s (run1=%s, run2=%s)\n", tc.name, status, hash1[:16], hash2[:16])
	}

	fmt.Fprintf(f, "\nPerformance Test:\n")
	fmt.Fprintf(f, "  Large case (2000x2000):\n")
	fmt.Fprintf(f, "    Sequential: %.4fs\n", durationSeq)
	fmt.Fprintf(f, "    Parallel:   %.4fs\n", durationPar)
	fmt.Fprintf(f, "    Speedup:    %.2fx\n", speedup)
	fmt.Fprintf(f, "    Scores match: %v (seq=%d, par=%d)\n", scoreSeq == scorePar, scoreSeq, scorePar)

	perfFile := "perf.txt"
	pf, err := os.Create(perfFile)
	if err != nil {
		fmt.Printf("Error creating perf file: %v\n", err)
		os.Exit(1)
	}
	defer pf.Close()

	fmt.Fprintf(pf, "Smith-Waterman Performance Results\n")
	fmt.Fprintf(pf, "==================================\n\n")
	fmt.Fprintf(pf, "Test Case: 2000x2000 sequences (N=4000000)\n")
	fmt.Fprintf(pf, "Sequential time: %.4fs\n", durationSeq)
	fmt.Fprintf(pf, "Parallel time:   %.4fs\n", durationPar)
	fmt.Fprintf(pf, "Speedup:         %.2fx\n", speedup)
	fmt.Fprintf(pf, "Scores match:    %v\n", scoreSeq == scorePar)

	fmt.Printf("\nResults written to %s and %s\n", summaryFile, perfFile)

	if !allPassed {
		fmt.Println("\n✗ Some tests FAILED")
		os.Exit(1)
	} else if speedup < 1.3 {
		fmt.Printf("\n✗ Performance gate not met: speedup %.2fx < 1.3x\n", speedup)
		os.Exit(1)
	} else {
		fmt.Println("\n✓ All tests PASSED")
		os.Exit(0)
	}
}
