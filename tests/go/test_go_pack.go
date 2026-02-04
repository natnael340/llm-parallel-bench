// fast_gemm_sweep.go
package main

import (
	"encoding/csv"
	"fmt"
	"math"
	"math/rand"
	"os"
	"sort"
	"time"
	gemm_seq "github.com/natnael340/llm-parallel-bench/GEMM/golang"
)

func makeRandomMatrix(r, c int, seed int64) [][]float64 {
	rng := rand.New(rand.NewSource(seed))
	A := make([][]float64, r)
	for i := 0; i < r; i++ {
		row := make([]float64, c)
		for j := 0; j < c; j++ {
			row[j] = rng.Float64()*2.0 - 1.0 // [-1, 1]
		}
		A[i] = row
	}
	return A
}

func zeros(r, c int) [][]float64 {
	C := make([][]float64, r)
	for i := 0; i < r; i++ {
		C[i] = make([]float64, c)
	}
	return C
}

func min(a, b int) int {
	if a < b {
		return a
	}
	return b
}


func timeAvgPerRun(fn func(), minWallSeconds float64, warmup int) float64 {
	for i := 0; i < warmup; i++ {
		fn()
	}
	start := time.Now()
	total := 0.0
	runs := 0
	for total < minWallSeconds {
		fn()
		runs++
		total = time.Since(start).Seconds()
	}
	if runs == 0 {
		return 0.0
	}
	return total / float64(runs)
}

func gflops(m, n, k int, seconds float64) float64 {
	if seconds <= 0 {
		return 0
	}
	return (2.0 * float64(m) * float64(n) * float64(k)) / (seconds * 1e9)
}

func mean(xs []float64) float64 {
	if len(xs) == 0 {
		return 0
	}
	s := 0.0
	for _, x := range xs {
		s += x
	}
	return s / float64(len(xs))
}

// population stddev
func pstdev(xs []float64) float64 {
	if len(xs) == 0 {
		return 0
	}
	m := mean(xs)
	sum := 0.0
	for _, x := range xs {
		d := x - m
		sum += d * d
	}
	return math.Sqrt(sum / float64(len(xs)))
}

// ----------------- Sweep logic -----------------

type Row struct {
	Stage       int
	MB, NB, KB  int
	AvgMs, SdMs float64
	GFLOPS      float64
}

func evalConfig(A, B [][]float64, MB, NB, KB int, repeats int, minWall float64) (avgMs, sdMs, gflopsVal float64) {
	m := len(A)
	k := len(A[0])
	n := len(B[0])

	samples := make([]float64, 0, repeats)
	for i := 0; i < repeats; i++ {
		avgSec := timeAvgPerRun(func() {
			C := zeros(m, n)
			// ---- your GEMM call here ----
			gemm_seq.Gemm(A, B, 1.0, C, 0.0, MB, NB, KB)
		}, minWall, 1)
		samples = append(samples, avgSec)
	}

	avgSec := mean(samples)
	sdSec := pstdev(samples)
	return avgSec * 1000.0, sdSec * 1000.0, gflops(m, n, k, avgSec)
}

func clamp(v, lo, hi int) int {
	if v < lo {
		return lo
	}
	if v > hi {
		return hi
	}
	return v
}

func floorToMultipleOf(v, step int) int {
	if step <= 0 {
		return v
	}
	return (v / step) * step
}

