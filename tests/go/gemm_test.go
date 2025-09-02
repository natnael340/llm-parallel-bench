// gemm_test.go
package main

import (
	"math"
	"math/rand"
	"testing"
	"time"
	gemm_seq "github.com/natnael340/llm-parallel-bench/GEMM/golang"
	//gemm_seq "github.com/natnael340/llm-parallel-bench/llm_written"
)

// ---------- helpers ----------

type Matrix = [][]float64

func makeMatrix(rows, cols int, fill float64) Matrix {
	m := make(Matrix, rows)
	for i := range m {
		m[i] = make([]float64, cols)
		for j := range m[i] {
			m[i][j] = fill
		}
	}
	return m
}

func makeRandomMatrix(rows, cols int, lo, hi float64, seed int64) Matrix {
	rng := rand.New(rand.NewSource(seed))
	m := make(Matrix, rows)
	for i := range m {
		m[i] = make([]float64, cols)
		for j := range m[i] {
			m[i][j] = rng.Float64()*(hi-lo) + lo
		}
	}
	return m
}

func copyMatrix(X Matrix) Matrix {
	m, n := len(X), len(X[0])
	Y := make(Matrix, m)
	for i := 0; i < m; i++ {
		Y[i] = make([]float64, n)
		copy(Y[i], X[i])
	}
	return Y
}

func matAlmostEqual(t *testing.T, X, Y Matrix, tol float64) {
	t.Helper()
	if len(X) != len(Y) || len(X[0]) != len(Y[0]) {
		t.Fatalf("dimension mismatch: X=%dx%d, Y=%dx%d", len(X), len(X[0]), len(Y), len(Y[0]))
	}
	for i := range X {
		for j := range X[0] {
			x, y := X[i][j], Y[i][j]
			if math.IsNaN(x) || math.IsNaN(y) {
				if !(math.IsNaN(x) && math.IsNaN(y)) {
					t.Fatalf("NaN mismatch at (%d,%d): %v vs %v", i, j, x, y)
				}
			} else {
				if math.Abs(x-y) > tol {
					t.Fatalf("values differ at (%d,%d): got=%g want=%g (tol=%g)", i, j, x, y, tol)
				}
			}
		}
	}
}

// naive reference: C := alpha*A*B + beta*C
func naiveGemm(A, B Matrix, alpha float64, C Matrix, beta float64) Matrix {
	m, k := len(A), len(A[0])
	k2, n := len(B), len(B[0])
	if k != k2 {
		panic("shape mismatch in naiveGemm")
	}
	if C == nil {
		C = makeMatrix(m, n, 0.0)
	} else {
		if len(C) != m || len(C[0]) != n {
			panic("C shape mismatch in naiveGemm")
		}
		if beta != 1.0 {
			for i := 0; i < m; i++ {
				for j := 0; j < n; j++ {
					C[i][j] *= beta
				}
			}
		}
	}
	if alpha == 0.0 {
		return C
	}
	for i := 0; i < m; i++ {
		for kk := 0; kk < k; kk++ {
			a := alpha * A[i][kk]
			if a == 0.0 {
				continue
			}
			Bk := B[kk]
			Ci := C[i]
			for j := 0; j < n; j++ {
				Ci[j] += a * Bk[j]
			}
		}
	}
	return C
}

// ---------- tests ----------

func TestIdentityLeft(t *testing.T) {
	m, n := 3, 4
	I := make(Matrix, m)
	for i := 0; i < m; i++ {
		I[i] = make([]float64, m)
		I[i][i] = 1
	}
	B := makeRandomMatrix(m, n, -1.0, 1.0, 1)
	out, err := gemm_seq.Gemm(I, B, 1.0, nil, 0.0, 64, 64, 64)
	if err != nil {
		t.Fatal(err)
	}
	matAlmostEqual(t, out, B, 1e-9)
}

func TestIdentityRight(t *testing.T) {
	m, k := 3, 5
	n := k
	A := makeRandomMatrix(m, k, -1.0, 1.0, 2)
	I := make(Matrix, n)
	for i := 0; i < n; i++ {
		I[i] = make([]float64, n)
		I[i][i] = 1
	}
	out, err := gemm_seq.Gemm(A, I, 1.0, nil, 0.0, 64, 64, 64)
	if err != nil {
		t.Fatal(err)
	}
	matAlmostEqual(t, out, A, 1e-9)
}

