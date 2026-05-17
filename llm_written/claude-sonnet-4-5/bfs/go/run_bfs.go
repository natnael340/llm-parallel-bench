package main

import (
	"fmt"
	"os"
	"time"
)

func main() {
	fmt.Println("=== BFS Test Runner ===\n")

	// Run correctness tests
	fmt.Println("Running correctness tests...")
	corrPassed, corrFailed, corrDetails := runCorrectnessTests()
	
	// Run determinism tests
	fmt.Println("Running determinism tests...")
	detPassed, detFailed, detDetails := runDeterminismTests()

	// Write summary to file
	f, err := os.Create("run_summary.txt")
	if err != nil {
		fmt.Printf("Error creating summary file: %v\n", err)
		os.Exit(1)
	}
	defer f.Close()

	f.WriteString("BFS Parallel Implementation - Test Results\n")
	f.WriteString("==========================================\n\n")
	f.WriteString(fmt.Sprintf("Test Date: %s\n\n", time.Now().Format(time.RFC3339)))

	f.WriteString("CORRECTNESS TESTS\n")
	f.WriteString("-----------------\n")
	for _, line := range corrDetails {
		f.WriteString(line + "\n")
	}
	f.WriteString(fmt.Sprintf("\nCorrectness Summary: %d passed, %d failed\n\n", corrPassed, corrFailed))

	f.WriteString("DETERMINISM TESTS\n")
	f.WriteString("-----------------\n")
	for _, line := range detDetails {
		f.WriteString(line + "\n")
	}
	f.WriteString(fmt.Sprintf("\nDeterminism Summary: %d passed, %d failed\n\n", detPassed, detFailed))

	totalTests := corrPassed + corrFailed + detPassed + detFailed
	totalPassed := corrPassed + detPassed
	totalFailed := corrFailed + detFailed

	f.WriteString("OVERALL SUMMARY\n")
	f.WriteString("---------------\n")
	f.WriteString(fmt.Sprintf("Total Tests: %d\n", totalTests))
	f.WriteString(fmt.Sprintf("Passed: %d\n", totalPassed))
	f.WriteString(fmt.Sprintf("Failed: %d\n", totalFailed))

	if totalFailed > 0 {
		f.WriteString("\nSTATUS: FAILED ❌\n")
		fmt.Println("\n❌ Tests FAILED")
		fmt.Printf("Results written to run_summary.txt\n")
		os.Exit(1)
	} else {
		f.WriteString("\nSTATUS: ALL TESTS PASSED ✓\n")
		fmt.Println("\n✓ All tests PASSED")
		fmt.Printf("Results written to run_summary.txt\n")
	}
}
