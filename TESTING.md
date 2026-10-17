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
   `results/<algo>/<lang>/<model>_<impl>.json` (latest result only — a re-run
   replaces it);
5. also copies it into `results/runs/<unix epoch>/<algo>/<lang>/`, the history
   folder for this invocation, with a `run_meta.json` and that run's
   `failures.json`. `--smoke` and `--print-cmd` create no run folder.
   `aggregate.py` ignores `results/runs/`.

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

## Determinism sweep

`bench/determinism.py` reruns every LLM `par` variant under different
scheduling conditions and checks that its output stays the same across runs and
matches the baseline sequential output.

```bash
python bench/determinism.py sweep                          # everything, 3 runs per condition
python bench/determinism.py sweep --algo sccs --lang go --sweep cores,race
python bench/determinism.py report                         # rebuild summary only
```

Conditions are varied one factor at a time (default: all cores, threads = cores):

| Sweep | Levels | Held fixed |
|-------|--------|------------|
| `cores` | 1, 2, 4, 8, all (`taskset -c 0-(k-1)`) | threads = cores |
| `threads` | 1, 2, 4, 8, 16, 32 | 4 cores |
| `load` | 4 / 8 CPU spinners, 8 memory-copy spinners, pinned to the same cores | 4 cores |
| `priority` | `nice -n 19`, `chrt --batch`, `chrt --idle`, with 2 CPU spinners | 4 cores |
| `race` | Go `-race`, C++ `-fsanitize=thread`, at all cores and at 2 | Go/C++ only |

Thread count is set through `GOMAXPROCS`, `OMP_NUM_THREADS`, `RAYON_NUM_THREADS`,
`DOTNET_PROCESSOR_COUNT`, Java `-XX:ActiveProcessorCount`, and `BENCH_CPU_COUNT`
(the Python harness patches `os.cpu_count`). Go `runtime.NumCPU()`, C++
`hardware_concurrency()` and Rust `available_parallelism()` can't be overridden;
they follow the affinity mask. Each dump records the core count the runtime saw,
and `threads_override_effective` in the summary shows whether the override took.

Each harness has a digest mode (`BENCH_DIGEST_OUT`): it runs its correctness
tests, calls the entry once on the benchmark input, writes the raw output, and
skips timing. Equality rules:

- **bfs, smith-waterman**: exact output.
- **sccs**: SCC partition must equal the baseline's; the reduced edge set must
  be identical across runs (a valid reduction need not equal the baseline's).
  `raw_order_stable` says whether the returned edge order was stable too.
- **gemm**: bitwise across runs; against the baseline, `max_abs_diff` and
  `max_rel_diff` are reported when bits differ.

Results go to `results/determinism/<algo>/<lang>/<model>_par.json` (every run
plus the verdict) and `results/determinism/summary.{csv,md}`. Dumps are kept
under `bench/build/determinism/` (the first run and the first divergent one).
A run whose unit tests fail still counts if it produced output
(`runs_tests_failed`), so determinism is reported for incorrect variants too.

Caveats: no real-time priorities (needs root); on SMT CPUs `0-(k-1)` may pick
sibling hyperthreads; TSan reports under OpenMP may be false positives
(`openmp_tsan_false_positives_possible`); variants that time out on their first
run are recorded as DNF and skipped.
