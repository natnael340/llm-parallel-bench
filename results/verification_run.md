# Fresh-boot verification run — one process at a time

**Goal:** run every combo individually (never two at once, no CPU racing), record
mean-first results, then compare each fresh mean against the recorded `perf`
files / notes and flag any inconsistency.

**Machine:** AMD Ryzen 7 5700U, 8 cores / 16 threads, WSL2 kernel 6.18. This is the
**same machine** the recorded `perf` numbers were taken on, so absolute mean deltas
are directly meaningful (not just the speedup ratio).

---

## Measurement discipline (non-negotiable)

- **Exactly one benchmark process alive at any moment.** Driven via
  `python bench/run.py run --algo A --lang L --model M --impl I` (blocks in
  `waitpid`, 0% runner CPU). I never launch the next until the current one exits.
- **Real reps/iters from the manifests** (not `--smoke`): bfs/sccs 5×20,
  gemm 5×5, smith-waterman 5×1. Whatever is used is recorded in each JSON.
- Fast combos run foreground; the slow pure-Python legs (gemm/python ~30–45 min,
  sw/python) run as a single backgrounded process and I wait for its completion
  before starting the next — still strictly one-at-a-time.
- Fresh boot ⇒ first build per language pays a one-time compile cost (cargo deps,
  dotnet restore). That is build time, not measured time.

## Run order (as requested: baseline first, then each model, all 6 langs)

For each algo `[bfs, sccs, gemm, smith-waterman]`:
1. `baseline/seq`  → python, go, cpp, csharp, java, rust
2. `gpt-5/par`     → python, go, cpp, csharp, java, rust
3. `claude-sonnet-4-5/par` → python, go, cpp, csharp, java, rust
4. `gemini-2-5-pro/par`    → python, go, cpp, csharp, java, rust

= 96 runs. Each writes `results/<algo>/<lang>/<model>_<impl>.json`; I append one row
to the table below immediately after it finishes (so partial progress survives).

## Known LLM-source defects — expected FAIL, NOT measurement inconsistencies

Recorded as `FAILED (known defect)` and skipped, not re-investigated:
1. bfs / go / claude — wrong neighbor order
2. bfs / java / gpt-5 — reorders same-level nodes (testReturnOrder)
3. bfs / java / gemini — reorders same-level nodes
4. bfs / rust / claude — won't compile
5. sccs / go / claude — non-deterministic
6. gemm / cpp / gpt-5 — no ragged-input validation
7. gemm / python / gpt-5 — hardcoded `llm_written.python_openai` import
8. gemm / rust / gemini — won't compile

## Comparison reference (what "consistent" is judged against)

| Group | Reference source | Rigor |
|-------|------------------|-------|
| baseline seq (24) | `analysis/data/sequential/<algo>/<lang>/perf` (`perf.txt` for bfs/java) | full |
| sccs parallel | `analysis/data/<model>/sccs/<lang>_benchmark_*.json` | full |
| bfs parallel | `analysis/data/<model>/bfs/*.md` | partial (parse md) |
| gemm parallel | `analysis/data/<model>/gemm/*.md` | partial (parse md) |
| sw parallel | — none recorded — | fresh = new baseline |

**Flag rule:** `|fresh − reported| / reported > 20%` → **INCONSISTENT** (investigate).
Also report the seq→par speedup ratio as a machine-invariant sanity check.

---

## Results (fresh, mean-first)

