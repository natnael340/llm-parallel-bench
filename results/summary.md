# Benchmark summary

## bfs

| lang | model | impl | mean (ms) | SD | median (ms) | IQR | speedup (mean) |
|------|-------|------|-----------|----|-------------|-----|----------------|
| cpp | baseline | seq | 63.04 | 1.13 | 62.48 | 1.71 | 1.00x |
| cpp | claude-sonnet-4-5 | par | 77.61 | 6.69 | 74.50 | 12.69 | 0.81x |
| cpp | gemini-2-5-pro | par | 2231.68 | 20.60 | 2229.28 | 41.02 | 0.03x |
| cpp | gpt-5 | par | 86.31 | 1.23 | 86.01 | 2.11 | 0.73x |
| csharp | baseline | seq | 179.06 | 6.51 | 181.41 | 11.60 | 1.00x |
| csharp | claude-sonnet-4-5 | par | 178.31 | 5.34 | 178.58 | 10.32 | 1.00x |
| csharp | gemini-2-5-pro | par | 177.31 | 6.41 | 179.28 | 11.97 | 1.01x |
| csharp | gpt-5 | par | 14.95 | 1.11 | 14.75 | 1.87 | 11.98x |
| go | baseline | seq | 188.76 | 3.88 | 187.79 | 5.50 | 1.00x |
| go | claude-sonnet-4-5 | par | 540.26 | 2.73 | 540.21 | 4.33 | 0.35x |
| go | gemini-2-5-pro | par | 74.33 | 2.24 | 74.32 | 3.94 | 2.54x |
| go | gpt-5 | par | 20.33 | 1.14 | 19.88 | 2.09 | 9.28x |
| java | baseline | seq | 962.21 | 459.87 | 981.85 | 904.67 | 1.00x |
| java | claude-sonnet-4-5 | par | 211.17 | 14.07 | 208.74 | 21.93 | 4.56x |
| java | gemini-2-5-pro | par | — | — | — | — | — |
| java | gpt-5 | par | — | — | — | — | — |
| python | baseline | seq | 1110.80 | 7.86 | 1110.61 | 15.10 | 1.00x |
| python | claude-sonnet-4-5 | par | 24594.71 | 147.31 | 24630.42 | 273.89 | 0.05x |
| python | gemini-2-5-pro | par | 8323.73 | 82.72 | 8309.03 | 138.64 | 0.13x |
| python | gpt-5 | par | 26817.96 | 369.81 | 26744.25 | 710.62 | 0.04x |
| rust | baseline | seq | 192.54 | 4.09 | 193.15 | 6.12 | 1.00x |
| rust | gemini-2-5-pro | par | 192.60 | 3.74 | 193.58 | 5.84 | 1.00x |
| rust | gpt-5 | par | 23.64 | 0.67 | 23.93 | 1.21 | 8.15x |

## gemm

