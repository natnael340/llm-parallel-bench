package main

import (
	"bufio"
	"math"
	"os"
	"strconv"
	"strings"
	"testing"
	"time"
)

const epsilon = 1e-6

// Helper function to check if two floats are approximately equal
func almostEqual(a, b, delta float64) bool {
	return math.Abs(a-b) <= delta
}

// ==================== Basic Functionality Tests ====================

func TestPerfectMatch(t *testing.T) {
	sw := NewSmithWaterman(2, -1, -1)
	query := "ACGT"
	reference := "ACGT"

	alignedA, alignedB, score, identity := sw.FindAlignment(query, reference)

	if alignedA != alignedB {
		t.Errorf("Expected alignedA == alignedB, got %s != %s", alignedA, alignedB)
	}
	if score != 8 {
		t.Errorf("Expected score 8, got %d", score)
	}
	if !almostEqual(identity, 100.0, epsilon) {
		t.Errorf("Expected identity 100.0, got %f", identity)
	}
}

func TestNoMatch(t *testing.T) {
	sw := NewSmithWaterman(2, -1, -1)
	query := "AAAA"
	reference := "TTTT"

	alignedA, alignedB, score, identity := sw.FindAlignment(query, reference)

	if alignedA != "" {
		t.Errorf("Expected empty alignedA, got %s", alignedA)
	}
	if alignedB != "" {
		t.Errorf("Expected empty alignedB, got %s", alignedB)
	}
	if score != 0 {
		t.Errorf("Expected score 0, got %d", score)
	}
	if !almostEqual(identity, 0.0, epsilon) {
		t.Errorf("Expected identity 0.0, got %f", identity)
	}
}

func TestPartialMatch(t *testing.T) {
	sw := NewSmithWaterman(2, -1, -1)
	query := "ACGTACGT"
	reference := "TACGTGCA"

	alignedA, alignedB, score, identity := sw.FindAlignment(query, reference)

	if len(alignedA) != len(alignedB) {
		t.Errorf("Expected equal length alignments")
	}
	if alignedA != "TACGT" {
		t.Errorf("Expected alignedA 'TACGT', got %s", alignedA)
	}
	if alignedB != "TACGT" {
		t.Errorf("Expected alignedB 'TACGT', got %s", alignedB)
	}
	if score != 10 {
		t.Errorf("Expected score 10, got %d", score)
	}
	if !almostEqual(identity, 100.0, epsilon) {
		t.Errorf("Expected identity 100.0, got %f", identity)
	}
}

func TestGapInQuery(t *testing.T) {
	sw := NewSmithWaterman(2, -1, -1)
	query := "ACGT"
	reference := "ACAGT"

	alignedA, alignedB, score, identity := sw.FindAlignment(query, reference)

	if alignedA != "AC-GT" {
		t.Errorf("Expected alignedA 'AC-GT', got %s", alignedA)
	}
	if alignedB != "ACAGT" {
		t.Errorf("Expected alignedB 'ACAGT', got %s", alignedB)
	}
	if score != 7 {
		t.Errorf("Expected score 7, got %d", score)
	}
	if !almostEqual(identity, 80.0, epsilon) {
		t.Errorf("Expected identity 80.0, got %f", identity)
	}
}

func TestGapInReference(t *testing.T) {
	sw := NewSmithWaterman(2, -1, -1)
	query := "ACAGT"
	reference := "ACGT"

	alignedA, alignedB, score, identity := sw.FindAlignment(query, reference)

	if alignedB != "AC-GT" {
		t.Errorf("Expected alignedB 'AC-GT', got %s", alignedB)
	}
	if alignedA != "ACAGT" {
		t.Errorf("Expected alignedA 'ACAGT', got %s", alignedA)
	}
	if score != 7 {
		t.Errorf("Expected score 7, got %d", score)
	}
	if !almostEqual(identity, 80.0, epsilon) {
		t.Errorf("Expected identity 80.0, got %f", identity)
	}
}

