User provided a sequential C++ Smith-Waterman implementation (class SmithWaterman) with:
- constructMatrix: fills DP matrix with nested i,j loops
- findHighestScore: scans matrix for max cell
- traceback: reconstructs alignment
- findAlignment: orchestrates constructMatrix + traceback

Goal: Provide a correct, deterministic, resource-bounded parallel implementation, tests, and justification.
Constraints:
- Use OpenMP for C++ with fixed schedules.
- Implement differential tests comparing sequential vs parallel across edge/small/medium/large.
- Repeat parallel twice to ensure determinism.
- Provide tiny-input sequential fallback and cap threads to CPU count.
Deliverables:
- algo_parallel.cpp (final implementation)
- test_smith_waterman.cpp (tests/runner)
- JUSTIFICATION.md (evidence-backed explanation)
Artifacts will write evidence to evidence/*.txt from the runner.