func stagedSweep(m, n, k int,
	kbList []int,
	coarse []int,
	stepRefine int,
	topKB int,
	topMBNB int,
	repeats int,
	minWall float64,
	csvPath string,
	seedA, seedB int64,
) []Row {

	A := makeRandomMatrix(m, k, seedA)
	B := makeRandomMatrix(k, n, seedB)

	rows := make([]Row, 0, 1024)

	// ----- Stage 1: scan KB with MB=NB=32 -----
	type kbScore struct{ G float64; K int }
	kbScores := make([]kbScore, 0, len(kbList))

	for _, KB := range kbList {
		avgMs, sdMs, flops := evalConfig(A, B, 32, 32, KB, repeats, minWall)
		rows = append(rows, Row{Stage: 1, MB: 32, NB: 32, KB: KB, AvgMs: avgMs, SdMs: sdMs, GFLOPS: flops})
		kbScores = append(kbScores, kbScore{G: flops, K: KB})
	}
	sort.Slice(kbScores, func(i, j int) bool { return kbScores[i].G > kbScores[j].G })
	if topKB > len(kbScores) {
		topKB = len(kbScores)
	}
	chosenKB := make([]int, 0, topKB)
	for i := 0; i < topKB; i++ {
		chosenKB = append(chosenKB, kbScores[i].K)
	}

	// ----- Stage 2: coarse MB/NB for each chosen KB -----
	mbnbCandidates := make(map[[3]int]struct{}) // (MB,NB,KB)
	for _, KB := range chosenKB {
		type scored struct{ G float64; MB, NB int }
		cands := make([]scored, 0, len(coarse)*len(coarse))
		for _, MB := range coarse {
			for _, NB := range coarse {
				avgMs, sdMs, flops := evalConfig(A, B, MB, NB, KB, repeats, minWall)
				rows = append(rows, Row{Stage: 2, MB: MB, NB: NB, KB: KB, AvgMs: avgMs, SdMs: sdMs, GFLOPS: flops})
				cands = append(cands, scored{G: flops, MB: MB, NB: NB})
			}
		}
		sort.Slice(cands, func(i, j int) bool { return cands[i].G > cands[j].G })
		limit := topMBNB
		if limit > len(cands) {
			limit = len(cands)
		}
		for i := 0; i < limit; i++ {
			mbnbCandidates[[3]int{cands[i].MB, cands[i].NB, KB}] = struct{}{}
		}
	}

	// ----- Stage 3: local refinement around each (MB,NB,KB) -----
	refined := make(map[[3]int]struct{})
	for key := range mbnbCandidates {
		MB, NB, KB := key[0], key[1], key[2]
		for _, dmb := range []int{-stepRefine, 0, stepRefine} {
			for _, dnb := range []int{-stepRefine, 0, stepRefine} {
				mb2 := clamp(MB+dmb, 4, m)
				nb2 := clamp(NB+dnb, 4, n)
				mb2 = floorToMultipleOf(mb2, 4)
				nb2 = floorToMultipleOf(nb2, 4)
				if mb2 <= 0 || nb2 <= 0 {
					continue
				}
				refined[[3]int{mb2, nb2, KB}] = struct{}{}
			}
		}
	}

	keys := make([][3]int, 0, len(refined))
	for k3 := range refined {
		keys = append(keys, k3)
	}
	sort.Slice(keys, func(i, j int) bool {
		if keys[i][2] != keys[j][2] {
			return keys[i][2] < keys[j][2]
		}
		if keys[i][0] != keys[j][0] {
			return keys[i][0] < keys[j][0]
		}
		return keys[i][1] < keys[j][1]
	})
	for _, k3 := range keys {
		MB, NB, KB := k3[0], k3[1], k3[2]
		avgMs, sdMs, flops := evalConfig(A, B, MB, NB, KB, repeats, minWall)
		rows = append(rows, Row{Stage: 3, MB: MB, NB: NB, KB: KB, AvgMs: avgMs, SdMs: sdMs, GFLOPS: flops})
	}

	// ----- Save CSV -----
	if csvPath != "" {
		f, err := os.Create(csvPath)
		if err != nil {
			fmt.Printf("failed to create CSV: %v\n", err)
		} else {
			defer f.Close()
			w := csv.NewWriter(f)
			defer w.Flush()
			_ = w.Write([]string{"stage", "MB", "NB", "KB", "avg_ms", "sd_ms", "gflops"})
			for _, r := range rows {
				rec := []string{
					fmt.Sprintf("%d", r.Stage),
					fmt.Sprintf("%d", r.MB),
					fmt.Sprintf("%d", r.NB),
					fmt.Sprintf("%d", r.KB),
					fmt.Sprintf("%.6f", r.AvgMs),
					fmt.Sprintf("%.6f", r.SdMs),
					fmt.Sprintf("%.6f", r.GFLOPS),
				}
				_ = w.Write(rec)
			}
		}
	}

	// ----- Top 10 overall -----
	rowsCopy := append([]Row(nil), rows...)
	sort.Slice(rowsCopy, func(i, j int) bool { return rowsCopy[i].GFLOPS > rowsCopy[j].GFLOPS })
	top := 10
	if top > len(rowsCopy) {
		top = len(rowsCopy)
	}
	fmt.Println("Top 10 configs:")
	for i := 0; i < top; i++ {
		r := rowsCopy[i]
		fmt.Printf("stage%d MB/NB/KB=%d/%d/%d  %.2f ms  ~%.2f GFLOP/s  (±%.2f ms)\n",
			r.Stage, r.MB, r.NB, r.KB, r.AvgMs, r.GFLOPS, r.SdMs)
	}

	return rows
}

// ----------------- main -----------------

func main() {
	// Quick dry-run; raise to 512/1024 for real tests.
	m, n, k := 256, 256, 256

	kbList := []int{16, 32, 48, 64, 96, 128}
	coarse := []int{8, 16, 32, 48, 64}
	stepRefine := 8

	topKB := 2
	topMBNB := 5
	repeats := 3
	minWall := 5.0 // seconds
	csvPath := "gemm_sweep_staged_256_go.csv"

	seedA := int64(1)
	seedB := int64(2)

	_ = stagedSweep(m, n, k,
		kbList, coarse, stepRefine,
		topKB, topMBNB,
		repeats, minWall,
		csvPath, seedA, seedB)
}
