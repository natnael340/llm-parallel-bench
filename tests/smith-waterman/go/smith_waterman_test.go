package sw_test

import (
	"math"
	"os"
	"strconv"
	"strings"
	"testing"

	benchutil "github.com/natnael340/llm-parallel-bench/tests/bench_utils/go"
	staging "github.com/natnael340/llm-parallel-bench/tests/smith-waterman/go/staging"
)

const epsilon = 1e-6

func almostEqual(a, b, delta float64) bool {
	return math.Abs(a-b) <= delta
}

func newSW() *staging.SmithWaterman {
	return staging.NewSmithWaterman(2, -1, -1)
}

func TestPerfectMatch(t *testing.T) {
	a, b, score, identity := staging.BenchFindAlignment(newSW(), "ACGT", "ACGT")
	if a != b {
		t.Errorf("expected aligned sequences equal, got %q vs %q", a, b)
	}
	if score != 8 {
		t.Errorf("expected score 8, got %d", score)
	}
	if !almostEqual(identity, 100.0, epsilon) {
		t.Errorf("expected identity 100.0, got %f", identity)
	}
}

func TestNoMatch(t *testing.T) {
	a, b, score, identity := staging.BenchFindAlignment(newSW(), "AAAA", "TTTT")
	if a != "" || b != "" || score != 0 || !almostEqual(identity, 0.0, epsilon) {
		t.Errorf("expected empty alignment / score 0, got %q %q %d %f", a, b, score, identity)
	}
}

func TestPartialMatch(t *testing.T) {
	a, b, score, identity := staging.BenchFindAlignment(newSW(), "ACGTACGT", "TACGTGCA")
	if a != "TACGT" || b != "TACGT" || score != 10 || !almostEqual(identity, 100.0, epsilon) {
		t.Errorf("partial match: got %q %q %d %f", a, b, score, identity)
	}
}

func TestGapInQuery(t *testing.T) {
	a, b, score, identity := staging.BenchFindAlignment(newSW(), "ACGT", "ACAGT")
	if a != "AC-GT" || b != "ACAGT" || score != 7 || !almostEqual(identity, 80.0, epsilon) {
		t.Errorf("gap in query: got %q %q %d %f", a, b, score, identity)
	}
}

func TestGapInReference(t *testing.T) {
	a, b, score, identity := staging.BenchFindAlignment(newSW(), "ACAGT", "ACGT")
	if a != "ACAGT" || b != "AC-GT" || score != 7 || !almostEqual(identity, 80.0, epsilon) {
		t.Errorf("gap in reference: got %q %q %d %f", a, b, score, identity)
	}
}

func TestSingleCharMatch(t *testing.T) {
	a, b, score, identity := staging.BenchFindAlignment(newSW(), "A", "A")
	if a != "A" || b != "A" || score != 2 || !almostEqual(identity, 100.0, epsilon) {
		t.Errorf("single char match: got %q %q %d %f", a, b, score, identity)
	}
}

func readSWInput(t *testing.T) (string, string, int, float64) {
	path := os.Getenv("SW_INPUT")
	if path == "" {
		t.Skip("SW_INPUT not set")
	}
	data, err := os.ReadFile(path)
	if err != nil {
		t.Skipf("cannot read SW_INPUT: %v", err)
	}
	lines := strings.Split(string(data), "\n")
	score, _ := strconv.Atoi(strings.TrimSpace(lines[2]))
	identity, _ := strconv.ParseFloat(strings.TrimSpace(lines[3]), 64)
	return strings.TrimSpace(lines[0]), strings.TrimSpace(lines[1]), score, identity
}

func TestLargeSequencesFromFile(t *testing.T) {
	query, reference, expScore, expIdentity := readSWInput(t)
	a, b, score, identity := staging.BenchFindAlignment(newSW(), query, reference)
	if len(a) != len(b) {
		t.Errorf("aligned lengths differ: %d vs %d", len(a), len(b))
	}
	if score != expScore {
		t.Errorf("expected score %d, got %d", expScore, score)
	}
	if !almostEqual(identity, expIdentity, epsilon) {
		t.Errorf("expected identity %f, got %f", expIdentity, identity)
	}
}

func TestSWSpeed(t *testing.T) {
	query, reference, _, _ := readSWInput(t)
	sw := newSW()

	reps := benchutil.Reps(5)
	iters := benchutil.Iters(1)

	r := benchutil.RunBenchmark(func() {
		staging.BenchFindAlignment(sw, query, reference)
	}, reps, iters, 1)

	t.Log(benchutil.FormatResult("SW large sequences", r))

	params := map[string]interface{}{"query_len": len(query), "reference_len": len(reference)}
	if err := benchutil.WriteResult(benchutil.Out(), r, "smith-waterman", benchutil.Impl(), params); err != nil {
		t.Fatalf("failed to write result JSON: %v", err)
	}
}
