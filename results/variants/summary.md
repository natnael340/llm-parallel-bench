# Variants: SCSS discovery swap

Hand-made one-change versions (see Readme, Variants). Not part of the 72 implementations
and not included in `results/summary.csv`. Graph: 100,000 nodes, clusters of 300, 5 reps x 20 iters.

Reference rows come from `results/summary.csv`. Variant rows ran on 16 Nov 2026, 00:25-01:04,
log `results/logs/variants_sccs_20261116_0024.log`, commit fbd8c43.

| Lang | Version | Median (ms) | IQR (ms) | Speedup vs recursive baseline | Source |
|---|---|---|---|---|---|
| Java | Baseline, recursive Tarjan | 59.70 | 16.89 | 1.00x | summary.csv |
| Java | Baseline, iterative Tarjan (variant) | 43.64 | 24.74 | 1.37x | variants/sccs/java/variant-iterative-tarjan_seq.json |
| Java | GPT-5, iterative Kosaraju (reported) | 40.35 | 9.84 | 1.48x | summary.csv |
| Java | GPT-5, recursive Tarjan (variant) | 31.83 | 4.56 | 1.88x | variants/sccs/java/variant-gpt-5-recursive-tarjan_par.json |
| Python | Baseline, recursive Tarjan | 286.45 | 5.70 | 1.00x | summary.csv |
| Python | Gemini, iterative Tarjan (reported) | 24714.03 | 67.55 | 0.0116x | summary.csv |
| Python | Gemini, recursive Tarjan (variant) | 23239.88 | 161.03 | 0.0123x | variants/sccs/python/variant-gemini-recursive-tarjan_par.json |

Swap factor (time with the model's discovery / time with recursive Tarjan, same parallel code):

- GPT-5 Java: 40.35 / 31.83 = 1.27, so iterative Kosaraju made it about 1.27x slower.
- Gemini Python: 24714.03 / 23239.88 = 1.06, so iterative Tarjan made it about 1.06x slower.

Caveat: the reference rows were measured in earlier sessions than the variants.
All variants passed the same 5 correctness tests. No determinism sweep was run for them.
