# LLM-Parallel-Bench

### Benchmarking LLM-Generated Parallel Implementations Across Algorithms and Languages

This repository contains the full experimental framework, generated code, and benchmarking scripts used to evaluate the parallelization capabilities of large language models (LLMs), including GPT-5, Claude Sonnet 4.5, and Gemini 2.5 Pro.

The project spans multiple algorithmic domains—DFS/BFS, GEMM, and SCC reduction—and multiple programming languages (Python, Go, C++, and C#). It measures correctness, determinism, and performance on a common workload (100k vertices, 334 SCCs).

---

## Repository Structure

```
LLM-PARALLEL-BENCH/
│
├── app/                     # CLI wrappers and driver scripts
├── BFS/                     # DFS/BFS case study implementations
├── GEMM/                    # GEMM case study implementations
├── scc/                     # SCC/Tarjan reduction case study
│
├── llm_written/             # All LLM-generated code
│   ├── gpt-5/
│   ├── gemini-2.5-pro/
│   └── claude-sonnet-4.5/
│       ├── python/
│       ├── go/
│       ├── cpp/
│       └── csharp/
│
├── reports/                 # Benchmark results
│   ├── sequential/
│   ├── gpt5/
│   ├── gemini_2.5_pro/
│   └── claude_sonnet_4.5/
│
├── tests/                   # Correctness tests
├── utils/                   # Graph generators, timers, helpers
│
├── llm-parallel-bench.csproj
├── go.mod
├── .python-version
├── .env
└── README.md
```

---

## Reports and Reproducibility

All benchmark results—mean runtime, standard deviation, speedup, Amdahl ratios, and logs—are stored under:

```
reports/
```

Each LLM has its own folder.

---

## LLM-Generated Code Transparency

All LLM-produced implementations (unmodified) are stored under:

```
llm_written/
```

Organized by model → language.

---

## Algorithms Covered

- GEMM (dense linear algebra)
- DFS (irregular traversals)
- SCC reduction (fine-grained parallelism)

---

## Requirements

- Python 3.10+
- Go 1.20+
- .NET 7+
- C++17 compiler with OpenMP
- Linux/WSL2 recommended

---
