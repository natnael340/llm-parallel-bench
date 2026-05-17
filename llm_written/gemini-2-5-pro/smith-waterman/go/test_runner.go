package main

import (
	"crypto/sha256"
	"fmt"
	"io/ioutil"
	"os"
	"time"
)

// Aliasing the types to allow for separate sequential and parallel implementations
type SequentialSmithWaterman SmithWaterman
type ParallelSmithWaterman SmithWaterman

func NewSequentialSmithWaterman(match, mismatch, gap int) *SequentialSmithWaterman {
	return &SequentialSmithWaterman{
		matchScore:    match,
		mismatchScore: mismatch,
		gapScore:      gap,
	}
}

func (sw *SequentialSmithWaterman) FindAlignment(query, reference string) (string, string, int, float64) {
	H := (*SmithWaterman)(sw).constructMatrixSequential(query, reference)
	// For the sequential version, we call the sequential FindHighestScore
	i, j := (*SmithWaterman)(sw).findHighestScoreSequential(H)
	return (*SmithWaterman)(sw).Traceback(H, query, reference, i, j)
}

func NewParallelSmithWaterman(match, mismatch, gap int) *ParallelSmithWaterman {
	return &ParallelSmithWaterman{
		matchScore:    match,
		mismatchScore: mismatch,
		gapScore:      gap,
	}
}

func (sw *ParallelSmithWaterman) FindAlignment(query, reference string) (string, string, int, float64) {
	H := (*SmithWaterman)(sw).constructMatrixSequential(query, reference)
	// For the parallel version, we call the parallel FindHighestScore
	i, j := (*SmithWaterman)(sw).FindHighestScore(H)
	return (*SmithWaterman)(sw).Traceback(H, query, reference, i, j)
}


func generateRandomString(length int) string {
	const charset = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
	b := make([]byte, length)
	for i := range b {
		b[i] = charset[i%len(charset)]
	}
	return string(b)
}

func main() {
	runMode := "test"
	if len(os.Args) > 1 {
		runMode = os.Args[1]
	}

	matchScore, mismatchScore, gapScore := 3, -1, -2

	var query, reference string
	var testCases = map[string]struct {
		query     string
		reference string
	}{
		"empty":         {query: "", reference: ""},
		"small_identical":{query: "A", reference: "A"},
		"small_diff":   {query: "A", reference: "B"},
		"small_gap":     {query: "AG", reference: "A"},
		"medium":        {query: "AGCAT", reference: "GAC"},
		"large":         {query: generateRandomString(500), reference: generateRandomString(500)},
	}

	if runMode == "perf" {
		query = generateRandomString(2000)
		reference = generateRandomString(2000)
		testCases = map[string]struct{query string; reference string}{
			"large_perf": {query: query, reference: reference},
		}
	}

	fmt.Println("Running Differential Tests")
	fmt.Println("==========================")

	allTestsPassed := true
	var perfResults string

	for name, tc := range testCases {
		fmt.Printf("Running test case: %s\n", name)
		
		// Sequential run
		seqSW := NewSequentialSmithWaterman(matchScore, mismatchScore, gapScore)
		startSeq := time.Now()
		seqA, seqB, seqScore, seqIdentity := seqSW.FindAlignment(tc.query, tc.reference)
		durationSeq := time.Since(startSeq)
		
		// Parallel run 1
		parSW := NewParallelSmithWaterman(matchScore, mismatchScore, gapScore)
		startPar1 := time.Now()
		parA1, parB1, parScore1, parIdentity1 := parSW.FindAlignment(tc.query, tc.reference)
		durationPar1 := time.Since(startPar1)

		// Parallel run 2 (for determinism)
		parA2, parB2, parScore2, parIdentity2 := parSW.FindAlignment(tc.query, tc.reference)

		// Hashing results for determinism check
		hash1 := sha256.Sum256([]byte(fmt.Sprintf("%s-%s-%d-%.2f", parA1, parB1, parScore1, parIdentity1)))
		hash2 := sha256.Sum256([]byte(fmt.Sprintf("%s-%s-%d-%.2f", parA2, parB2, parScore2, parIdentity2)))

		// Correctness Check
		correct := seqA == parA1 && seqB == parB1 && seqScore == parScore1 && fmt.Sprintf("%.2f", seqIdentity) == fmt.Sprintf("%.2f", parIdentity1)
		
		// Determinism Check
		deterministic := hash1 == hash2

		if correct && deterministic {
			fmt.Printf("  ✅ PASS\n")
		} else {
			fmt.Printf("  ❌ FAIL\n")
			allTestsPassed = false
		}
		
		if !correct {
			fmt.Println("  Correctness failed!")
			fmt.Printf("    Sequential: (%s, %s, %d, %.2f)\n", seqA, seqB, seqScore, seqIdentity)
			fmt.Printf("    Parallel:   (%s, %s, %d, %.2f)\n", parA1, parB1, parScore1, parIdentity1)
		}
		
		if !deterministic {
			fmt.Println("  Determinism failed!")
			fmt.Printf("    Run 1 Hash: %x\n", hash1)
			fmt.Printf("    Run 2 Hash: %x\n", hash2)
		}

		if runMode == "perf" {
			speedup := float64(durationSeq) / float64(durationPar1)
			perfResults = fmt.Sprintf("N=%d, t_seq=%.4fs, t_par=%.4fs, speedup=%.2fx\n", len(tc.query), durationSeq.Seconds(), durationPar1.Seconds(), speedup)
			fmt.Println(perfResults)
		}
	}

	fmt.Println("==========================")
	if !allTestsPassed {
		fmt.Println("Some tests failed.")
		os.Exit(1)
	}
	fmt.Println("All tests passed.")
	
	// Write evidence
	os.Mkdir("evidence", 0755)
	if runMode == "perf" {
		ioutil.WriteFile("evidence/perf.txt", []byte(perfResults), 0644)
	}
	summary := fmt.Sprintf("Correctness and determinism tests passed for all cases: %v\n", keys(testCases))
	ioutil.WriteFile("evidence/run_summary.txt", []byte(summary), 0644)

}

func keys(m map[string]struct{query string; reference string}) []string {
	keys := make([]string, 0, len(m))
	for k := range m {
		keys = append(keys, k)
	}
	return keys
}
