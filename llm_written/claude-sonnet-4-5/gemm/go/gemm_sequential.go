package llm_written

import (
	"fmt"
)

// GemmSequential computes C := alpha * A * B + beta * C (sequential version).
// A is (m x k), B is (k x n), C is (m x n). If C == nil, a zero matrix is used.
// If MB/NB/KB are 0, sensible defaults are used.
func GemmSequential(A, B Matrix, alpha float64, C Matrix, beta float64, MB, NB, KB int) (Matrix, error) {
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