func TestZeroMatricesYieldZero(t *testing.T) {
	m, k, n := 4, 3, 5
	A := makeMatrix(m, k, 0)
	B := makeMatrix(k, n, 0)
	out, err := gemm_seq.Gemm(A, B, 1.0, nil, 0.0, 64, 64, 64)
	if err != nil {
		t.Fatal(err)
	}
	matAlmostEqual(t, out, makeMatrix(m, n, 0), 1e-12)
}

func TestAlphaZeroWithCNone(t *testing.T) {
	m, k, n := 2, 3, 4
	A := makeRandomMatrix(m, k, -1, 1, 3)
	B := makeRandomMatrix(k, n, -1, 1, 4)
	out, err := gemm_seq.Gemm(A, B, 0.0, nil, 0.0, 64, 64, 64)
	if err != nil {
		t.Fatal(err)
	}
	matAlmostEqual(t, out, makeMatrix(m, n, 0), 1e-12)
}

func TestAlphaZeroWithCBetaOnePreservesC(t *testing.T) {
	m, k, n := 3, 3, 2
	A := makeRandomMatrix(m, k, -1, 1, 5)
	B := makeRandomMatrix(k, n, -1, 1, 6)
	C := makeRandomMatrix(m, n, -1, 1, 7)
	Ccopy := copyMatrix(C)
	out, err := gemm_seq.Gemm(A, B, 0.0, C, 1.0, 64, 64, 64)
	if err != nil {
		t.Fatal(err)
	}
	// in-place: same underlying data (check first element address)
	if &out[0][0] != &C[0][0] {
		t.Fatalf("expected in-place output to be the same slice")
	}
	matAlmostEqual(t, out, Ccopy, 1e-12)
}

func TestAlphaZeroWithCBetaScalesOnceEvenWithSmallKB(t *testing.T) {
	m, k, n := 3, 7, 4
	A := makeRandomMatrix(m, k, -1, 1, 8)
	B := makeRandomMatrix(k, n, -1, 1, 9)
	C := makeRandomMatrix(m, n, -1, 1, 10)
	Ccopy := copyMatrix(C)
	beta := 2.5
	out, err := gemm_seq.Gemm(A, B, 0.0, C, beta, 2, 3, 1) // many k-slabs
	if err != nil {
		t.Fatal(err)
	}
	if &out[0][0] != &C[0][0] {
		t.Fatalf("expected in-place output")
	}
	expected := make(Matrix, m)
	for i := 0; i < m; i++ {
		expected[i] = make([]float64, n)
		for j := 0; j < n; j++ {
			expected[i][j] = beta * Ccopy[i][j]
		}
	}
	matAlmostEqual(t, out, expected, 1e-12)
}

func TestBetaZeroIgnoresInputC(t *testing.T) {
	m, k, n := 4, 3, 5
	A := makeRandomMatrix(m, k, -1, 1, 11)
	B := makeRandomMatrix(k, n, -1, 1, 12)
	C := makeMatrix(m, n, 7.0)
	out, err := gemm_seq.Gemm(A, B, 1.0, C, 0.0, 64, 64, 64)
	if err != nil {
		t.Fatal(err)
	}
	ref := naiveGemm(A, B, 1.0, makeMatrix(m, n, 0.0), 0.0)
	matAlmostEqual(t, out, ref, 1e-9)
}

func TestBetaOneAccumulatesIntoC(t *testing.T) {
	m, k, n := 3, 4, 2
	A := makeRandomMatrix(m, k, -1, 1, 13)
	B := makeRandomMatrix(k, n, -1, 1, 14)
	C := makeRandomMatrix(m, n, -1, 1, 15)
	Cref := copyMatrix(C)
	out, err := gemm_seq.Gemm(A, B, 0.5, C, 1.0, 64, 64, 64)
	if err != nil {
		t.Fatal(err)
	}
	ref := naiveGemm(A, B, 0.5, Cref, 1.0)
	matAlmostEqual(t, out, ref, 1e-9)
}