// ==================== Edge Cases ====================

func TestEmptyQuery(t *testing.T) {
	sw := NewSmithWaterman(2, -1, -1)
	query := ""
	reference := "ACGT"

	H := sw.ConstructMatrix(query, reference)
	if len(H) != 1 {
		t.Errorf("Expected matrix length 1, got %d", len(H))
	}

	alignedA, alignedB, score, identity := sw.Traceback(H, query, reference)
	if alignedA != "" || alignedB != "" {
		t.Errorf("Expected empty alignments")
	}
	if score != 0 {
		t.Errorf("Expected score 0, got %d", score)
	}
	if !almostEqual(identity, 0.0, epsilon) {
		t.Errorf("Expected identity 0.0, got %f", identity)
	}
}

func TestEmptyReference(t *testing.T) {
	sw := NewSmithWaterman(2, -1, -1)
	query := "ACGT"
	reference := ""

	H := sw.ConstructMatrix(query, reference)
	if len(H[0]) != 1 {
		t.Errorf("Expected matrix column length 1, got %d", len(H[0]))
	}

	alignedA, alignedB, score, identity := sw.Traceback(H, query, reference)
	if alignedA != "" || alignedB != "" {
		t.Errorf("Expected empty alignments")
	}
	if score != 0 {
		t.Errorf("Expected score 0, got %d", score)
	}
	if !almostEqual(identity, 0.0, epsilon) {
		t.Errorf("Expected identity 0.0, got %f", identity)
	}
}

func TestBothEmpty(t *testing.T) {
	sw := NewSmithWaterman(2, -1, -1)
	query := ""
	reference := ""

	H := sw.ConstructMatrix(query, reference)
	if len(H) != 1 || len(H[0]) != 1 {
		t.Errorf("Expected 1x1 matrix")
	}

	alignedA, alignedB, score, identity := sw.Traceback(H, query, reference)
	if alignedA != "" || alignedB != "" {
		t.Errorf("Expected empty alignments")
	}
	if score != 0 {
		t.Errorf("Expected score 0, got %d", score)
	}
	if !almostEqual(identity, 0.0, epsilon) {
		t.Errorf("Expected identity 0.0, got %f", identity)
	}
}

func TestSingleCharacterMatch(t *testing.T) {
	sw := NewSmithWaterman(2, -1, -1)
	query := "A"
	reference := "A"

	alignedA, alignedB, score, identity := sw.FindAlignment(query, reference)

	if alignedA != "A" {
		t.Errorf("Expected alignedA 'A', got %s", alignedA)
	}
	if alignedB != "A" {
		t.Errorf("Expected alignedB 'A', got %s", alignedB)
	}
	if score != 2 {
		t.Errorf("Expected score 2, got %d", score)
	}
	if !almostEqual(identity, 100.0, epsilon) {
		t.Errorf("Expected identity 100.0, got %f", identity)
	}
}

func TestSingleCharacterMismatch(t *testing.T) {
	sw := NewSmithWaterman(2, -1, -1)
	query := "A"
	reference := "T"

	alignedA, alignedB, score, identity := sw.FindAlignment(query, reference)

	if alignedA != "" {
		t.Errorf("Expected empty alignedA, got %s", alignedA)
	}
	if alignedB != "" {
		t.Errorf("Expected empty alignedB, got %s", alignedB)
	}
	if score != 0 {
		t.Errorf("Expected score 0, got %d", score)
	}
	if !almostEqual(identity, 0.0, epsilon) {
		t.Errorf("Expected identity 0.0, got %f", identity)
	}
}

