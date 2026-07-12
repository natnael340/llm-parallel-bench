# Speedup Verification TODO (strong-scaling)

## Why this exists
Reported speedups compare the **sequential baseline** against the **parallel
implementation at full thread count**. That comparison changes two things at once:
the thread count *and* (sometimes) the data structure / memory layout. So a single
speedup number does not prove the gain came from parallelism.

The clearest case is **Gemini Java BFS = 23.31x**. The sequential baseline uses
`HashMap`; the parallel version uses `ConcurrentHashMap`. 23.31x is *above* the
Amdahl ceiling (13.89x on 16 cores), i.e. super-linear, so part or all of it is a
cache / data-structure effect, not parallelism. This number is currently in the
thesis abstract and must be verified before it stays.

## The test: run the SAME binary at different thread counts
Do **not** modify the model's code. Hold everything constant and vary only the
core count. Whatever speedup survives between 1 thread and N threads is *pure
parallelism*, because nothing else changed.

The Gemini Java BFS sizes its pool from `Runtime.getRuntime().availableProcessors()`
(`BfsParallel.java:25`), so the JVM flag `-XX:ActiveProcessorCount=N` controls the
thread count with zero code edits.

### Commands (Gemini Java BFS)
```bash
cd ~/projects/llm-parallel-bench/llm_written/gemini-2-5-pro/bfs/java
javac *.java

# Use the SAME graph size as the thesis BFS benchmark (2000-node complete graph).
# Adjust the TestBfs arg to match the benchmark input you reported.
for N in 1 2 4 8 16; do
  echo "=== ActiveProcessorCount=$N ==="
  java -XX:ActiveProcessorCount=$N TestBfs performance 2000
done
```

`TestBfs` prints both `Sequential BFS took ...` and `Parallel BFS took ...` each run.
**Track the "Parallel BFS took ..." line across the five thread counts.** The
built-in "Speedup" line is the confounded seq-vs-par number; ignore it for this test.

### Compute the honest parallel speedup
```
true_parallel_speedup(N) = ParallelTime(1 thread) / ParallelTime(N threads)
```

### Decision rule
- **Times drop as threads increase** (e.g. par@16 ~ par@1 / ~10) -> genuine parallel
  speedup. The 23.31x is partly real; report the scaling curve.
- **Times are flat** (par@1 already fast, par@16 barely better) -> the gain is a
  cache/data-structure artifact, NOT parallelism. Pull 23.31x from the abstract and
  report it explicitly as super-linear/cache-attributable.

## Measurement caveats (Java specifically)
- `TestBfs` times a SINGLE seq + single par call with no warmup. The JVM JIT is cold
  on the first run. Either run the loop above 3-5 times and take the **median**, or
  add warmup iterations. Do not trust a one-shot Java timing.
- Fix the heap so every run gets the same GC behaviour: add `-Xms2g -Xmx2g`.
- `ConcurrentHashMap` vs `HashMap` allocate differently; log GC with `-Xlog:gc` if the
  numbers look noisy.

## Scope: which implementations to verify (NOT all 72)
Mandatory:
- [ ] Gemini Java BFS (23.31x) -- in the abstract, must be resolved.

Recommended (cheap, makes the thesis defensible -- show the headline winners scale):
- [ ] GPT-5 C# BFS (11.81x)
- [ ] Claude Rust BFS (11.4x)
- [ ] GPT-5 C++ SCSS (5.03x)
- [ ] Claude Go Smith-Waterman (3.52x, block wavefront)

Skip: all sub-1x slowdowns, all Python (GIL story already clear), and the middling
1.3x-2x results. Report their single number; the scaling plots above are enough to
show the methodology is sound.

### Thread-count control per language (no code edits)
- **Java**:  `java -XX:ActiveProcessorCount=N ...`  (works because pool size comes
  from `availableProcessors()`; verify each impl actually reads that and not a hardcoded count)
- **C# / .NET**: `taskset -c 0-(N-1) dotnet run ...` (Environment.ProcessorCount follows the affinity mask)
- **Rust (Rayon)**: `RAYON_NUM_THREADS=N ./binary`
- **C++ (OpenMP)**: `OMP_NUM_THREADS=N ./binary`
- **Go**: `GOMAXPROCS=N ./binary`
- If an implementation hardcodes its worker count instead of reading the env/flag,
  fall back to `taskset -c 0-(N-1)` to pin physical cores.

## What to write in the thesis once done
One sentence + one strong-scaling figure closes the hole for the whole study:

> "To confirm that reported speedups reflect parallelism rather than incidental
> data-structure effects, strong-scaling experiments were run on a representative
> subset. The headline implementations scale with core count (Figure X), whereas
> Gemini's Java BFS speedup is super-linear and cache-attributable rather than
> parallel, and is therefore excluded from the effective-parallelization comparison."