func TestNegativeAlphaAndBeta(t *testing.T) {
	m, k, n := 2, 3, 2
	A := makeRandomMatrix(m, k, -1, 1, 16)
	B := makeRandomMatrix(k, n, -1, 1, 17)
	C := makeRandomMatrix(m, n, -1, 1, 18)
	Cref := copyMatrix(C)
	out, err := gemm_seq.Gemm(A, B, -1.0, C, -0.5, 64, 64, 64)
	if err != nil {
		t.Fatal(err)
	}
	ref := naiveGemm(A, B, -1.0, Cref, -0.5)
	matAlmostEqual(t, out, ref, 1e-9)
}

func TestRectangularTallSkinny(t *testing.T) {
	m, k, n := 10, 2, 7
	A := makeRandomMatrix(m, k, -1, 1, 19)
	B := makeRandomMatrix(k, n, -1, 1, 20)
	out, err := gemm_seq.Gemm(A, B, 1.0, nil, 0.0, 64, 64, 64)
	if err != nil {
		t.Fatal(err)
	}
	ref := naiveGemm(A, B, 1.0, nil, 0.0)
	matAlmostEqual(t, out, ref, 1e-9)
}

func TestRectangularShortFat(t *testing.T) {
	m, k, n := 3, 8, 20
	A := makeRandomMatrix(m, k, -1, 1, 21)
	B := makeRandomMatrix(k, n, -1, 1, 22)
	out, err := gemm_seq.Gemm(A, B, 1.0, nil, 0.0, 2, 7, 3)
	if err != nil {
		t.Fatal(err)
	}
	ref := naiveGemm(A, B, 1.0, nil, 0.0)
	matAlmostEqual(t, out, ref, 1e-9)
}

func TestSingleRowTimesSingleColumnScalar(t *testing.T) {
	m, k, n := 1, 5, 1
	A := makeRandomMatrix(m, k, -1, 1, 23)
	B := makeRandomMatrix(k, n, -1, 1, 24)
	out, err := gemm_seq.Gemm(A, B, 1.0, nil, 0.0, 64, 64, 64)
	if err != nil {
		t.Fatal(err)
	}
	ref := naiveGemm(A, B, 1.0, nil, 0.0)
	matAlmostEqual(t, out, ref, 1e-12)
}

func TestRowVectorTimesMatrix(t *testing.T) {
	m, k, n := 1, 6, 4
	A := makeRandomMatrix(m, k, -1, 1, 25)
	B := makeRandomMatrix(k, n, -1, 1, 26)
	out, err := gemm_seq.Gemm(A, B, 1.0, nil, 0.0, 1, 3, 2)
	if err != nil {
		t.Fatal(err)
	}
	ref := naiveGemm(A, B, 1.0, nil, 0.0)
	matAlmostEqual(t, out, ref, 1e-12)
}

func TestMatrixTimesColumnVector(t *testing.T) {
	m, k, n := 7, 5, 1
	A := makeRandomMatrix(m, k, -1, 1, 27)
	B := makeRandomMatrix(k, n, -1, 1, 28)
	out, err := gemm_seq.Gemm(A, B, 1.0, nil, 0.0, 4, 1, 3)
	if err != nil {
		t.Fatal(err)
	}
	ref := naiveGemm(A, B, 1.0, nil, 0.0)
	matAlmostEqual(t, out, ref, 1e-9)
}

func TestGeneralRandomCompareReference(t *testing.T) {
	m, k, n := 9, 11, 8
	A := makeRandomMatrix(m, k, -1, 1, 29)
	B := makeRandomMatrix(k, n, -1, 1, 30)
	C := makeRandomMatrix(m, n, -1, 1, 31)
	Cdeep := copyMatrix(C)
	out, err := gemm_seq.Gemm(A, B, 1.2, Cdeep, 0.7, 4, 5, 3)
	if err != nil {
		t.Fatal(err)
	}
	ref := naiveGemm(A, B, 1.2, C, 0.7)
	matAlmostEqual(t, out, ref, 1e-9)
}

func TestNotMultipleOfBlockSizes(t *testing.T) {
	m, k, n := 13, 17, 19
	A := makeRandomMatrix(m, k, -1, 1, 32)
	B := makeRandomMatrix(k, n, -1, 1, 33)
	out, err := gemm_seq.Gemm(A, B, 1.0, nil, 0.0, 5, 6, 7)
	if err != nil {
		t.Fatal(err)
	}
	ref := naiveGemm(A, B, 1.0, nil, 0.0)
	matAlmostEqual(t, out, ref, 1e-9)
}