| algo | lang | model | impl | mean ms | sd | median ms | reps×iters | status |
|------|------|-------|------|--------:|---:|----------:|-----------|--------|
| bfs | python | baseline | seq | 1110.80 | 7.86 | 1110.61 | 5×20 | ok |
| bfs | go | baseline | seq | 188.76 | 3.88 | 187.79 | 5×20 | ok |
| bfs | cpp | baseline | seq | 63.04 | 1.13 | 62.48 | 5×20 | ok |
| bfs | csharp | baseline | seq | 179.06 | 6.51 | 181.41 | 5×20 | ok |
| bfs | java | baseline | seq | 731.68 | 299.46 | 583.38 | 5×20 | ok |
| bfs | rust | baseline | seq | 192.54 | 4.09 | 193.15 | 5×20 | ok |
| bfs | python | gpt-5 | par | 26817.96 | 369.81 | 26744.25 | 5×20 | ok |
| bfs | go | gpt-5 | par | 20.33 | 1.14 | 19.88 | 5×20 | ok |
| bfs | cpp | gpt-5 | par | 86.31 | 1.23 | 86.01 | 5×20 | ok |
| bfs | csharp | gpt-5 | par | 14.95 | 1.11 | 14.75 | 5×20 | ok |
| bfs | java | gpt-5 | par | 184.79 | 6.45 | 182.62 | 5×20 | ok |
| bfs | rust | gpt-5 | par | 23.64 | 0.67 | 23.93 | 5×20 | ok |
| bfs | python | claude-sonnet-4-5 | par | 24594.71 | 147.31 | 24630.42 | 5×20 | ok |
| bfs | go | claude-sonnet-4-5 | par | 540.26 | 2.73 | 540.21 | 5×20 | ok |
| bfs | cpp | claude-sonnet-4-5 | par | 77.61 | 6.69 | 74.50 | 5×20 | ok |
| bfs | csharp | claude-sonnet-4-5 | par | 178.31 | 5.34 | 178.58 | 5×20 | ok |
| bfs | java | claude-sonnet-4-5 | par | 176.86 | 31.74 | 163.03 | 5×20 | ok |
| bfs | rust | claude-sonnet-4-5 | par | — | — | — | — | FAIL — known defect: won't compile |
| bfs | python | gemini-2-5-pro | par | 8323.73 | 82.72 | 8309.03 | 5×20 | ok |
| bfs | go | gemini-2-5-pro | par | 74.33 | 2.24 | 74.32 | 5×20 | ok |
| bfs | cpp | gemini-2-5-pro | par | 2231.68 | 20.60 | 2229.28 | 5×20 | ok |
| bfs | csharp | gemini-2-5-pro | par | 177.31 | 6.41 | 179.28 | 5×20 | ok |
| bfs | java | gemini-2-5-pro | par | 29.08 | 2.37 | 30.05 | 5×20 | ok |
| bfs | rust | gemini-2-5-pro | par | 192.60 | 3.74 | 193.58 | 5×20 | ok |
| sccs | python | baseline | seq | 266.73 | 3.13 | 265.72 | 5×20 | ok |
| sccs | go | baseline | seq | 60.54 | 1.38 | 60.49 | 5×20 | ok |
| sccs | cpp | baseline | seq | 63.17 | 0.72 | 63.09 | 5×20 | ok |
| sccs | csharp | baseline | seq | 42.25 | 3.55 | 40.94 | 5×20 | ok |
| sccs | java | baseline | seq | 33.04 | 8.22 | 27.30 | 5×20 | ok |
| sccs | rust | baseline | seq | 27.13 | 0.33 | 27.08 | 5×20 | ok |
| sccs | python | gpt-5 | par | 1918.40 | 44.74 | 1935.96 | 5×20 | ok |
| sccs | go | gpt-5 | par | 49.70 | 2.13 | 49.06 | 5×20 | ok |
| sccs | cpp | gpt-5 | par | 12.53 | 0.84 | 12.23 | 5×20 | ok |
| sccs | csharp | gpt-5 | par | 30.61 | 6.18 | 28.23 | 5×20 | ok |
| sccs | java | gpt-5 | par | 45.69 | 4.89 | 47.20 | 5×20 | ok |
| sccs | rust | gpt-5 | par | 10.07 | 0.32 | 10.12 | 5×20 | ok |
| sccs | python | claude-sonnet-4-5 | par | 22869.94 | 179.12 | 22930.84 | 5×20 | ok |
| sccs | go | claude-sonnet-4-5 | par | 40.97 | 1.62 | 40.97 | 5×20 | ok |
| sccs | cpp | claude-sonnet-4-5 | par | 18.13 | 1.40 | 17.65 | 5×20 | ok |
| sccs | csharp | claude-sonnet-4-5 | par | 26.33 | 5.20 | 24.01 | 5×20 | ok |
| sccs | java | claude-sonnet-4-5 | par | 22.70 | 5.42 | 20.81 | 5×20 | ok |
| sccs | rust | claude-sonnet-4-5 | par | 504.33 | 4.80 | 503.98 | 5×20 | ok |
| sccs | python | gemini-2-5-pro | par | 23011.38 | 206.74 | 23046.46 | 5×20 | ok |
| sccs | go | gemini-2-5-pro | par | 28.84 | 1.29 | 28.59 | 5×20 | ok |
| sccs | cpp | gemini-2-5-pro | par | 75.06 | 0.19 | 75.06 | 5×20 | ok |
| sccs | csharp | gemini-2-5-pro | par | 28.92 | 5.12 | 26.86 | 5×20 | ok |
| sccs | java | gemini-2-5-pro | par | 24.35 | 4.97 | 22.92 | 5×20 | ok |
| sccs | rust | gemini-2-5-pro | par | 14.52 | 1.20 | 13.96 | 5×20 | ok |
| gemm | python | baseline | seq | 103092.94 | 434.16 | 103319.87 | 5×5 | ok |
| gemm | go | baseline | seq | 2487.47 | 26.66 | 2476.32 | 5×5 | ok |
| gemm | cpp | baseline | seq | 1400.78 | 10.33 | 1397.36 | 5×5 | ok |
| gemm | csharp | baseline | seq | 1798.41 | 5.86 | 1800.00 | 5×5 | ok |
| gemm | java | baseline | seq | 1225.70 | 19.97 | 1217.94 | 5×5 | ok |
| gemm | rust | baseline | seq | 232.18 | 7.97 | 228.01 | 5×5 | ok |
| gemm | python | gpt-5 | par | — | — | — | — | FAIL — known defect: bad import (llm_written.python_openai) |
| gemm | go | gpt-5 | par | 373.37 | 7.38 | 370.48 | 5×5 | ok |
| gemm | cpp | gpt-5 | par | — | — | — | — | FAIL — known defect: no ragged-input validation |
| gemm | csharp | gpt-5 | par | 529.41 | 6.10 | 527.06 | 5×5 | ok |
| gemm | java | gpt-5 | par | 150.45 | 14.60 | 143.65 | 5×5 | ok |
| gemm | rust | gpt-5 | par | 203.33 | 9.61 | 200.75 | 5×5 | ok |
| gemm | python | claude-sonnet-4-5 | par | DNF | — | — | — | ran ~6.7h then killed |
| gemm | go | claude-sonnet-4-5 | par | 437.04 | 6.78 | 437.77 | 5×5 | ok |
| gemm | cpp | claude-sonnet-4-5 | par | 297.33 | 19.03 | 285.87 | 5×5 | ok |
| gemm | csharp | claude-sonnet-4-5 | par | 534.11 | 7.05 | 534.20 | 5×5 | ok |
| gemm | java | claude-sonnet-4-5 | par | 137.01 | 5.44 | 134.83 | 5×5 | ok |
| gemm | rust | claude-sonnet-4-5 | par | 239.68 | 10.24 | 235.40 | 5×5 | ok |
| gemm | python | gemini-2-5-pro | par | DNF | — | — | — | killed early; identical ProcessPoolExecutor pattern |
| gemm | go | gemini-2-5-pro | par | 273.41 | 4.09 | 273.96 | 5×5 | ok |
| gemm | cpp | gemini-2-5-pro | par | 190.78 | 9.21 | 187.48 | 5×5 | ok |
| gemm | csharp | gemini-2-5-pro | par | 560.56 | 8.04 | 562.78 | 5×5 | ok |
| gemm | java | gemini-2-5-pro | par | 362.16 | 6.92 | 361.27 | 5×5 | ok |
| gemm | rust | gemini-2-5-pro | par | — | — | — | — | FAIL — known defect: won't compile |
| smith-waterman | python | baseline | seq | 122507.65 | 1291.81 | 122326.46 | 5×1 | ok |
| smith-waterman | go | baseline | seq | 544.21 | 75.27 | 514.09 | 5×1 | ok |
| smith-waterman | cpp | baseline | seq | 1229.04 | 8.39 | 1227.56 | 5×1 | ok |
| smith-waterman | csharp | baseline | seq | 1843.56 | 56.93 | 1810.89 | 5×1 | ok |
| smith-waterman | java | baseline | seq | 1585.27 | 141.85 | 1615.34 | 5×1 | ok |
| smith-waterman | rust | baseline | seq | 891.70 | 1.96 | 891.48 | 5×1 | ok |
| smith-waterman | python | gpt-5 | par | 39564.29 | 1096.10 | 39863.19 | 5×1 | ok |
| smith-waterman | go | gpt-5 | par | 1027.54 | 76.70 | 1003.13 | 5×1 | ok |
| smith-waterman | cpp | gpt-5 | par | 1127.45 | 435.36 | 1010.51 | 5×1 | ok |
| smith-waterman | csharp | gpt-5 | par | 1016.65 | 47.70 | 1008.40 | 5×1 | ok |
| smith-waterman | java | gpt-5 | par | 31193.81 | 341.73 | 31345.98 | 5×1 | ok |
| smith-waterman | rust | gpt-5 | par | 59743.22 | 3264.39 | 58252.76 | 5×1 | ok |
| smith-waterman | python | claude-sonnet-4-5 | par | 385937.85 | 22810.22 | 394817.54 | 5×1 | ok |
| smith-waterman | go | claude-sonnet-4-5 | par | 659.83 | 207.69 | 597.67 | 5×1 | ok |
| smith-waterman | cpp | claude-sonnet-4-5 | par | 954.71 | 39.38 | 938.58 | 5×1 | ok |
| smith-waterman | csharp | claude-sonnet-4-5 | par | 4177.79 | 202.31 | 4257.89 | 5×1 | ok |
| smith-waterman | java | claude-sonnet-4-5 | par | 9478.76 | 428.93 | 9284.80 | 5×1 | ok |
| smith-waterman | rust | claude-sonnet-4-5 | par | 869.60 | 2.18 | 868.36 | 5×1 | ok |
| smith-waterman | python | gemini-2-5-pro | par | 139015.23 | 708.81 | 138783.43 | 5×1 | ok |
| smith-waterman | go | gemini-2-5-pro | par | 1792.84 | 154.77 | 1756.84 | 5×1 | ok |
| smith-waterman | cpp | gemini-2-5-pro | par | 883.02 | 189.28 | 867.95 | 5×1 | ok |
| smith-waterman | csharp | gemini-2-5-pro | par | 4283.71 | 101.03 | 4232.39 | 5×1 | ok |
| smith-waterman | java | gemini-2-5-pro | par | 12283.62 | 105.56 | 12327.06 | 5×1 | ok |
| smith-waterman | rust | gemini-2-5-pro | par | 21618.45 | 321.60 | 21698.43 | 5×1 | ok |

