package llm_written

// import (
// 	"fmt"
// 	"math"
// 	"os"
// 	"runtime"
// 	"time"
// )

// func main() {
// 	fmt.Println("=== Performance Tests ===")
// 	var perfDetails []string

// 	sizes := []int{256, 512}

// 	for _, size := range sizes {
// 		fmt.Printf("Testing %dx%d matrix...\n", size, size)
// 		A := createTestMatrix(size, size, 1.0)
// 		B := createTestMatrix(size, size, 2.0)

// 		// Sequential
// 		startSeq := time.Now()
// 		CSeq, err := GemmSequential(A, B, 1.0, nil, 0.0, 0, 0, 0)
// 		durSeq := time.Since(startSeq)
// 		if err != nil {
// 			fmt.Printf("  Sequential error: %v\n", err)
// 			continue
// 		}

// 		// Parallel (run 3 times, take best)
// 		var durPar time.Duration = math.MaxInt64
// 		var CPar Matrix
// 		for run := 0; run < 3; run++ {
// 			start := time.Now()
// 			CPar, err = Gemm(A, B, 1.0, nil, 0.0, 0, 0, 0)
// 			dur := time.Since(start)
// 			if err != nil {
// 				fmt.Printf("  Parallel run %d error: %v\n", run+1, err)
// 				continue
// 			}
// 			if dur < durPar {
// 				durPar = dur
// 			}
// 		}

// 		// Verify correctness
// 		if !matricesEqual(CSeq, CPar) {
// 			fmt.Printf("  [FAIL] Outputs differ!\n")
// 			perfDetails = append(perfDetails, fmt.Sprintf("FAIL: %dx%d (outputs differ)", size, size))
// 			continue
// 		}

// 		speedup := float64(durSeq) / float64(durPar)
// 		cores := runtime.NumCPU()
// 		efficiency := speedup / float64(cores) * 100.0

// 		fmt.Printf("  Sequential: %.2f ms\n", float64(durSeq.Microseconds())/1000.0)
// 		fmt.Printf("  Parallel:   %.2f ms\n", float64(durPar.Microseconds())/1000.0)
// 		fmt.Printf("  Speedup:    %.2fx\n", speedup)
// 		fmt.Printf("  Cores:      %d\n", cores)
// 		fmt.Printf("  Efficiency: %.1f%%\n\n", efficiency)

// 		perfDetails = append(perfDetails, fmt.Sprintf("%dx%d: seq=%.2fms, par=%.2fms, speedup=%.2fx, cores=%d, eff=%.1f%%",
// 			size, size,
// 			float64(durSeq.Microseconds())/1000.0,
// 			float64(durPar.Microseconds())/1000.0,
// 			speedup, cores, efficiency))
// 	}

// 	// Write to perf.txt
// 	perfFile, err := os.Create("perf.txt")
// 	if err != nil {
// 		fmt.Printf("Error creating perf.txt: %v\n", err)
// 		os.Exit(1)
// 	}
// 	for _, line := range perfDetails {
// 		fmt.Fprintln(perfFile, line)
// 	}
// 	perfFile.Close()
// 	fmt.Println("Performance results written to perf.txt")
// }

// Helper functions
// func createTestMatrix(rows, cols int, seed float64) Matrix {
// 	m := generateMatrix(rows, cols)
// 	for i := 0; i < rows; i++ {
// 		for j := 0; j < cols; j++ {
// 			m[i][j] = seed + float64(i*cols+j)*0.1
// 		}
// 	}
// 	return m
// }

// func matricesEqual(a, b Matrix) bool {
// 	if len(a) != len(b) {
// 		return false
// 	}
// 	for i := range a {
// 		if len(a[i]) != len(b[i]) {
// 			return false
// 		}
// 		for j := range a[i] {
// 			if a[i][j] != b[i][j] {
// 				return false
// 			}
// 		}
// 	}
// 	return true
// }