func TestBlockSizesOneMatchesNaive(t *testing.T) {
	m, k, n := 5, 6, 4
	A := makeRandomMatrix(m, k, -1, 1, 34)
	B := makeRandomMatrix(k, n, -1, 1, 35)
	out, err := gemm_seq.Gemm(A, B, 1.0, nil, 0.0, 1, 1, 1)
	if err != nil {
		t.Fatal(err)
	}
	ref := naiveGemm(A, B, 1.0, nil, 0.0)
	matAlmostEqual(t, out, ref, 1e-12)
}

func TestBlockSizesLargerThanDims(t *testing.T) {
	m, k, n := 4, 3, 2
	A := makeRandomMatrix(m, k, -1, 1, 36)
	B := makeRandomMatrix(k, n, -1, 1, 37)
	out, err := gemm_seq.Gemm(A, B, 1.0, nil, 0.0, 128, 128, 128)
	if err != nil {
		t.Fatal(err)
	}
	ref := naiveGemm(A, B, 1.0, nil, 0.0)
	matAlmostEqual(t, out, ref, 1e-12)
}

func TestInPlaceCObjectIdentity(t *testing.T) {
	m, k, n := 3, 3, 3
	A := makeRandomMatrix(m, k, -1, 1, 38)
	B := makeRandomMatrix(k, n, -1, 1, 39)
	C := makeRandomMatrix(m, n, -1, 1, 40)
	out, err := gemm_seq.Gemm(A, B, 0.3, C, 0.4, 64, 64, 64)
	if err != nil {
		t.Fatal(err)
	}
	if &out[0][0] != &C[0][0] {
		t.Fatalf("expected in-place mutation of C")
	}
}

func TestCCreatedWhenNil(t *testing.T) {
	m, k, n := 2, 3, 2
	A := makeRandomMatrix(m, k, -1, 1, 41)
	B := makeRandomMatrix(k, n, -1, 1, 42)
	out, err := gemm_seq.Gemm(A, B, 1.0, nil, 0.0, 64, 64, 64)
	if err != nil {
		t.Fatal(err)
	}
	if len(out) != m || len(out[0]) != n {
		t.Fatalf("unexpected out shape: got %dx%d want %dx%d", len(out), len(out[0]), m, n)
	}
}

func TestDimensionMismatchRaises(t *testing.T) {
	A := makeRandomMatrix(3, 4, -1, 1, 43)
	B := makeRandomMatrix(5, 2, -1, 1, 44) // k != k2
	if _, err := gemm_seq.Gemm(A, B, 1.0, nil, 0.0, 64, 64, 64); err == nil {
		t.Fatalf("expected error for dimension mismatch")
	}
}

func TestInvalidCShapeRaises(t *testing.T) {
	A := makeRandomMatrix(3, 2, -1, 1, 45)
	B := makeRandomMatrix(2, 4, -1, 1, 46)
	C := makeRandomMatrix(2, 4, -1, 1, 47) // wrong m
	if _, err := gemm_seq.Gemm(A, B, 1.0, C, 0.0, 64, 64, 64); err == nil {
		t.Fatalf("expected error for invalid C shape")
	}
}

func TestRaggedARejected(t *testing.T) {
	A := Matrix{
		{1.0, 2.0},
		{3.0}, // ragged
	}
	B := makeRandomMatrix(2, 2, -1, 1, 48)
	if _, err := gemm_seq.Gemm(A, B, 1.0, nil, 0.0, 64, 64, 64); err == nil {
		t.Fatalf("expected error for ragged A")
	}
}

func TestRaggedBRejected(t *testing.T) {
	A := makeRandomMatrix(2, 2, -1, 1, 49)
	B := Matrix{
		{1.0},
		{2.0, 3.0}, // ragged
	}
	if _, err := gemm_seq.Gemm(A, B, 1.0, nil, 0.0, 64, 64, 64); err == nil {
		t.Fatalf("expected error for ragged B")
	}
}

// Note: "non-numeric entry" is not representable with [][]float64 in Go, so that test is omitted.