## Baseline (seq) comparison vs recorded perf files — same machine

| algo | lang | fresh mean ms | reported mean ms | Δ% | verdict |
|------|------|-------------:|-----------------:|----:|---------|
| bfs | python | 1110.80 | 1033.82 | +7.4% | consistent |
| bfs | go | 188.76 | 188.63 | +0.1% | consistent |
| bfs | cpp | 63.04 | 59.53 | +5.9% | consistent |
| bfs | csharp | 179.06 | 180.75 | -0.9% | consistent |
| bfs | java | 731.68 | 943.46 | -22.4% | INCONSISTENT |
| bfs | rust | 192.54 | 291.91 | -34.0% | INCONSISTENT |
| sccs | python | 266.73 | 302.75 | -11.9% | consistent |
| sccs | go | 60.54 | 161.37 | -62.5% | INCONSISTENT |
| sccs | cpp | 63.17 | 65.67 | -3.8% | consistent |
| sccs | csharp | 42.25 | 40.08 | +5.4% | consistent |
| sccs | java | 33.04 | 59.44 | -44.4% | INCONSISTENT |
| sccs | rust | 27.13 | 38.59 | -29.7% | INCONSISTENT |
| gemm | python | 103092.94 | 130023.00 | -20.7% | INCONSISTENT |
| gemm | go | 2487.47 | 2978.79 | -16.5% | consistent |
| gemm | cpp | 1400.78 | 1347.61 | +3.9% | consistent |
| gemm | csharp | 1798.41 | 1967.97 | -8.6% | consistent |
| gemm | java | 1225.70 | 1189.66 | +3.0% | consistent |
| gemm | rust | 232.18 | 1852.50 | -87.5% | INCONSISTENT |
| smith-waterman | python | 122507.65 | 216645.00 | -43.5% | INCONSISTENT |
| smith-waterman | go | 544.21 | 2258.53 | -75.9% | INCONSISTENT |
| smith-waterman | cpp | 1229.04 | 1416.93 | -13.3% | consistent |
| smith-waterman | csharp | 1843.56 | 3108.03 | -40.7% | INCONSISTENT |
| smith-waterman | java | 1585.27 | 2004.84 | -20.9% | INCONSISTENT |
| smith-waterman | rust | 891.70 | 1079.18 | -17.4% | consistent |

