package golang

// ---- 2x2 micro-kernel + edge kernels ----

// microKernel2x2 computes a 2x2 C-tile at (i0,j0).
// Ablk rows: Ablk[iOff][0:kb], Bpan rows: Bpan[jOff][0:kb]
func microKernel2x2(Ablk, Bpan Matrix, C Matrix, alpha float64, i0, j0, kb int) {
	a0 := Ablk[i0+0]
	a1 := Ablk[i0+1]
	b0 := Bpan[j0+0]
	b1 := Bpan[j0+1]
	// bounds-check elimination
	_ = a0[kb-1]; _ = a1[kb-1]; _ = b0[kb-1]; _ = b1[kb-1]

	c00, c01 := 0.0, 0.0
	c10, c11 := 0.0, 0.0

	// small unroll by 4
	k := 0
	for ; k+3 < kb; k += 4 {
		a00, a01, a02, a03 := a0[k+0], a0[k+1], a0[k+2], a0[k+3]
		a10, a11, a12, a13 := a1[k+0], a1[k+1], a1[k+2], a1[k+3]
		b00, b01, b02, b03 := b0[k+0], b0[k+1], b0[k+2], b0[k+3]
		b10, b11, b12, b13 := b1[k+0], b1[k+1], b1[k+2], b1[k+3]

		c00 += a00*b00 + a01*b01 + a02*b02 + a03*b03
		c01 += a00*b10 + a01*b11 + a02*b12 + a03*b13
		c10 += a10*b00 + a11*b01 + a12*b02 + a13*b03
		c11 += a10*b10 + a11*b11 + a12*b12 + a13*b13
	}
	for ; k < kb; k++ {
		ak0, ak1 := a0[k], a1[k]
		bk0, bk1 := b0[k], b1[k]
		c00 += ak0 * bk0
		c01 += ak0 * bk1
		c10 += ak1 * bk0
		c11 += ak1 * bk1
	}

	Ci0 := C[0] // will remap below
	Ci1 := C[0]
	_ = Ci0 // silence linter
	// writeback
	Ci0 = C[i0+0]
	Ci1 = C[i0+1]
	Ci0[j0+0] += alpha * c00
	Ci0[j0+1] += alpha * c01
	Ci1[j0+0] += alpha * c10
	Ci1[j0+1] += alpha * c11
}

func microKernel2x1(Ablk Matrix, Bpan Matrix, C Matrix, alpha float64, i0, j0, kb int) {
	a0 := Ablk[i0+0]
	a1 := Ablk[i0+1]
	b0 := Bpan[j0+0]
	_ = a0[kb-1]; _ = a1[kb-1]; _ = b0[kb-1]

	c00, c10 := 0.0, 0.0
	k := 0
	for ; k+3 < kb; k += 4 {
		c00 += a0[k+0]*b0[k+0] + a0[k+1]*b0[k+1] + a0[k+2]*b0[k+2] + a0[k+3]*b0[k+3]
		c10 += a1[k+0]*b0[k+0] + a1[k+1]*b0[k+1] + a1[k+2]*b0[k+2] + a1[k+3]*b0[k+3]
	}
	for ; k < kb; k++ {
		ak0, ak1 := a0[k], a1[k]
		bk0 := b0[k]
		c00 += ak0 * bk0
		c10 += ak1 * bk0
	}
	C[i0+0][j0+0] += alpha * c00
	C[i0+1][j0+0] += alpha * c10
}

func microKernel1x2(Ablk Matrix, Bpan Matrix, C Matrix, alpha float64, i0, j0, kb int) {
	a0 := Ablk[i0+0]
	b0 := Bpan[j0+0]
	b1 := Bpan[j0+1]
	_ = a0[kb-1]; _ = b0[kb-1]; _ = b1[kb-1]

	c00, c01 := 0.0, 0.0
	k := 0
	for ; k+3 < kb; k += 4 {
		a00, a01, a02, a03 := a0[k+0], a0[k+1], a0[k+2], a0[k+3]
		c00 += a00*b0[k+0] + a01*b0[k+1] + a02*b0[k+2] + a03*b0[k+3]
		c01 += a00*b1[k+0] + a01*b1[k+1] + a02*b1[k+2] + a03*b1[k+3]
	}
	for ; k < kb; k++ {
		ak := a0[k]
		c00 += ak * b0[k]
		c01 += ak * b1[k]
	}
	C[i0+0][j0+0] += alpha * c00
	C[i0+0][j0+1] += alpha * c01
}

func microKernel1x1(Ablk Matrix, Bpan Matrix, C Matrix, alpha float64, i0, j0, kb int) {
	a0 := Ablk[i0+0]
	b0 := Bpan[j0+0]
	_ = a0[kb-1]; _ = b0[kb-1]
	s := 0.0
	k := 0
	for ; k+3 < kb; k += 4 {
		s += a0[k+0]*b0[k+0] + a0[k+1]*b0[k+1] + a0[k+2]*b0[k+2] + a0[k+3]*b0[k+3]
	}
	for ; k < kb; k++ {
		s += a0[k] * b0[k]
	}
	C[i0+0][j0+0] += alpha * s
}