func TestQueryMuchLonger(t *testing.T) {
	sw := NewSmithWaterman(2, -1, -1)
	query := "ACGTACGTACGTACGT"
	reference := "ACG"

	alignedA, alignedB, score, identity := sw.FindAlignment(query, reference)

	if len(alignedA) != len(alignedB) {
		t.Errorf("Expected equal length alignments")
	}
	if alignedB != "ACG" {
		t.Errorf("Expected alignedB 'ACG', got %s", alignedB)
	}
	if alignedA != "ACG" {
		t.Errorf("Expected alignedA 'ACG', got %s", alignedA)
	}
	if score != 6 {
		t.Errorf("Expected score 6, got %d", score)
	}
	if !almostEqual(identity, 100.0, epsilon) {
		t.Errorf("Expected identity 100.0, got %f", identity)
	}
}

func TestReferenceMuchLonger(t *testing.T) {
	sw := NewSmithWaterman(2, -1, -1)
	query := "ACG"
	reference := "ACGTACGTACGTACGT"

	alignedA, alignedB, score, identity := sw.FindAlignment(query, reference)

	if len(alignedA) != len(alignedB) {
		t.Errorf("Expected equal length alignments")
	}
	if alignedB != "ACG" {
		t.Errorf("Expected alignedB 'ACG', got %s", alignedB)
	}
	if alignedA != "ACG" {
		t.Errorf("Expected alignedA 'ACG', got %s", alignedA)
	}
	if score != 6 {
		t.Errorf("Expected score 6, got %d", score)
	}
	if !almostEqual(identity, 100.0, epsilon) {
		t.Errorf("Expected identity 100.0, got %f", identity)
	}
}

// ==================== Matrix Construction Tests ====================

func TestMatrixDimensions(t *testing.T) {
	sw := NewSmithWaterman(2, -1, -1)
	query := "ACGT"
	reference := "TAGC"

	H := sw.ConstructMatrix(query, reference)

	if len(H) != len(query)+1 {
		t.Errorf("Expected matrix rows %d, got %d", len(query)+1, len(H))
	}
	if len(H[0]) != len(reference)+1 {
		t.Errorf("Expected matrix cols %d, got %d", len(reference)+1, len(H[0]))
	}
}

func TestMatrixFirstRowColumnZeros(t *testing.T) {
	sw := NewSmithWaterman(2, -1, -1)
	query := "ACGT"
	reference := "TAGC"

	H := sw.ConstructMatrix(query, reference)

	// Check first row
	for _, val := range H[0] {
		if val != 0 {
			t.Errorf("Expected 0 in first row, got %d", val)
		}
	}

	// Check first column
	for _, row := range H {
		if row[0] != 0 {
			t.Errorf("Expected 0 in first column, got %d", row[0])
		}
	}
}

func TestMatrixNonNegativeValues(t *testing.T) {
	sw := NewSmithWaterman(2, -1, -1)
	query := "ACGTTAGC"
	reference := "GCATACGT"

	H := sw.ConstructMatrix(query, reference)

	for _, row := range H {
		for _, val := range row {
			if val < 0 {
				t.Errorf("Expected non-negative value, got %d", val)
			}
		}
	}
}

func TestFindHighestScoreSimple(t *testing.T) {
	sw := NewSmithWaterman(2, -1, -1)
	query := "AC"
	reference := "AC"

	H := sw.ConstructMatrix(query, reference)
	i, j := sw.FindHighestScore(H)

	// Highest score should be at bottom-right for perfect match
	if i != 2 || j != 2 {
		t.Errorf("Expected position (2, 2), got (%d, %d)", i, j)
	}
}

func TestFindHighestScoreZeroMatrix(t *testing.T) {
	sw := NewSmithWaterman(2, -1, -1)
	H := [][]int{
		{0, 0, 0},
		{0, 0, 0},
		{0, 0, 0},
	}

	i, j := sw.FindHighestScore(H)
	if i != 0 || j != 0 {
		t.Errorf("Expected position (0, 0), got (%d, %d)", i, j)
	}
}

// ==================== Different Scoring Schemes ====================