| lang | model | impl | mean (ms) | SD | median (ms) | IQR | speedup (mean) |
|------|-------|------|-----------|----|-------------|-----|----------------|
| cpp | baseline | seq | 1400.78 | 10.33 | 1397.36 | 16.64 | 1.00x |
| cpp | claude-sonnet-4-5 | par | 297.33 | 19.03 | 285.87 | 35.72 | 4.71x |
| cpp | gemini-2-5-pro | par | 190.78 | 9.21 | 187.48 | 16.23 | 7.34x |
| csharp | baseline | seq | 1798.41 | 5.86 | 1800.00 | 9.22 | 1.00x |
| csharp | claude-sonnet-4-5 | par | 534.11 | 7.05 | 534.20 | 11.63 | 3.37x |
| csharp | gemini-2-5-pro | par | 560.56 | 8.04 | 562.78 | 15.53 | 3.21x |
| csharp | gpt-5 | par | 529.41 | 6.10 | 527.06 | 11.37 | 3.40x |
| go | baseline | seq | 2487.47 | 26.66 | 2476.32 | 42.63 | 1.00x |
| go | claude-sonnet-4-5 | par | 437.04 | 6.78 | 437.77 | 12.40 | 5.69x |
| go | gemini-2-5-pro | par | 273.41 | 4.09 | 273.96 | 8.05 | 9.10x |
| go | gpt-5 | par | 373.37 | 7.38 | 370.48 | 9.76 | 6.66x |
| java | baseline | seq | 1225.70 | 19.97 | 1217.94 | 29.38 | 1.00x |
| java | claude-sonnet-4-5 | par | 137.01 | 5.44 | 134.83 | 10.39 | 8.95x |
| java | gemini-2-5-pro | par | 362.16 | 6.92 | 361.27 | 10.17 | 3.38x |
| java | gpt-5 | par | 150.45 | 14.60 | 143.65 | 20.96 | 8.15x |
| python | baseline | seq | 103092.94 | 434.16 | 103319.87 | 757.29 | 1.00x |
| python | claude-sonnet-4-5 | par | — | — | — | — | — |
| python | gemini-2-5-pro | par | — | — | — | — | — |
| rust | baseline | seq | 3435.96 | 129.64 | 3409.09 | 225.59 | 1.00x |
| rust | claude-sonnet-4-5 | par | 323.23 | 21.68 | 316.92 | 38.33 | 10.63x |
| rust | gemini-2-5-pro | par | — | — | — | — | — |
| rust | gpt-5 | par | 314.51 | 15.32 | 319.53 | 28.70 | 10.92x |

## sccs

| lang | model | impl | mean (ms) | SD | median (ms) | IQR | speedup (mean) |
|------|-------|------|-----------|----|-------------|-----|----------------|
| cpp | baseline | seq | 128.75 | 1.64 | 129.23 | 3.18 | 1.00x |
| cpp | claude-sonnet-4-5 | par | 37.14 | 4.40 | 35.74 | 6.51 | 3.47x |
| cpp | gemini-2-5-pro | par | 53.55 | 6.05 | 51.34 | 8.25 | 2.40x |
| cpp | gpt-5 | par | 33.13 | 13.11 | 28.56 | 21.29 | 3.89x |
| csharp | baseline | seq | 42.25 | 3.55 | 40.94 | 4.70 | 1.00x |
| csharp | claude-sonnet-4-5 | par | 26.33 | 5.20 | 24.01 | 6.57 | 1.60x |
| csharp | gemini-2-5-pro | par | 28.92 | 5.12 | 26.86 | 7.11 | 1.46x |
| csharp | gpt-5 | par | 30.61 | 6.18 | 28.23 | 7.77 | 1.38x |
| go | baseline | seq | 60.54 | 1.38 | 60.49 | 2.57 | 1.00x |
| go | claude-sonnet-4-5 | par | 40.97 | 1.62 | 40.97 | 2.80 | 1.48x |
| go | gemini-2-5-pro | par | 28.84 | 1.29 | 28.59 | 2.31 | 2.10x |
| go | gpt-5 | par | 49.70 | 2.13 | 49.06 | 3.57 | 1.22x |
| java | baseline | seq | 33.04 | 8.22 | 27.30 | 14.52 | 1.00x |
| java | claude-sonnet-4-5 | par | 22.70 | 5.42 | 20.81 | 7.12 | 1.46x |
| java | gemini-2-5-pro | par | 24.35 | 4.97 | 22.92 | 7.59 | 1.36x |
| java | gpt-5 | par | 45.69 | 4.89 | 47.20 | 7.06 | 0.72x |
| python | baseline | seq | 266.73 | 3.13 | 265.72 | 5.85 | 1.00x |
| python | claude-sonnet-4-5 | par | 22869.94 | 179.12 | 22930.84 | 323.50 | 0.01x |
| python | gemini-2-5-pro | par | 23011.38 | 206.74 | 23046.46 | 405.22 | 0.01x |
| python | gpt-5 | par | 1918.40 | 44.74 | 1935.96 | 81.93 | 0.14x |
| rust | baseline | seq | 48.12 | 0.84 | 48.33 | 1.52 | 1.00x |
| rust | claude-sonnet-4-5 | par | 978.65 | 36.41 | 978.21 | 60.31 | 0.05x |
| rust | gemini-2-5-pro | par | 44.13 | 2.55 | 44.08 | 4.17 | 1.09x |
| rust | gpt-5 | par | 22.29 | 1.49 | 21.66 | 2.74 | 2.16x |

