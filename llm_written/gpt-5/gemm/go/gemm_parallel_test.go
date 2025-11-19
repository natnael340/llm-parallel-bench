package llm_written

import (
	"math/rand"
	"testing"
)

func TestGemmMatchesSequential(t *testing.T) {
	// Local helpers to avoid package-level symbol clashes
	randMat := func(rng *rand.Rand, rows, cols int) Matrix {
		m := make(Matrix, rows)
		for i := 0; i < rows; i++ {
			m[i] = make([]float64, cols)
			for j := 0; j < cols; j++ {
				m[i][j] = rng.Float64()*2 - 1
			}
		}
		return m
	}
	clone := func(m Matrix) Matrix {
		out := make(Matrix, len(m))
		for i := range m {
			row := make([]float64, len(m[0]))
			copy(row, m[i])
			out[i] = row
		}
		return out
	}
	scaleInPlace := func(C Matrix, beta float64) {
		if beta == 1.0 {
			return
		}
		for i := range C {
			for j := range C[i] {
				C[i][j] *= beta
			}
		}
	}
	equalWithin := func(a, b Matrix, tol float64) bool {
		if len(a) != len(b) || len(a[0]) != len(b[0]) {
			return false
		}
		for i := range a {
			for j := range a[0] {
				d := a[i][j] - b[i][j]
				if d < 0 {
					d = -d
				}
				if d > tol {
					return false
				}
			}
		}
		return true
	}

	seed := int64(1337)
	rng := rand.New(rand.NewSource(seed))

	cases := []struct {
		m, k, n int
		alpha   float64
		beta    float64
		MB, NB, KB int
		name    string
	}{
		{1, 1, 1, 4, 1.0, 0, 0, 0, "1x1"},
		{1, 3, 1, 1.0, 0.5, 0, 0, 0, "1x3*3x1"},
		{2, 3, 4, 0.75, 0.3, 32, 32, 32, "small1"},
		{5, 5, 5, 1.0, 0.9, 16, 16, 16, "small2"},
		{8, 7, 6, 1.1, 0.8, 64, 64, 64, "small3"},
		{64, 64, 64, 1.0, 0.7, 64, 64, 64, "large1"},
		{128, 64, 96, 0.95, 0.6, 64, 64, 64, "large2"},
	}

	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			A := randMat(rng, tc.m, tc.k)
			B := randMat(rng, tc.k, tc.n)
			C0 := randMat(rng, tc.m, tc.n)

			// Baseline: sequential kernel with pre-scaled C
			Cseq := clone(C0)
			scaleInPlace(Cseq, tc.beta)
			CseqOut, err := gemmSequential(A, B, tc.alpha, Cseq, 1.0, tc.MB, tc.NB, tc.KB)
			if err != nil {
				t.Fatalf("sequential error: %v", err)
			}

			// Parallel: full Gemm scales C internally
			Cpar := clone(C0)
			CparOut, err := Gemm(A, B, tc.alpha, Cpar, tc.beta, tc.MB, tc.NB, tc.KB)
			if err != nil {
				t.Fatalf("parallel error: %v", err)
			}

			if !equalWithin(CseqOut, CparOut, 1e-12) {
				t.Fatalf("mismatch between sequential and parallel results")
			}
		})
	}
}

func TestDeterminism(t *testing.T) {
	randMat := func(rng *rand.Rand, rows, cols int) Matrix {
		m := make(Matrix, rows)
		for i := 0; i < rows; i++ {
			m[i] = make([]float64, cols)
			for j := 0; j < cols; j++ {
				m[i][j] = rng.Float64()*2 - 1
			}
		}
		return m
	}
	equalWithin := func(a, b Matrix, tol float64) bool {
		if len(a) != len(b) || len(a[0]) != len(b[0]) {
			return false
		}
		for i := range a {
			for j := range a[0] {
				d := a[i][j] - b[i][j]
				if d < 0 {
					d = -d
				}
				if d > tol {
					return false
				}
			}
		}
		return true
	}

	rng := rand.New(rand.NewSource(2024))
	A := randMat(rng, 64, 64)
	B := randMat(rng, 64, 64)
	C0 := randMat(rng, 64, 64)

	C1 := make(Matrix, len(C0))
	for i := range C0 { row := make([]float64, len(C0[0])); copy(row, C0[i]); C1[i] = row }
	C2 := make(Matrix, len(C0))
	for i := range C0 { row := make([]float64, len(C0[0])); copy(row, C0[i]); C2[i] = row }

	C1, err1 := Gemm(A, B, 1.0, C1, 0.8, 64, 64, 64)
	if err1 != nil { t.Fatalf("first run error: %v", err1) }
	C2, err2 := Gemm(A, B, 1.0, C2, 0.8, 64, 64, 64)
	if err2 != nil { t.Fatalf("second run error: %v", err2) }

	if !equalWithin(C1, C2, 0) {
		t.Fatalf("non-deterministic outputs")
	}
}

func TestAlphaZeroShortCircuit(t *testing.T) {
	randMat := func(rng *rand.Rand, rows, cols int) Matrix {
		m := make(Matrix, rows)
		for i := 0; i < rows; i++ {
			m[i] = make([]float64, cols)
			for j := 0; j < cols; j++ {
				m[i][j] = rng.Float64()*2 - 1
			}
		}
		return m
	}
	equalWithin := func(a, b Matrix, tol float64) bool {
		if len(a) != len(b) || len(a[0]) != len(b[0]) {
			return false
		}
		for i := range a {
			for j := range a[0] {
				d := a[i][j] - b[i][j]
				if d < 0 { d = -d }
				if d > tol { return false }
			}
		}
		return true
	}

	rng := rand.New(rand.NewSource(7))
	A := randMat(rng, 4, 5)
	B := randMat(rng, 5, 3)
	C0 := randMat(rng, 4, 3)

	// Expected: C := beta * C0
	expected := make(Matrix, len(C0))
	for i := range C0 { row := make([]float64, len(C0[0])); copy(row, C0[i]); expected[i] = row }
	beta := 0.7
	for i := range expected { for j := range expected[i] { expected[i][j] *= beta } }

	C := make(Matrix, len(C0))
	for i := range C0 { row := make([]float64, len(C0[0])); copy(row, C0[i]); C[i] = row }
	out, err := Gemm(A, B, 0.0, C, beta, 0, 0, 0)
	if err != nil { t.Fatalf("Gemm returned error: %v", err) }
	if !equalWithin(out, expected, 0) {
		t.Fatalf("alpha==0 path mismatch")
	}
}

func TestErrors(t *testing.T) {
	// Shape mismatch
	{
		A := Matrix{{1, 2}, {3, 4}}
		B := Matrix{{1, 2, 3}}
		C := Matrix{{0, 0}, {0, 0}}
		if _, err := Gemm(A, B, 1.0, C, 1.0, 0, 0, 0); err == nil {
			t.Fatalf("expected shape mismatch error, got nil")
		}
	}
	// C size mismatch
	{
		A := Matrix{{1, 2}, {3, 4}}
		B := Matrix{{5, 6}, {7, 8}}
		C := Matrix{{0}}
		if _, err := Gemm(A, B, 1.0, C, 1.0, 0, 0, 0); err == nil {
			t.Fatalf("expected C shape mismatch error, got nil")
		}
	}
	// Ragged matrix
	{
		A := Matrix{{1, 2}, {3}} // ragged
		B := Matrix{{1}, {2}}
		C := Matrix{{0, 0}}
		if _, err := Gemm(A, B, 1.0, C, 1.0, 0, 0, 0); err == nil {
			t.Fatalf("expected ragged A error, got nil")
		}
	}
}