func TestNaNPropagation(t *testing.T) {
	A := Matrix{
		{math.NaN(), 1.0},
		{2.0, 3.0},
	}
	B := Matrix{
		{4.0, 5.0},
		{6.0, 7.0},
	}
	out, err := gemm_seq.Gemm(A, B, 1.0, nil, 0.0, 64, 64, 64)
	if err != nil {
		t.Fatal(err)
	}
	if !(math.IsNaN(out[0][0]) && math.IsNaN(out[0][1])) {
		t.Fatalf("expected NaN propagation in first row, got %v %v", out[0][0], out[0][1])
	}
}

func TestInfinityPropagation(t *testing.T) {
	A := Matrix{
		{math.Inf(1), 0.0},
		{0.0, 1.0},
	}
	B := Matrix{
		{1.0, 2.0},
		{3.0, 4.0},
	}
	out, err := gemm_seq.Gemm(A, B, 1.0, nil, 0.0, 64, 64, 64)
	if err != nil {
		t.Fatal(err)
	}
	if !(math.IsInf(out[0][0], 0) && math.IsInf(out[0][1], 0)) {
		t.Fatalf("expected Inf propagation in first row, got %v %v", out[0][0], out[0][1])
	}
}

func TestRepeatCallsAccumulateWithBetaOne(t *testing.T) {
	m, k, n := 3, 3, 3
	A := makeRandomMatrix(m, k, -1, 1, 51)
	B := makeRandomMatrix(k, n, -1, 1, 52)
	C := makeMatrix(m, n, 0.0)
	if _, err := gemm_seq.Gemm(A, B, 1.0, C, 1.0, 64, 64, 64); err != nil {
		t.Fatal(err)
	}
	if _, err := gemm_seq.Gemm(A, B, 1.0, C, 1.0, 64, 64, 64); err != nil {
		t.Fatal(err)
	}
	refOnce := naiveGemm(A, B, 1.0, makeMatrix(m, n, 0.0), 1.0)
	refTwice := naiveGemm(A, B, 1.0, refOnce, 1.0)
	matAlmostEqual(t, C, refTwice, 1e-9)
}

func TestAlphaScalingLinear(t *testing.T) {
	m, k, n := 4, 5, 3
	A := makeRandomMatrix(m, k, -1, 1, 53)
	B := makeRandomMatrix(k, n, -1, 1, 54)
	C1, err := gemm_seq.Gemm(A, B, 1.0, nil, 0.0, 64, 64, 64)
	if err != nil {
		t.Fatal(err)
	}
	s := 2.75
	C2, err := gemm_seq.Gemm(A, B, s, nil, 0.0, 64, 64, 64)
	if err != nil {
		t.Fatal(err)
	}
	scaled := make(Matrix, len(C1))
	for i := range C1 {
		scaled[i] = make([]float64, len(C1[0]))
		for j := range C1[0] {
			scaled[i][j] = s * C1[i][j]
		}
	}
	matAlmostEqual(t, C2, scaled, 1e-9)
}

// Heavy test (skipped with -short)
func TestGemmPerformanceSpeed(t *testing.T) {
	if testing.Short() {
		t.Skip("skipping performance test in -short mode")
	}
	m := 1000
	k := 1000
	n := 1000
	A := makeRandomMatrix(m, k, -1, 1, 10)
	B := makeRandomMatrix(k, n, -1, 1, 12)

	const iters = 10
	start := time.Now()
	for i := 0; i < iters; i++ {
		if _, err := gemm_seq.Gemm(A, B, 1.0, nil, 0.0, 32, 32, 32); err != nil {
			t.Fatal(err)
		}
	}
	elapsed := time.Since(start).Seconds()

	C, err := gemm_seq.Gemm(A, B, 1.0, nil, 0.0, 32, 32, 32)
	if err != nil {
		t.Fatal(err)
	}
	if len(C) != m || len(C[0]) != n {
		t.Fatalf("unexpected out shape: got %dx%d want %dx%d", len(C), len(C[0]), m, n)
	}

	// 2*m*n*k floating ops (mul+add) per multiply
	gflops := (2.0 * float64(m) * float64(n) * float64(k) * float64(iters)) / elapsed / 1e9
	t.Logf("GEMM 1000x1000: %.3fs  (~%.3f GFLOPs)", elapsed, gflops)
}