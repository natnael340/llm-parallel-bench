# Benchmark Testing Guide

All benchmarks write a JSON result file and print a summary line. Two env vars control every run:

| Variable | Values | Effect |
|----------|--------|--------|
| `IMPL` | `seq` \| `par` | Selects sequential (baseline) or parallel implementation |
| `BENCH_OUT` | `/path/to/result.json` | Where to write the JSON result (skipped if unset) |

JSON schema (all languages, all algorithms):
```json
{ "algo": "bfs", "lang": "python", "impl": "seq",
  "elapsed_ms": [1.2, 1.3, ...], "median": 1.25, "iqr": 0.05,
  "reps": 5, "iters_per_rep": 20 }
```

---

## Python

Runs from the project root. Swap with `IMPL=seq|par`.

### BFS
```bash
# Correctness + performance (benchmark)
IMPL=seq BENCH_OUT=results/bfs_python_seq.json pytest tests/bfs/python/test_bfs.py --run-perf -v -s
IMPL=par BENCH_OUT=results/bfs_python_par.json pytest tests/bfs/python/test_bfs.py --run-perf -v -s
```

**Swap target:** `tests/bfs/python/par.py` — drop any parallel implementation here and rename its entry-point function to `bfs`.

### GEMM
```bash
IMPL=seq BENCH_OUT=results/gemm_python_seq.json pytest tests/gemm/python/test_gemm.py --run-perf -v -s
IMPL=par BENCH_OUT=results/gemm_python_par.json pytest tests/gemm/python/test_gemm.py --run-perf -v -s
```

### SCC
```bash
# Runs as a standalone script; always requires --out
IMPL=seq python tests/sccs/python/benchmark_scc.py --out results/scc_python_seq.json
IMPL=par python tests/sccs/python/benchmark_scc.py --out results/scc_python_par.json
```

**Note:** run from the project root so the local graph imports resolve.

### Smith-Waterman
```bash
IMPL=seq BENCH_OUT=results/sw_python_seq.json pytest tests/smith-waterman/python/test_smith_waterman.py --run-perf -v -s
IMPL=par BENCH_OUT=results/sw_python_par.json pytest tests/smith-waterman/python/test_smith_waterman.py --run-perf -v -s
```

**Note:** requires `tests/smith-waterman/python/main.py` (baseline) and `algo_parallel.py` (parallel) to be present. Copy from `baselines/smith-waterman/python/` and `llm_written/<model>/smith-waterman/python/` respectively.

---

## Go

Module root: project root (`go.mod` module `github.com/natnael340/llm-parallel-bench`).

### BFS

The test file imports a specific LLM model's implementation. **To swap model, edit line ~11 of `tests/bfs/go/bfs_test.go`:**

```go
// Current (GPT-5 parallel):
bfsgo "github.com/natnael340/llm-parallel-bench/llm_written/gpt-5/bfs/go"

// Switch to baseline (sequential):
bfsgo "github.com/natnael340/llm-parallel-bench/baselines/bfs/go"

// Switch to Claude Sonnet 4.5:
bfsgo "github.com/natnael340/llm-parallel-bench/llm_written/claude-sonnet-4-5/bfs/go"

// Switch to Gemini 2.5 Pro:
bfsgo "github.com/natnael340/llm-parallel-bench/llm_written/gemini-2-5-pro/bfs/go"
```

Also update the function call in `TestBFSSpeed` to match (e.g. `bfsgo.Bfs()` for baseline vs `bfsgo.BfsParallel()` for parallel).

```bash
# Run correctness tests
go test ./tests/bfs/go/... -v

# Run performance test only
IMPL=par BENCH_OUT=results/bfs_go_par.json go test ./tests/bfs/go/... -run TestBFSSpeed -v
```

### SCC

`IMPL` env var controls seq vs par at runtime — no file edits needed.

```bash
# Sequential baseline
IMPL=seq go run tests/sccs/go/benchmark.go --out results/scc_go_seq.json

# Parallel
IMPL=par go run tests/sccs/go/benchmark.go --out results/scc_go_par.json
```

**To switch SCC model:** edit the imports at the top of `tests/sccs/go/benchmark.go`:
```go
graphpar "github.com/natnael340/llm-parallel-bench/scc/scssgo/par"
graphseq "github.com/natnael340/llm-parallel-bench/scc/scssgo/seq"
```

---

## C++

No build system — compile manually with `g++`. All commands run from the relevant test subdirectory.

### BFS — Sequential (baseline)

```bash
cd tests/bfs/cpp

g++ -std=c++17 -O2 -o test_bfs_seq \
    test_bfs.cpp \
    ../../../baselines/bfs/cpp/bfs_seq.cpp \
    ../../../baselines/bfs/cpp/graph.cpp \
    -I../../../baselines/bfs/cpp \
    -I../../bench_utils/cpp

BENCH_OUT=../../../results/bfs_cpp_seq.json ./test_bfs_seq
```

### BFS — Parallel (LLM-written)

The parallel test file hardcodes which model to include. **To swap model, edit `tests/bfs/cpp/test_bfs_parallel.cpp` lines 4–6:**