## smith-waterman

| lang | model | impl | mean (ms) | SD | median (ms) | IQR | speedup (mean) |
|------|-------|------|-----------|----|-------------|-----|----------------|
| cpp | baseline | seq | 1229.04 | 8.39 | 1227.56 | 12.54 | 1.00x |
| cpp | claude-sonnet-4-5 | par | 954.71 | 39.38 | 938.58 | 47.52 | 1.29x |
| cpp | gemini-2-5-pro | par | 883.02 | 189.28 | 867.95 | 336.74 | 1.39x |
| cpp | gpt-5 | par | 1127.45 | 435.36 | 1010.51 | 750.29 | 1.09x |
| csharp | baseline | seq | 1843.56 | 56.93 | 1810.89 | 107.57 | 1.00x |
| csharp | claude-sonnet-4-5 | par | 4177.79 | 202.31 | 4257.89 | 382.42 | 0.44x |
| csharp | gemini-2-5-pro | par | 4283.71 | 101.03 | 4232.39 | 151.56 | 0.43x |
| csharp | gpt-5 | par | 1016.65 | 47.70 | 1008.40 | 74.69 | 1.81x |
| go | baseline | seq | 3749.75 | 550.85 | 3560.11 | 1012.85 | 1.00x |
| go | claude-sonnet-4-5 | par | 1001.09 | 227.98 | 973.18 | 437.70 | 3.75x |
| go | gemini-2-5-pro | par | 2355.03 | 568.78 | 2035.98 | 886.70 | 1.59x |
| go | gpt-5 | par | 2009.29 | 853.51 | 1697.01 | 1161.69 | 1.87x |
| java | baseline | seq | 1585.27 | 141.85 | 1615.34 | 208.84 | 1.00x |
| java | claude-sonnet-4-5 | par | 9478.76 | 428.93 | 9284.80 | 734.26 | 0.17x |
| java | gemini-2-5-pro | par | 12283.62 | 105.56 | 12327.06 | 198.39 | 0.13x |
| java | gpt-5 | par | 31193.81 | 341.73 | 31345.98 | 661.39 | 0.05x |
| python | baseline | seq | 122507.65 | 1291.81 | 122326.46 | 2262.58 | 1.00x |
| python | claude-sonnet-4-5 | par | 385937.85 | 22810.22 | 394817.54 | 33438.28 | 0.32x |
| python | gemini-2-5-pro | par | 139015.23 | 708.81 | 138783.43 | 1042.28 | 0.88x |
| python | gpt-5 | par | 39564.29 | 1096.10 | 39863.19 | 1746.01 | 3.10x |
| rust | baseline | seq | 2482.62 | 94.78 | 2470.84 | 183.89 | 1.00x |
| rust | claude-sonnet-4-5 | par | 920.57 | 14.06 | 917.63 | 23.92 | 2.70x |
| rust | gemini-2-5-pro | par | 26587.21 | 3773.95 | 24383.90 | 6469.05 | 0.09x |
| rust | gpt-5 | par | 72469.71 | 4128.33 | 72210.78 | 6584.91 | 0.03x |

## Combos with no measurement

| algo | lang | model | impl | status | detail |
|------|------|-------|------|--------|--------|
| bfs | java | gemini-2-5-pro | par | failed_correctness | fails BFS order test; previously published 30.05 ms, 19.41x |
| bfs | java | gpt-5 | par | failed_correctness | fails BFS order test; previously published 182.62 ms, 3.19x |
| gemm | python | claude-sonnet-4-5 | par | did_not_finish | ran ~6.7h then killed |
| gemm | python | gemini-2-5-pro | par | did_not_finish | killed early; identical ProcessPoolExecutor pattern |
| gemm | rust | gemini-2-5-pro | par | build_failed | does not compile: `n1` not in scope |
