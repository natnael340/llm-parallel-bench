User provided a sequential Python implementation of the Smith-Waterman local alignment algorithm (class SmithWaterman with constructMatrix, findHighestScore, traceback, findAlignment). Task: transform into a correct, deterministic, resource-bounded parallel implementation, create rigorous differential tests, and provide justification.

Constraints:
- Keep public API behavior (alignment strings, score, percent identity) identical to the baseline.
- Implement minimal, deterministic parallelization; Python preference: vectorization (NumPy) first; else ProcessPoolExecutor.
- Add small-N sequential fallback and bound resource usage to CPU count.
- Provide tests comparing sequential vs parallel across edge/small/medium/large inputs, repeat parallel runs for determinism, and basic performance gate.
- Deliverables: algo_parallel.py (final impl), test/run scripts, JUSTIFICATION.md, evidence files.