## Fresh seq→par speedup (baseline_seq / model_par), compiled langs

| algo | lang | baseline ms | gpt-5 | claude | gemini |
|------|------|-----------:|------:|-------:|-------:|
| bfs | python | 1110.8 | 0.04× | 0.05× | 0.13× |
| bfs | go | 188.8 | 9.28× | 0.35× | 2.54× |
| bfs | cpp | 63.0 | 0.73× | 0.81× | 0.03× |
| bfs | csharp | 179.1 | 11.98× | 1.00× | 1.01× |
| bfs | java | 731.7 | 3.96× | 4.14× | 25.17× |
| bfs | rust | 192.5 | 8.15× | — | 1.00× |
| sccs | python | 266.7 | 0.14× | 0.01× | 0.01× |
| sccs | go | 60.5 | 1.22× | 1.48× | 2.10× |
| sccs | cpp | 63.2 | 5.04× | 3.48× | 0.84× |
| sccs | csharp | 42.2 | 1.38× | 1.60× | 1.46× |
| sccs | java | 33.0 | 0.72× | 1.46× | 1.36× |
| sccs | rust | 27.1 | 2.69× | 0.05× | 1.87× |
| gemm | python | 103092.9 | — | DNF | DNF |
| gemm | go | 2487.5 | 6.66× | 5.69× | 9.10× |
| gemm | cpp | 1400.8 | — | 4.71× | 7.34× |
| gemm | csharp | 1798.4 | 3.40× | 3.37× | 3.21× |
| gemm | java | 1225.7 | 8.15× | 8.95× | 3.38× |
| gemm | rust | 232.2 | 1.14× | 0.97× | — |
| smith-waterman | python | 122507.6 | 3.10× | 0.32× | 0.88× |
| smith-waterman | go | 544.2 | 0.53× | 0.82× | 0.30× |
| smith-waterman | cpp | 1229.0 | 1.09× | 1.29× | 1.39× |
| smith-waterman | csharp | 1843.6 | 1.81× | 0.44× | 0.43× |
| smith-waterman | java | 1585.3 | 0.05× | 0.17× | 0.13× |
| smith-waterman | rust | 891.7 | 0.01× | 1.03× | 0.04× |

