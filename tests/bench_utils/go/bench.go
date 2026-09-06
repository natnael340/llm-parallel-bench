// Package benchutil is the shared benchmark harness for all Go benchmarks.
// It mirrors tests/bench_utils.py: reps x iters timing with warmup, median/IQR
// and mean/SD statistics, and the schema-v2 JSON result format.
package benchutil

import (
	"encoding/json"
	"fmt"
	"math"
	"os"
	"sort"
	"strconv"
	"time"
)

type Result struct {
	Median    float64
	IQR       float64
	Mean      float64
	SD        float64
	ElapsedMS []float64
	Reps      int
	Iters     int
}

// --- env helpers: the standard benchmark env contract ---

func envInt(name string, def int) int {
	if v := os.Getenv(name); v != "" {
		if n, err := strconv.Atoi(v); err == nil {
			return n
		}
	}
	return def
}

func Reps(def int) int  { return envInt("BENCH_REPS", def) }
func Iters(def int) int { return envInt("BENCH_ITERS", def) }

func Impl() string {
	if v := os.Getenv("IMPL"); v != "" {
		return v
	}
	return "seq"
}

func Model() string {
	if v := os.Getenv("MODEL"); v != "" {
		return v
	}
	return "baseline"
}

func Out() string { return os.Getenv("BENCH_OUT") }

// --- statistics ---

func Median(vals []float64) float64 {
	s := append([]float64(nil), vals...)
	sort.Float64s(s)
	n := len(s)
	if n%2 == 0 {
		return (s[n/2-1] + s[n/2]) / 2.0
	}
	return s[n/2]
}

// IQR uses the same definition as Python's statistics.quantiles(data, n=4)
// (exclusive, interpolated), so the dispersion figure is comparable across all
// six languages and matches what bench/aggregate.py recomputes. The previous
// truncated nearest-rank indexing disagreed with the Python harness on the
// same samples (e.g. 1.5 vs 5.75 for [10, 10.5, 11, 12, 20]).
func IQR(vals []float64) float64 {
	s := append([]float64(nil), vals...)
	sort.Float64s(s)
	n := len(s)
	if n < 2 {
		return 0
	}
	const nq = 4
	m := n + 1
	var q [3]float64
	for i := 1; i <= 3; i++ {
		j := i * m / nq
		if j < 1 {
			j = 1
		}
		if j > n-1 {
			j = n - 1
		}
		delta := float64(i*m - j*nq)
		q[i-1] = (s[j-1]*(nq-delta) + s[j]*delta) / nq
	}
	return q[2] - q[0]
}

func Mean(vals []float64) float64 {
	sum := 0.0
	for _, v := range vals {
		sum += v
	}
	return sum / float64(len(vals))
}

func SD(vals []float64) float64 {
	if len(vals) < 2 {
		return 0
	}
	m := Mean(vals)
	sq := 0.0
	for _, v := range vals {
		sq += (v - m) * (v - m)
	}
	return math.Sqrt(sq / float64(len(vals)-1))
}

// RunBenchmark runs warmup untimed calls, then reps timed blocks of iters
// calls each, returning per-block mean time per call in milliseconds.
func RunBenchmark(fn func(), reps, iters, warmup int) Result {
	for i := 0; i < warmup; i++ {
		fn()
	}
	perRunMs := make([]float64, reps)
	for r := 0; r < reps; r++ {
		start := time.Now()
		for k := 0; k < iters; k++ {
			fn()
		}
		perRunMs[r] = time.Since(start).Seconds() * 1000 / float64(iters)
	}
	return Result{
		Median:    Median(perRunMs),
		IQR:       IQR(perRunMs),
		Mean:      Mean(perRunMs),
		SD:        SD(perRunMs),
		ElapsedMS: perRunMs,
		Reps:      reps,
		Iters:     iters,
	}
}

func FormatResult(label string, r Result) string {
	return fmt.Sprintf("%s | mean %.2f ms/run ± %.2f SD | median %.2f ms/run ± %.2f IQR (n=%d)",
		label, r.Mean, r.SD, r.Median, r.IQR, r.Reps)
}

type payload struct {
	SchemaVersion int                    `json:"schema_version"`
	Algo          string                 `json:"algo"`
	Lang          string                 `json:"lang"`
	Impl          string                 `json:"impl"`
	Model         string                 `json:"model"`
	ElapsedMS     []float64              `json:"elapsed_ms"`
	Mean          float64                `json:"mean"`
	SD            float64                `json:"sd"`
	Median        float64                `json:"median"`
	IQR           float64                `json:"iqr"`
	Reps          int                    `json:"reps"`
	ItersPerRep   int                    `json:"iters_per_rep"`
	Params        map[string]interface{} `json:"params"`
	Timestamp     string                 `json:"timestamp"`
}

// WriteResult writes the schema-v2 JSON result to path (no-op if empty).
func WriteResult(path string, r Result, algo, impl string, params map[string]interface{}) error {
	if path == "" {
		return nil
	}
	if params == nil {
		params = map[string]interface{}{}
	}
	p := payload{
		SchemaVersion: 2,
		Algo:          algo,
		Lang:          "go",
		Impl:          impl,
		Model:         Model(),
		ElapsedMS:     r.ElapsedMS,
		Mean:          r.Mean,
		SD:            r.SD,
		Median:        r.Median,
		IQR:           r.IQR,
		Reps:          r.Reps,
		ItersPerRep:   r.Iters,
		Params:        params,
		Timestamp:     time.Now().UTC().Format(time.RFC3339),
	}
	data, err := json.MarshalIndent(p, "", "  ")
	if err != nil {
		return err
	}
	return os.WriteFile(path, data, 0644)
}
