package golang

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

// Gemm computes C := alpha * A * B + beta * C.
// A is (m x k), B is (k x n), C is (m x n). If C == nil, a zero matrix is used.
// If MB/NB/KB are 0, sensible defaults are used.
func Gemm(A, B Matrix, alpha float64, C Matrix, beta float64, MB, NB, KB int) (Matrix, error) {
	if err := validateMatrix(A, "A"); err != nil {
		return nil, err
	}
	if err := validateMatrix(B, "B"); err != nil {
		return nil, err
	}

	m, k := getSize(A)
	k2, n := getSize(B)
	if k != k2 {
		return nil, fmt.Errorf("shape mismatch: A is (%d,%d), B is (%d,%d)", m, k, k2, n)
	}

	if C != nil {
		if err := validateMatrix(C, "C"); err != nil {
			return nil, err
		}
		m2, n2 := getSize(C)
		if m2 != m || n2 != n {
			return nil, fmt.Errorf("C has shape (%d,%d); expected (%d,%d)", m2, n2, m, n)
		}
		if beta != 1.0 {
			for i := 0; i < m; i++ {
				row := C[i]
				for j := 0; j < n; j++ {
					row[j] *= beta
				}
			}
		}
	} else {
		C = generateMatrix(m, n)
	}

	if alpha == 0.0 {
		return C, nil
	}

	// Default block sizes if not provided
	if MB == 0 {
		MB = defaultMB
	}
	if NB == 0 {
		NB = defaultNB
	}
	if KB == 0 {
		KB = defaultKB
	}

	Bt := transpose(B)

	for n0 := 0; n0 < n; n0 += NB {
		n1 := n0 + NB
		if n1 > n {
			n1 = n
		}
		for k0 := 0; k0 < k; k0 += KB {
			k1 := k0 + KB
			if k1 > k {
				k1 = k
			}
			Bpack := packMatrix(Bt, k0, k1, n0, n1) // (nChunk x kChunk)

			for m0 := 0; m0 < m; m0 += MB {
				m1 := m0 + MB
				if m1 > m {
					m1 = m
				}
				Apack := packMatrix(A, k0, k1, m0, m1) // (mChunk x kChunk)

				kb := k1 - k0
				partialMatmul(Apack, Bpack, C, alpha, m0, n0, kb)
			}
		}
	}

	return C, nil
}

// printMatrix prints the matrix with separators.
func printMatrix(m Matrix) {
	fmt.Println("=========================")
	for _, row := range m {
		fmt.Println(row)
	}
	fmt.Println("=========================")
}

func main() {
	A := Matrix{
		{1, 2, 3},
		{4, 5, 6},
		{7, 8, 9},
	}
	B := Matrix{
		{1, 4},
		{2, 5},
		{3, 6},
	}

	fmt.Println("A:")
	printMatrix(A)
	fmt.Println("B:")
	printMatrix(B)

	C, err := Gemm(A, B, 1.0, nil, 0.0, 64, 64, 64)
	if err != nil {
		panic(err)
	}

	fmt.Println("C = A * B:")
	printMatrix(C)

	// Example with existing C and beta scaling:
	C2 := generateMatrix(3, 2)
	C2[0][0] = 10
	C2[1][1] = -2
	Cout, err := Gemm(A, B, 1.0, C2, 0.5, 64, 64, 64) // scales provided C by beta=0.5 before adding alpha*A*B
	if err != nil {
		panic(err)
	}
	fmt.Println("Cout = A*B + 0.5*C2:")
	printMatrix(Cout)
}

// (Optional) small helper to ensure errors are surfaced in main:
func must[T any](v T, err error) T {
	if err != nil {
		panic(err)
	}
	return v
}
