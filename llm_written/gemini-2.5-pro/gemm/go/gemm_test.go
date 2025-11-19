package llm_written

import (
	"math"
	"math/rand"
	"reflect"
	"testing"
	"time"
)

// areMatricesEqual compares two matrices for equality within a given tolerance.
func areMatricesEqual(a, b Matrix, tolerance float64) bool {
	rowsA, colsA := getSize(a)
	rowsB, colsB := getSize(b)
	if rowsA != rowsB || colsA != colsB {
		return false
	}
	for i := 0; i < rowsA; i++ {
		for j := 0; j < colsA; j++ {
			if math.Abs(a[i][j]-b[i][j]) > tolerance {
				return false
			}
		}
	}
	return true
}

// generateRandomMatrix creates a matrix of given dimensions with random float64 values.
func generateRandomMatrix(rows, cols int, seed int64) Matrix {
	r := rand.New(rand.NewSource(seed))
	m := make(Matrix, rows)
	for i := range m {
		m[i] = make([]float64, cols)
		for j := range m[i] {
			m[i][j] = r.Float64()*2.0 - 1.0 // Values between -1.0 and 1.0
		}
	}
	return m
}

// deepCopyMatrix creates a deep copy of a matrix.
func deepCopyMatrix(m Matrix) Matrix {
	if m == nil {
		return nil
	}
	rows, cols := getSize(m)
	newM := make(Matrix, rows)
	for i := 0; i < rows; i++ {
		newM[i] = make([]float64, cols)
		copy(newM[i], m[i])
	}
	return newM
}

func TestGemmParallel(t *testing.T) {
	testCases := []struct {
		name        string
		m, k, n     int
		mb, nb, kb  int
		alpha, beta float64
		seed        int64
	}{
		{"small_fastpath", 32, 32, 32, 64, 64, 64, 1.0, 0.0, 1},
		{"standard_case", 128, 128, 128, 64, 64, 64, 1.0, 1.0, 42},
		{"non_multiple_dims", 100, 150, 120, 32, 32, 32, 0.5, 0.5, 43},
		{"large_dims", 256, 256, 256, 64, 64, 64, 1.0, 0.0, 44},
		{"tall_A", 512, 64, 64, 64, 64, 64, 1.0, 1.0, 45},
		{"wide_B", 64, 64, 512, 64, 64, 64, 1.0, 1.0, 46},
		{"zero_alpha", 128, 128, 128, 64, 64, 64, 0.0, 2.0, 47},
		{"zero_beta", 128, 128, 128, 64, 64, 64, 2.0, 0.0, 48},
		{"nil_C", 128, 128, 128, 64, 64, 64, 1.0, 1.0, 49},
		{"small_blocks", 128, 128, 128, 16, 16, 16, 1.0, 1.0, 50},
	}

	for _, tc := range testCases {
		t.Run(tc.name, func(t *testing.T) {
			A := generateRandomMatrix(tc.m, tc.k, tc.seed)
			B := generateRandomMatrix(tc.k, tc.n, tc.seed+1)
			var C, C_seq Matrix
			if tc.beta != 0.0 {
				C = generateRandomMatrix(tc.m, tc.n, tc.seed+2)
				C_seq = deepCopyMatrix(C)
			}

			// Run sequential for baseline
			expected, err_seq := gemmSequential(A, B, tc.alpha, C_seq, tc.beta, tc.mb, tc.nb, tc.kb)
			if err_seq != nil {
				t.Fatalf("Sequential implementation failed: %v", err_seq)
			}

			// Run parallel
			actual, err_par := Gemm(A, B, tc.alpha, C, tc.beta, tc.mb, tc.nb, tc.kb)
			if err_par != nil {
				t.Fatalf("Parallel implementation failed: %v", err_par)
			}

			if !areMatricesEqual(expected, actual, 1e-9) {
				t.Errorf("Matrices are not equal for case %s", tc.name)
			}
		})
	}
}

func TestGemmErrorCases(t *testing.T) {
	A_valid := generateRandomMatrix(4, 4, 1)
	B_valid := generateRandomMatrix(4, 4, 2)

	t.Run("mismatch_A_B", func(t *testing.T) {
		A := generateRandomMatrix(4, 5, 1) // 4x5
		B := generateRandomMatrix(4, 4, 2) // 4x4
		_, err := Gemm(A, B, 1.0, nil, 0.0, 4, 4, 4)
		if err == nil {
			t.Error("Expected shape mismatch error for A and B, got nil")
		}
	})

	t.Run("mismatch_C", func(t *testing.T) {
		C_bad := generateRandomMatrix(3, 3, 3) // 3x3, expecting 4x4
		_, err := Gemm(A_valid, B_valid, 1.0, C_bad, 1.0, 4, 4, 4)
		if err == nil {
			t.Error("Expected shape mismatch error for C, got nil")
		}
	})

	t.Run("ragged_A", func(t *testing.T) {
		A_ragged := Matrix{[]float64{1, 2}, []float64{3}}
		_, err := Gemm(A_ragged, B_valid, 1.0, nil, 0.0, 4, 4, 4)
		if err == nil {
			t.Error("Expected ragged matrix error for A, got nil")
		}
	})
}

// TestDeterminism runs the same parallel computation twice and expects bit-for-bit identical results.
func TestDeterminism(t *testing.T) {
	seed := time.Now().UnixNano()
	A := generateRandomMatrix(128, 128, seed)
	B := generateRandomMatrix(128, 128, seed+1)
	C1 := generateRandomMatrix(128, 128, seed+2)
	C2 := deepCopyMatrix(C1)

	res1, err1 := Gemm(A, B, 1.0, C1, 1.0, 32, 32, 32)
	if err1 != nil {
		t.Fatalf("First run failed: %v", err1)
	}

	res2, err2 := Gemm(A, B, 1.0, C2, 1.0, 32, 32, 32)
	if err2 != nil {
		t.Fatalf("Second run failed: %v", err2)
	}

	if !reflect.DeepEqual(res1, res2) {
		t.Error("Parallel implementation is not deterministic")
	}
}