func TestHighGapPenalty(t *testing.T) {
	sw := NewSmithWaterman(3, -3, -2)
	query := "ACGT"
	reference := "ACAGT"

	alignedA, alignedB, score, identity := sw.FindAlignment(query, reference)

	if len(alignedA) != len(alignedB) {
		t.Errorf("Expected equal length alignments")
	}
	if alignedA != "AC-GT" {
		t.Errorf("Expected alignedA 'AC-GT', got %s", alignedA)
	}
	if alignedB != "ACAGT" {
		t.Errorf("Expected alignedB 'ACAGT', got %s", alignedB)
	}
	if score != 10 {
		t.Errorf("Expected score 10, got %d", score)
	}
	if !almostEqual(identity, 80.0, epsilon) {
		t.Errorf("Expected identity 80.0, got %f", identity)
	}
}

func TestNegativeMatchScore(t *testing.T) {
	sw := NewSmithWaterman(-1, -2, -1)
	query := "ACGT"
	reference := "ACGT"

	H := sw.ConstructMatrix(query, reference)

	// All values should remain zero due to Smith-Waterman's max(0, ...) constraint
	for _, row := range H {
		for _, val := range row {
			if val != 0 {
				t.Errorf("Expected all zeros, got %d", val)
			}
		}
	}
}

// ==================== Special Character Tests ====================

func TestLowercaseSequences(t *testing.T) {
	sw := NewSmithWaterman(2, -1, -1)
	query := "acgt"
	reference := "acgt"

	alignedA, alignedB, score, identity := sw.FindAlignment(query, reference)

	if alignedA != "acgt" {
		t.Errorf("Expected alignedA 'acgt', got %s", alignedA)
	}
	if alignedB != "acgt" {
		t.Errorf("Expected alignedB 'acgt', got %s", alignedB)
	}
	if score != 8 {
		t.Errorf("Expected score 8, got %d", score)
	}
	if !almostEqual(identity, 100.0, epsilon) {
		t.Errorf("Expected identity 100.0, got %f", identity)
	}
}

func TestMixedCaseSequences(t *testing.T) {
	sw := NewSmithWaterman(2, -1, -1)
	query := "AcGt"
	reference := "aCgT"

	alignedA, alignedB, score, identity := sw.FindAlignment(query, reference)

	if len(alignedA) != len(alignedB) {
		t.Errorf("Expected equal length alignments")
	}
	if alignedA != "" {
		t.Errorf("Expected empty alignedA, got %s", alignedA)
	}
	if alignedB != "" {
		t.Errorf("Expected empty alignedB, got %s", alignedB)
	}
	if score != 0 {
		t.Errorf("Expected score 0, got %d", score)
	}
	if !almostEqual(identity, 0.0, epsilon) {
		t.Errorf("Expected identity 0.0, got %f", identity)
	}
}

func TestNumericCharacters(t *testing.T) {
	sw := NewSmithWaterman(2, -1, -1)
	query := "123"
	reference := "123"

	alignedA, alignedB, score, identity := sw.FindAlignment(query, reference)

	if alignedA != "123" {
		t.Errorf("Expected alignedA '123', got %s", alignedA)
	}
	if alignedB != "123" {
		t.Errorf("Expected alignedB '123', got %s", alignedB)
	}
	if score != 6 {
		t.Errorf("Expected score 6, got %d", score)
	}
	if !almostEqual(identity, 100.0, epsilon) {
		t.Errorf("Expected identity 100.0, got %f", identity)
	}
}

func TestSpecialCharacters(t *testing.T) {
	sw := NewSmithWaterman(2, -1, -1)
	query := "A-C*G"
	reference := "A-C*G"

	alignedA, alignedB, score, identity := sw.FindAlignment(query, reference)

	if alignedA != "A-C*G" {
		t.Errorf("Expected alignedA 'A-C*G', got %s", alignedA)
	}
	if alignedB != "A-C*G" {
		t.Errorf("Expected alignedB 'A-C*G', got %s", alignedB)
	}
	if score != 10 {
		t.Errorf("Expected score 10, got %d", score)
	}
	if !almostEqual(identity, 100.0, epsilon) {
		t.Errorf("Expected identity 100.0, got %f", identity)
	}
}

