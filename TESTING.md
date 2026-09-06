# Benchmark Testing Guide

All benchmarks run through a single plug-and-play runner. You never edit a
source file to switch implementation, model, or language — the runner stages
the selected code, generates an adapter, builds, and runs it.

```bash
# one combo
python bench/run.py run --algo bfs --lang go --model gpt-5 --impl par

# the sequential baseline (impl defaults to seq for --model baseline)
python bench/run.py run --algo bfs --lang go --model baseline

# the whole matrix (baseline seq + every model's par, all algos/langs)
python bench/run.py matrix

# a filtered slice; --smoke does a reps=1 iters=1 build+correctness sanity check
python bench/run.py matrix --algo bfs,sccs --lang cpp,go,rust --smoke

# list every runnable combo
python bench/run.py list

# roll all results/ JSONs up into a research-ready table
python bench/aggregate.py
```

Algorithms: `bfs`, `gemm`, `sccs`, `smith-waterman`.
Languages: `python`, `go`, `cpp`, `java`, `csharp`, `rust`.
Models: `baseline` (sequential), `gpt-5`, `claude-sonnet-4-5`, `gemini-2-5-pro`.

## How it works

Each `algo × lang` has a manifest at `bench/manifests/<algo>/<lang>.json` that
lists, per variant (`<model>/<impl>`), which implementation files to copy and a
small adapter mapping a canonical entry symbol onto whatever that implementation
exposes. The runner:

1. copies the selected variant's files into a gitignored staging dir
   (`tests/<algo>/<lang>/staging/`, or `bench/rust/src/staged/` for Rust) and
   generates the adapter — **`llm_written/` and `baselines/` are never edited**;
2. builds the harness against the staging dir;
3. runs the benchmark with the env contract below;
4. validates the emitted JSON against schema v2 and writes it to
   `results/<algo>/<lang>/<model>_<impl>.json`.

Only one variant is staged per run, so the sequential and parallel legs of a
combo go through the identical harness and timing loop.

## Env contract

The runner sets these; you only set them by hand if you run a staged binary
directly (see `--print-cmd`).

| Variable | Meaning |
|----------|---------|
| `IMPL` | `seq` or `par` |
| `MODEL` | model name, or `baseline` |
| `BENCH_OUT` | path to write the result JSON |
| `BENCH_REPS` | timed repeats (default per manifest) |
| `BENCH_ITERS` | calls per repeat (default per manifest) |
| `SW_INPUT` | Smith-Waterman only: shared large-sequence input file |

## Result schema (v2)

Uniform across all languages and algorithms. Raw `elapsed_ms` is always stored,
so any statistic can be recomputed later.

```json
{
  "schema_version": 2,
  "algo": "bfs", "lang": "go", "impl": "par", "model": "gpt-5",
  "elapsed_ms": [12.1, 12.4, 12.2, 12.3, 12.2],
  "mean": 12.24, "sd": 0.11, "median": 12.2, "iqr": 0.15,
  "reps": 5, "iters_per_rep": 20,
  "params": { "graph_size": 2000 },
  "timestamp": "..."
}
```

`bench/aggregate.py` walks `results/**/*.json`, recomputes the stats from
`elapsed_ms` (warns on any disagreement), joins each parallel row to its
baseline sequential row per `algo × lang`, and writes `results/summary.csv`
(with `speedup_mean` / `speedup_median`) plus a paper-ready `results/summary.md`.
`python bench/aggregate.py --verify` only checks stored-vs-raw and exits non-zero
on mismatch.

## Zero-interference guarantees

Timing happens inside each benchmark process, never in the runner, so runner
overhead cannot leak into `elapsed_ms`:

- all staging and compilation finish before the benchmark process starts;
- the benchmark is a single subprocess awaited with a blocking wait (0% runner
  CPU); benchmarks never run in parallel;
- `--exec` replaces the runner process with the benchmark entirely
  (`os.execvpe`), so nothing else is alive during measurement;
- `--print-cmd` prints the bare staged/built command + env to run by hand.

## Reps / iters per algorithm

BFS and SCC default to `reps=5 × iters=20`. GEMM and Smith-Waterman default to
`reps=5 × iters=5` and `iters=1` respectively (each call is expensive). Override
with `--reps` / `--iters`; whatever is used is recorded in the JSON. The runner
uses the same reps/iters for a combo's seq and par legs.

## Notes

- The full matrix takes hours (pure-Python GEMM/SW dominate). `matrix` resumes
  by default — combos whose result JSON already exists are skipped unless
  `--force`. Use `--algo` / `--lang` / `--model` / `--impl` / `--skip-lang` to
  slice, and per-combo `--timeout`.
- Correctness is a gate: every harness runs its assertions before the timed
  section and exits non-zero on failure, so the runner rejects the result.
  Failures are recorded in `results/failures.json` and the matrix continues.
- GEMM tile sizes (`MB/NB/KB`) are sweep-tuned per language and recorded in each
  result's `params`, so cross-language GFLOPs comparisons stay honest.
