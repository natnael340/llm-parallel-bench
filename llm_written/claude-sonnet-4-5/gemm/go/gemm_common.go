package llm_written

import (
	"fmt"
)

// Matrix is a rectangular 2D slice of float64.
type Matrix [][]float64

// getSize returns (rows, cols) of a rectangular matrix.
func getSize(m Matrix) (int, int) {
	return len(m), len(m[0])
}

// validateMatrix checks that the matrix is non-empty, rectangular, and numeric (float64 by type).
func validateMatrix(m Matrix, name string) error {
	if m == nil {
		return fmt.Errorf("%s must be a non-empty list of rows", name)
	}
	if len(m) == 0 {
		return fmt.Errorf("%s  must have at least one row", name)
	}
	if len(m[0]) == 0 {
		return fmt.Errorf("%s must have at least one column", name)
	}
	cols := len(m[0])
	for r, row := range m {
		if row == nil {
			return fmt.Errorf("%s row %d is nil", name, r)
		}
		if len(row) != cols {
			return fmt.Errorf("%s is ragged: row %d has %d cols, expected %d", name, r, len(row), cols)
		}
	}
	return nil
}

// generateMatrix returns an rows x cols zero matrix.
func generateMatrix(rows, cols int) Matrix {
	out := make(Matrix, rows)
	for i := range out {
		out[i] = make([]float64, cols)
	}
	return out
}

// partialMatmul computes, for the provided packed blocks:
//   C[m0+i_off][n0+j_off] += alpha * sum_{k=0..kb-1} A[i_off][k] * B[j_off][k]
func partialMatmul(A, B, C Matrix, alpha float64, m0, n0, kb int) {
	for iOff, Aik := range A {
		Ci := C[m0+iOff]
		for jOff, Bjk := range B {
			s := 0.0
			for k := 0; k < kb; k++ {
				s += Aik[k] * Bjk[k]
			}
			Ci[n0+jOff] += alpha * s
		}
	}
}

// transpose returns the transpose of a rectangular matrix.
func transpose(m Matrix) Matrix {
	r, c := getSize(m)
	out := make(Matrix, c)
	for j := 0; j < c; j++ {
		out[j] = make([]float64, r)
		for i := 0; i < r; i++ {
			out[j][i] = m[i][j]
		}
	}
	return out
}

// packMatrix returns a view (sub-slices) of matrix[b0:b1], each row sliced as row[a0:a1].
// It does not copy row data (reads only).
func packMatrix(matrix Matrix, a0, a1, b0, b1 int) Matrix {
	out := make(Matrix, b1-b0)
	for i := range out {
		out[i] = matrix[b0+i][a0:a1]
	}
	return out
}

const (
	defaultMB = 64
	defaultNB = 64
	defaultKB = 64
)