// ==================== Repetitive Patterns ====================

func TestRepeatedCharacters(t *testing.T) {
	sw := NewSmithWaterman(2, -1, -1)
	query := "AAAA"
	reference := "AAAA"

	alignedA, alignedB, score, identity := sw.FindAlignment(query, reference)

	if alignedA != "AAAA" {
		t.Errorf("Expected alignedA 'AAAA', got %s", alignedA)
	}
	if alignedB != "AAAA" {
		t.Errorf("Expected alignedB 'AAAA', got %s", alignedB)
	}
	if score != 8 {
		t.Errorf("Expected score 8, got %d", score)
	}
	if !almostEqual(identity, 100.0, epsilon) {
		t.Errorf("Expected identity 100.0, got %f", identity)
	}
}

func TestTandemRepeats(t *testing.T) {
	sw := NewSmithWaterman(2, -1, -1)
	query := "ACGTACGTACGT"
	reference := "ACGTACGTACGT"

	alignedA, alignedB, score, identity := sw.FindAlignment(query, reference)

	if alignedA != query {
		t.Errorf("Expected alignedA '%s', got %s", query, alignedA)
	}
	if alignedB != reference {
		t.Errorf("Expected alignedB '%s', got %s", reference, alignedB)
	}
	if score != 24 {
		t.Errorf("Expected score 24, got %d", score)
	}
	if !almostEqual(identity, 100.0, epsilon) {
		t.Errorf("Expected identity 100.0, got %f", identity)
	}
}

// ==================== Alignment Properties Tests ====================

func TestAlignmentLengthsEqual(t *testing.T) {
	sw := NewSmithWaterman(2, -1, -1)

	testCases := []struct {
		query      string
		reference  string
		expectedA  string
		expectedB  string
	}{
		{"ACGT", "TAGC", "A-C", "AGC"},
		{"AAAA", "TTTT", "", ""},
		{"ACGTACGT", "ACGT", "ACGT", "ACGT"},
		{"A", "ACGTACGT", "A", "A"},
		{"ACGTNNACGT", "ACGTACGT", "ACGTNNACGT", "ACGT--ACGT"},
	}

	for _, tc := range testCases {
		t.Run(tc.query+"_"+tc.reference, func(t *testing.T) {
			alignedA, alignedB, _, _ := sw.FindAlignment(tc.query, tc.reference)

			if len(alignedA) != len(alignedB) {
				t.Errorf("Expected equal length alignments")
			}
			if alignedA != tc.expectedA {
				t.Errorf("Expected alignedA '%s', got '%s'", tc.expectedA, alignedA)
			}
			if alignedB != tc.expectedB {
				t.Errorf("Expected alignedB '%s', got '%s'", tc.expectedB, alignedB)
			}
		})
	}
}

func TestNoDoubleGaps(t *testing.T) {
	sw := NewSmithWaterman(2, -1, -1)
	query := "ACGTACGT"
	reference := "TAGCTAGC"

	alignedA, alignedB, score, identity := sw.FindAlignment(query, reference)

	if len(alignedA) != len(alignedB) {
		t.Errorf("Expected equal length alignments")
	}
	if alignedA != "A-CGTA-C" {
		t.Errorf("Expected alignedA 'A-CGTA-C', got %s", alignedA)
	}
	if alignedB != "AGC-TAGC" {
		t.Errorf("Expected alignedB 'AGC-TAGC', got %s", alignedB)
	}
	if score != 7 {
		t.Errorf("Expected score 7, got %d", score)
	}
	if !almostEqual(identity, 62.5, epsilon) {
		t.Errorf("Expected identity 62.5, got %f", identity)
	}
}

// ==================== Real Biological Sequences ====================