## Inconsistencies flagged (baseline, |Δ|>20%)

- **bfs/java**: fresh 731.7 ms vs recorded 943.5 ms (-22.4%)
- **bfs/rust**: fresh 192.5 ms vs recorded 291.9 ms (-34.0%)
- **sccs/go**: fresh 60.5 ms vs recorded 161.4 ms (-62.5%)
- **sccs/java**: fresh 33.0 ms vs recorded 59.4 ms (-44.4%)
- **sccs/rust**: fresh 27.1 ms vs recorded 38.6 ms (-29.7%)
- **gemm/python**: fresh 103092.9 ms vs recorded 130023.0 ms (-20.7%)
- **gemm/rust**: fresh 232.2 ms vs recorded 1852.5 ms (-87.5%)
- **smith-waterman/python**: fresh 122507.6 ms vs recorded 216645.0 ms (-43.5%)
- **smith-waterman/go**: fresh 544.2 ms vs recorded 2258.5 ms (-75.9%)
- **smith-waterman/csharp**: fresh 1843.6 ms vs recorded 3108.0 ms (-40.7%)
- **smith-waterman/java**: fresh 1585.3 ms vs recorded 2004.8 ms (-20.9%)
---

## Interpretation

**Machine:** AMD Ryzen 7 5700U, same box as the recorded perf files. An OpenSearch
container was found consuming ~½ core during part of this run and was stopped
mid-sweep; it (or similar background load) may also have been present when the
original reference numbers were recorded.