```cpp
// Current (GPT-5):
#include "../../llm_written/gpt-5/bfs/cpp/graph.h"
#include "../../llm_written/gpt-5/bfs/cpp/bfs_parallel.hpp"
#include "../../llm_written/gpt-5/bfs/cpp/bfs_seq.hpp"

// Switch to Claude Sonnet 4.5:
#include "../../llm_written/claude-sonnet-4-5/bfs/cpp/graph.h"
#include "../../llm_written/claude-sonnet-4-5/bfs/cpp/bfs_parallel.hpp"

// Switch to Gemini 2.5 Pro:
#include "../../llm_written/gemini-2-5-pro/bfs/cpp/graph.h"
#include "../../llm_written/gemini-2-5-pro/bfs/cpp/bfs_parallel.hpp"
```

```bash
cd tests/bfs/cpp

g++ -std=c++17 -O2 -o test_bfs_par \
    test_bfs_parallel.cpp \
    ../../../llm_written/gpt-5/bfs/cpp/bfs_parallel.cpp \
    ../../../llm_written/gpt-5/bfs/cpp/graph.cpp \
    -I../../../llm_written/gpt-5/bfs/cpp \
    -I../../bench_utils/cpp

BENCH_OUT=../../../results/bfs_cpp_par.json ./test_bfs_par
```

### SCC

Toggle the `#include` comment at lines 9–10 of `tests/sccs/cpp/benchmark.cpp`:

```cpp
// Sequential:
#include "./seq/graph.cpp"
//#include "./par/graph.cpp"

// Parallel (default):
//#include "./seq/graph.cpp"
#include "./par/graph.cpp"
```

```bash
cd tests/sccs/cpp

# Sequential
g++ -std=c++17 -O2 -o benchmark benchmark.cpp -I../../bench_utils/cpp
IMPL=seq ./benchmark --out ../../../results/scc_cpp_seq.json

# Parallel (after toggling include above and recompiling)
g++ -std=c++17 -O2 -o benchmark benchmark.cpp -I../../bench_utils/cpp
IMPL=par ./benchmark --out ../../../results/scc_cpp_par.json
```

---

## Java

No build system — compile with `javac`, run with `java`.

### BFS

The `Bfs` wrapper class in `tests/bfs/java/TestBfs.java` (lines 5–9) hardcodes which implementation to call. **To swap, edit that class:**

```java
// Current (parallel):
class Bfs {
    public static List<Integer> run(Graph graph, int start) {
        BfsParallel bfs = new BfsParallel();
        return bfs.run(graph, start);
    }
}

// Switch to sequential baseline:
class Bfs {
    public static List<Integer> run(Graph graph, int start) {
        BfsSequential bfs = new BfsSequential();
        return bfs.run(graph, start);
    }
}
```

```bash
cd tests/bfs/java

# Sequential (baseline)
javac -cp . \
    BfsTests.java \
    ../../../baselines/bfs/java/BfsSequential.java \
    ../../../baselines/bfs/java/Graph.java

IMPL=seq BENCH_OUT=../../../results/bfs_java_seq.json java -cp .:../../../baselines/bfs/java BfsTests

# Parallel (GPT-5)
javac -cp . \
    BfsTests.java \
    ../../../llm_written/gpt-5/bfs/java/BfsParallel.java \
    ../../../llm_written/gpt-5/bfs/java/Graph.java

IMPL=par BENCH_OUT=../../../results/bfs_java_par.json java -cp .:../../../llm_written/gpt-5/bfs/java BfsTests
```

### SCC

Toggle the import comment at lines 1–2 of `tests/sccs/java/Benchmark.java`:

```java
// Sequential:
import seq.Graph;
//import par.Graph;

// Parallel:
//import seq.Graph;
import par.Graph;
```

```bash
cd tests/sccs/java

# Sequential
javac -cp .:../../../baselines/sccs/java/ \
    Benchmark.java ../../../baselines/sccs/java/Graph.java

IMPL=seq java -cp .:../../../baselines/sccs/java/ Benchmark \
    --out ../../../results/scc_java_seq.json

# Parallel (GPT-5)
javac -cp .:../../../llm_written/gpt-5/sccs/java/ \
    Benchmark.java ../../../llm_written/gpt-5/sccs/java/AlgoParallel.java

IMPL=par java -cp .:../../../llm_written/gpt-5/sccs/java/ Benchmark \
    --out ../../../results/scc_java_par.json
```

---

## C#

### BFS

Toggle the `using` alias at line 7 of `tests/bfs/csharp/TestBfs.cs`:

```csharp
// Sequential (baseline):
using Bfs = BfsSequential;

// Parallel (LLM-written):
using Bfs = BfsParallel;
```

```bash
# Run from the directory containing the .csproj that includes TestBfs.cs
IMPL=seq BENCH_OUT=results/bfs_cs_seq.json dotnet test
IMPL=par BENCH_OUT=results/bfs_cs_par.json dotnet test
```

### SCC

Toggle the `using` alias at line 2 of `tests/sccs/csharp/benchmark.cs`:

```csharp
// Parallel (default):
using Graph = SCC.Par.Graph;

// Sequential:
using Graph = SCC.Seq.Graph;
```

```bash
IMPL=seq dotnet run -- --out results/scc_cs_seq.json
IMPL=par dotnet run -- --out results/scc_cs_par.json
```

---

## Results directory

```bash
mkdir -p results
```

All `BENCH_OUT` paths above write JSON files there. Because `elapsed_ms` (raw per-repeat timings)
is always stored, you can recompute mean, std, or any other statistic later without re-running:

```python
import json, statistics
d = json.load(open("results/bfs_python_par.json"))
print("median:", d["median"], "iqr:", d["iqr"])
print("mean:", statistics.mean(d["elapsed_ms"]))
print("stdev:", statistics.stdev(d["elapsed_ms"]))
```