func TestRealisticDNASequences(t *testing.T) {
	sw := NewSmithWaterman(2, -1, -1)
	query := "ATCGATCGATCG"
	reference := "ATCGATCGATCG"

	alignedA, alignedB, score, identity := sw.FindAlignment(query, reference)

	if alignedA != query {
		t.Errorf("Expected alignedA '%s', got %s", query, alignedA)
	}
	if alignedB != reference {
		t.Errorf("Expected alignedB '%s', got %s", reference, alignedB)
	}
	if score != 24 {
		t.Errorf("Expected score 24, got %d", score)
	}
	if !almostEqual(identity, 100.0, epsilon) {
		t.Errorf("Expected identity 100.0, got %f", identity)
	}
}

func TestDNAWithSingleMutation(t *testing.T) {
	sw := NewSmithWaterman(2, -1, -1)
	query := "ATCGATCGATCG"
	reference := "ATCGTTCGATCG" // T instead of A at position 5

	alignedA, alignedB, score, identity := sw.FindAlignment(query, reference)

	if len(alignedA) <= 8 {
		t.Errorf("Expected alignment length > 8, got %d", len(alignedA))
	}
	if len(alignedA) != len(alignedB) {
		t.Errorf("Expected equal length alignments")
	}
	if score != 21 {
		t.Errorf("Expected score 21, got %d", score)
	}
	if !almostEqual(identity, 91.66666666666666, epsilon) {
		t.Errorf("Expected identity 91.67, got %f", identity)
	}
}

// ==================== Large Input Tests ====================

func TestLargeSequencesFromFile(t *testing.T) {
	sw := NewSmithWaterman(2, -1, -1)

	file, err := os.Open("large_test_input.txt")
	if err != nil {
		t.Skip("large_test_input.txt not found")
		return
	}
	defer file.Close()

	scanner := bufio.NewScanner(file)
	scanner.Buffer(make([]byte, 1024*1024), 1024*1024*10) // Increase buffer size

	var lines []string
	for scanner.Scan() {
		lines = append(lines, scanner.Text())
	}

	if len(lines) < 4 {
		t.Fatal("Expected at least 4 lines in large_test_input.txt")
	}

	query := strings.TrimSpace(lines[0])
	reference := strings.TrimSpace(lines[1])
	expectedScore, _ := strconv.Atoi(strings.TrimSpace(lines[2]))
	expectedIdentity, _ := strconv.ParseFloat(strings.TrimSpace(lines[3]), 64)

	// Test matrix construction completes
	H := sw.ConstructMatrix(query, reference)
	if H == nil {
		t.Fatal("Matrix construction failed")
	}

	// Test dimensions
	if len(H) != len(query)+1 {
		t.Errorf("Expected matrix rows %d, got %d", len(query)+1, len(H))
	}
	if len(H[0]) != len(reference)+1 {
		t.Errorf("Expected matrix cols %d, got %d", len(reference)+1, len(H[0]))
	}

	// Test traceback completes
	alignedA, alignedB, score, identity := sw.Traceback(H, query, reference)
	if len(alignedA) != len(alignedB) {
		t.Errorf("Expected equal length alignments")
	}
	if score != expectedScore {
		t.Errorf("Expected score %d, got %d", expectedScore, score)
	}
	if !almostEqual(identity, expectedIdentity, epsilon) {
		t.Errorf("Expected identity %f, got %f", expectedIdentity, identity)
	}
}

func TestPerformanceMediumSequences(t *testing.T) {
	sw := NewSmithWaterman(2, -1, -1)

	// 200 characters each
	query := strings.Repeat("ACGT", 50)
	reference := strings.Repeat("TAGC", 50)

	// Test matrix construction time
	start := time.Now()
	H := sw.ConstructMatrix(query, reference)
	matrixTime := time.Since(start)

	// Test traceback time
	start = time.Now()
	_, _, _, _ = sw.Traceback(H, query, reference)
	tracebackTime := time.Since(start)

	// These are reasonable time limits
	if matrixTime > 5*time.Second {
		t.Errorf("Matrix construction took too long: %v", matrixTime)
	}
	if tracebackTime > 2*time.Second {
		t.Errorf("Traceback took too long: %v", tracebackTime)
	}
}