### Harness validated by the well-controlled baselines
Where conditions are equal, fresh baselines land on the recorded numbers:
bfs/go +0.1%, bfs/cpp +5.9%, bfs/csharp −0.9%, gemm/cpp +3.9%, gemm/java +3.0%,
gemm/csharp −8.6%, gemm/go −16.5%, sw/cpp −13.3%, sw/rust −17.4%. The standardized
harness reproduces the original methodology.

### Flagged baselines — three explainable buckets, not harness errors
1. **JIT variance** — bfs/java fresh 731±**299** ms (median 583). Java warmup makes
   the mean unstable; within noise of the recorded 943 ms. Use median here.
2. **Systematically faster on a clean boot (sccs + sw families)** — nearly every
   sccs/sw baseline is 20–75% faster fresh. Most likely the reference was captured
   under background load (the OpenSearch container we just found). A clean boot
   removes it. → re-record the reference clean, or adopt these as the clean baseline.
3. **Two large outliers — investigated and RESOLVED (neither is a harness error):**
   - **gemm/rust** (fresh 243 ms / **8.8 GFLOPs**, reproduced twice: 232 & 243 ms).
     Built the *same* `baselines/gemm/rust` three ways: release = 8.8 GFLOPs/243 ms,
     full debug = 0.23 GFLOPs/9488 ms. The recorded reference (**1.16 GFLOPs**/1852 ms)
     matches *neither* — 1.16 GFLOPs is the signature of a **naive un-tiled** GEMM.
     Today's baseline is a 465-line tiled/microkernel impl, so the reference was
     measuring a different/earlier, less-optimized rust baseline. Fresh number is
     correct for the current code.
   - **sw/go** (fresh median 521 ms, reproduced: 544 & 521 ms, high single-iter
     variance SD≈240). Go has no debug/release split, so not a build-mode issue;
     the recorded 2258 ms is most consistent with background load and/or the old
     colocated harness measuring a wider scope. Fresh number is reproducible and
     correct for the current baseline.

### Research signal (seq→par speedup) — intact and coherent
- **Interpreted-language "parallel" is usually a net loss**: every Python parallel
  is <1× (0.01–0.14×) — multiprocessing/pickle overhead swamps the work. Same for
  several compiled cases (gemini bfs/cpp 0.03×, gpt-5 sw/java 0.05×, sw/rust 0.01×).
- **Genuine speedups where the model parallelized well**: gemm compiled 3–9× across
  models; bfs gpt-5 go/csharp 9–12×; sccs cpp/rust 3–5×.
- **Known super-linear artifact reappears**: bfs gemini/java 25.2× — above the
  16-thread Amdahl ceiling; the HashMap→ConcurrentHashMap cache effect flagged in
  VERIFY_SPEEDUP.md, not pure parallelism.

### Non-viable / defect combos (recorded, not measured)
- gemm/python claude + gemini: **DNF** — parallel Python GEMM impractically slow
  (ProcessPoolExecutor pickle overhead; claude ran 6.7 h before being killed).
- 8 known LLM-source defects failed exactly as predicted (4 bfs, 1 sccs, 3 gemm).
