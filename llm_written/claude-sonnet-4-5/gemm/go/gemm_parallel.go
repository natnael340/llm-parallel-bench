package llm_written

import (
	"fmt"
	"runtime"
	"sync"
)

const (
	parallelThreshold = 10000 // m*n threshold for using parallel path
)

// mBlockTask represents a single m-block computation task.
type mBlockTask struct {
	Apack Matrix
	Bpack Matrix
	C     Matrix
	alpha float64
	m0    int
	n0    int
	kb    int
}

// Gemm computes C := alpha * A * B + beta * C (parallel version).
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

	// Use sequential path for small matrices
	if m*n < parallelThreshold {
		return GemmSequential(A, B, alpha, C, 1.0, MB, NB, KB)
	}

	// Parallel path
	Bt := transpose(B)

	// Create worker pool
	numWorkers := runtime.NumCPU()

	// Dispatch tasks
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
			kb := k1 - k0

			// Collect all m-blocks for this (n0, k0) pair
			var mBlocks []mBlockTask
			for m0 := 0; m0 < m; m0 += MB {
				m1 := m0 + MB
				if m1 > m {
					m1 = m
				}
				Apack := packMatrix(A, k0, k1, m0, m1) // (mChunk x kChunk)

				mBlocks = append(mBlocks, mBlockTask{
					Apack: Apack,
					Bpack: Bpack,
					C:     C,
					alpha: alpha,
					m0:    m0,
					n0:    n0,
					kb:    kb,
				})
			}

			// Process m-blocks in parallel with bounded concurrency
			var wg sync.WaitGroup
			sem := make(chan struct{}, numWorkers)

			for _, task := range mBlocks {
				wg.Add(1)
				sem <- struct{}{} // Acquire semaphore
				go func(t mBlockTask) {
					defer wg.Done()
					defer func() { <-sem }() // Release semaphore
					partialMatmul(t.Apack, t.Bpack, t.C, t.alpha, t.m0, t.n0, t.kb)
				}(task)
			}

			// Wait for all m-blocks to complete before moving to next (n0, k0)
			// This ensures deterministic accumulation order
			wg.Wait()
		}
	}

	return C, nil
}
