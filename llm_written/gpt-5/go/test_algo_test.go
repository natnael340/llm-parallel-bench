package main

import (
	"os"
	"runtime"
	"testing"
	"time"
	"fmt"
)

func TestParityAndDeterminism(t *testing.T) {
	if err := os.MkdirAll("evidence", 0o755); err != nil {
		t.Fatalf("mkdir evidence: %v", err)
	}
	cases := []struct{
		name string
		g    *Graph
	}{
		{"empty", NewGraph(0)},
		{"single_no_edges", NewGraph(1)},
		{"line3", func() *Graph { g := NewGraph(3); g.AddEdge(0,1); g.AddEdge(1,2); return g }()},
		{"one_scc5", func() *Graph { g := NewGraph(5); for i:=0;i<5;i++{ g.AddEdge(i,(i+1)%5) }; g.AddEdge(0,2); g.AddEdge(3,1); return g }()},
		{"rand_med", buildRandomGraph(20, 8, 40, 42)},
	}

	summary := ""
	fail := false
	for _, tc := range cases {
		seq := tc.g.ReduceEdgesSequential()
		par := tc.g.ReduceEdgesParallel(0)
		if !sameEdges(seq, par) {
			fail = true
			summary += fmt.Sprintf("[FAIL] %s: seq vs par mismatch (|seq|=%d, |par|=%d)\n", tc.name, len(seq), len(par))
		} else {
			summary += fmt.Sprintf("[OK]   %s: outputs match (%d edges)\n", tc.name, len(seq))
		}
		par2 := tc.g.ReduceEdgesParallel(0)
		h1 := hashEdges(par)
		h2 := hashEdges(par2)
		if h1 != h2 {
			fail = true
			summary += fmt.Sprintf("[FAIL] %s: parallel determinism mismatch (%s vs %s)\n", tc.name, h1[:8], h2[:8])
		} else {
			summary += fmt.Sprintf("[OK]   %s: parallel deterministic (hash %s)\n", tc.name, h1[:8])
		}
	}

	big := buildRandomGraph(300, 24, 900, 123)
	start := time.Now()
	_ = big.ReduceEdgesSequential()
	seqDur := time.Since(start)
	start = time.Now()
	_ = big.ReduceEdgesParallel(0)
	parDur := time.Since(start)
	spd := float64(seqDur) / float64(parDur)
	perfLine := fmt.Sprintf("LargeN: |V|=%d, SCCs=%d, t_seq=%v, t_par=%v, speedup=%.2fx, workers<=%d\n",
		big.V, len(big.FindSCCs()), seqDur, parDur, spd, runtime.GOMAXPROCS(0))

	_ = os.WriteFile("evidence/perf.txt", []byte(perfLine), 0o644)

	if fail {
		summary = "RESULT: FAIL\n" + summary
		_ = os.WriteFile("evidence/run_summary.txt", []byte(summary), 0o644)
		t.Fatalf("\n%s", summary)
	}
	summary = "RESULT: OK\n" + summary
	_ = os.WriteFile("evidence/run_summary.txt", []byte(summary), 0o644)
}
