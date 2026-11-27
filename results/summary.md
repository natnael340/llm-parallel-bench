# Benchmark summary

## bfs

| lang | model | impl | mean (ms) | SD | median (ms) | IQR | speedup (mean) | tests |
|------|-------|------|-----------|----|-------------|-----|----------------|-------|
| cpp | baseline | seq | 64.37 | 0.76 | 64.14 | 1.31 | 1.00x | pass |
| cpp | claude-sonnet-4-5 | par | 73.08 | 0.93 | 73.06 | 1.75 | 0.88x | pass |
| cpp | gemini-2-5-pro | par | 2389.16 | 16.51 | 2383.85 | 28.86 | 0.03x | pass |
| cpp | gpt-5 | par | 92.39 | 1.99 | 92.40 | 3.71 | 0.70x | pass |
| csharp | baseline | seq | 88.53 | 0.40 | 88.30 | 0.74 | 1.00x | pass |
| csharp | claude-sonnet-4-5 | par | 184.54 | 10.23 | 187.48 | 20.00 | 0.48x | pass |
| csharp | gemini-2-5-pro | par | 180.96 | 6.98 | 178.31 | 12.08 | 0.49x | pass |
| csharp | gpt-5 | par | 16.36 | 0.90 | 16.14 | 1.64 | 5.41x | pass |
| go | baseline | seq | 194.26 | 5.86 | 197.16 | 10.71 | 1.00x | pass |
| go | claude-sonnet-4-5 | par | 577.31 | 3.98 | 577.95 | 7.67 | 0.34x | FAIL |
| go | gemini-2-5-pro | par | 78.10 | 2.09 | 78.31 | 3.20 | 2.49x | pass |
| go | gpt-5 | par | 19.99 | 0.99 | 19.71 | 1.44 | 9.72x | pass |
| java | baseline | seq | 150.03 | 18.30 | 143.46 | 23.35 | 1.00x | pass |
| java | claude-sonnet-4-5 | par | 139.33 | 5.04 | 137.47 | 7.25 | 1.08x | pass |
| java | gemini-2-5-pro | par | 24.75 | 1.94 | 23.82 | 2.87 | 6.06x | FAIL |
| java | gpt-5 | par | 181.37 | 17.91 | 174.17 | 21.63 | 0.83x | FAIL |
| python | baseline | seq | 606.38 | 1.86 | 606.63 | 3.29 | 1.00x | pass |
| python | claude-sonnet-4-5 | par | 25085.78 | 164.11 | 25185.09 | 306.83 | 0.02x | pass |
| python | gemini-2-5-pro | par | 8232.76 | 83.44 | 8197.30 | 143.81 | 0.07x | pass |
| python | gpt-5 | par | 27256.51 | 75.44 | 27256.80 | 133.63 | 0.02x | pass |
| rust | baseline | seq | 128.75 | 3.67 | 126.89 | 6.96 | 1.00x | pass |
| rust | claude-sonnet-4-5 | par | 17.60 | 1.43 | 17.16 | 2.72 | 7.31x | pass |
| rust | gemini-2-5-pro | par | 196.06 | 2.81 | 195.30 | 4.65 | 0.66x | pass |
| rust | gpt-5 | par | 21.99 | 0.59 | 21.94 | 1.13 | 5.86x | pass |

## gemm

| lang | model | impl | mean (ms) | SD | median (ms) | IQR | speedup (mean) | tests |
|------|-------|------|-----------|----|-------------|-----|----------------|-------|
| cpp | baseline | seq | 1482.27 | 13.87 | 1489.33 | 19.79 | 1.00x | pass |
| cpp | claude-sonnet-4-5 | par | 228.37 | 3.11 | 226.69 | 4.68 | 6.49x | pass |
| cpp | gemini-2-5-pro | par | 189.54 | 2.31 | 189.74 | 4.22 | 7.82x | pass |
| cpp | gpt-5 | par | 263.31 | 8.56 | 260.37 | 13.03 | 5.63x | pass |
| csharp | baseline | seq | 1511.07 | 14.54 | 1516.85 | 28.27 | 1.00x | pass |
| csharp | claude-sonnet-4-5 | par | 604.72 | 15.42 | 599.77 | 27.97 | 2.50x | pass |
| csharp | gemini-2-5-pro | par | 591.26 | 2.98 | 590.41 | 4.68 | 2.56x | pass |
| csharp | gpt-5 | par | 594.98 | 10.97 | 595.40 | 20.92 | 2.54x | pass |
| go | baseline | seq | 3975.28 | 173.35 | 3988.10 | 315.47 | 1.00x | pass |
| go | claude-sonnet-4-5 | par | 436.78 | 3.89 | 435.85 | 7.10 | 9.10x | pass |
| go | gemini-2-5-pro | par | 330.77 | 5.90 | 330.59 | 10.69 | 12.02x | pass |
| go | gpt-5 | par | 383.76 | 2.41 | 383.21 | 4.52 | 10.36x | pass |
| java | baseline | seq | 1281.52 | 5.57 | 1284.38 | 10.26 | 1.00x | pass |
| java | claude-sonnet-4-5 | par | 143.95 | 4.68 | 141.71 | 6.91 | 8.90x | pass |
| java | gemini-2-5-pro | par | 363.97 | 12.34 | 360.22 | 16.24 | 3.52x | pass |
| java | gpt-5 | par | 161.41 | 7.03 | 164.53 | 13.37 | 7.94x | pass |
| python | baseline | seq | 104234.74 | 826.82 | 103751.59 | 1309.85 | 1.00x | pass |
| python | claude-sonnet-4-5 | par | 1472768.05 | 21668.46 | 1480890.00 | 38726.99 | 0.07x | pass |
| python | gemini-2-5-pro | par | 14208.13 | 39.03 | 14222.06 | 69.07 | 7.34x | pass |
| python | gpt-5 | par | 35096.38 | 81.25 | 35080.48 | 140.13 | 2.97x | pass |
| rust | baseline | seq | 1572.76 | 80.03 | 1531.62 | 124.88 | 1.00x | pass |
| rust | claude-sonnet-4-5 | par | 257.24 | 2.95 | 256.99 | 5.21 | 6.11x | pass |
| rust | gemini-2-5-pro | par | 2763.62 | 6.19 | 2762.38 | 11.68 | 0.57x | pass |
| rust | gpt-5 | par | 236.50 | 3.10 | 237.03 | 5.63 | 6.65x | pass |

## sccs

| lang | model | impl | mean (ms) | SD | median (ms) | IQR | speedup (mean) | tests |
|------|-------|------|-----------|----|-------------|-----|----------------|-------|
| cpp | baseline | seq | 67.64 | 0.76 | 67.79 | 1.27 | 1.00x | pass |
| cpp | claude-sonnet-4-5 | par | 18.74 | 0.16 | 18.65 | 0.30 | 3.61x | pass |
| cpp | gemini-2-5-pro | par | 31.04 | 1.05 | 30.91 | 1.86 | 2.18x | pass |
| cpp | gpt-5 | par | 13.34 | 0.30 | 13.18 | 0.47 | 5.07x | pass |
| csharp | baseline | seq | 45.39 | 2.50 | 44.41 | 3.00 | 1.00x | pass |
| csharp | claude-sonnet-4-5 | par | 28.92 | 5.59 | 26.75 | 7.15 | 1.57x | pass |
| csharp | gemini-2-5-pro | par | 29.82 | 5.58 | 27.32 | 8.23 | 1.52x | FAIL |
| csharp | gpt-5 | par | 32.68 | 7.08 | 29.62 | 8.27 | 1.39x | pass |
| go | baseline | seq | 63.53 | 2.92 | 64.85 | 4.63 | 1.00x | pass |
| go | claude-sonnet-4-5 | par | 41.21 | 1.69 | 41.10 | 2.85 | 1.54x | FAIL |
| go | gemini-2-5-pro | par | 31.09 | 1.38 | 30.57 | 2.55 | 2.04x | pass |
| go | gpt-5 | par | 52.51 | 0.57 | 52.36 | 0.91 | 1.21x | pass |
| java | baseline | seq | 56.81 | 9.48 | 59.70 | 16.89 | 1.00x | pass |
| java | claude-sonnet-4-5 | par | 27.76 | 2.92 | 28.54 | 5.25 | 2.05x | pass |
| java | gemini-2-5-pro | par | 32.94 | 3.81 | 34.37 | 7.36 | 1.72x | pass |
| java | gpt-5 | par | 39.81 | 6.00 | 40.35 | 9.84 | 1.43x | pass |
| python | baseline | seq | 288.37 | 3.15 | 286.45 | 5.70 | 1.00x | pass |
| python | claude-sonnet-4-5 | par | 24552.07 | 440.06 | 24839.41 | 817.14 | 0.01x | pass |
| python | gemini-2-5-pro | par | 24721.21 | 34.78 | 24714.03 | 67.54 | 0.01x | pass |
| python | gpt-5 | par | 1958.25 | 42.18 | 1978.56 | 77.30 | 0.15x | pass |
| rust | baseline | seq | 30.97 | 0.12 | 30.97 | 0.18 | 1.00x | pass |
| rust | claude-sonnet-4-5 | par | 568.16 | 1.15 | 568.07 | 2.14 | 0.05x | pass |
| rust | gemini-2-5-pro | par | 14.25 | 0.68 | 14.29 | 1.18 | 2.17x | pass |
| rust | gpt-5 | par | 10.17 | 0.38 | 9.97 | 0.63 | 3.05x | pass |

## smith-waterman

| lang | model | impl | mean (ms) | SD | median (ms) | IQR | speedup (mean) | tests |
|------|-------|------|-----------|----|-------------|-----|----------------|-------|
| cpp | baseline | seq | 808.87 | 4.34 | 806.79 | 8.22 | 1.00x | pass |
| cpp | claude-sonnet-4-5 | par | 700.58 | 2.65 | 700.42 | 4.25 | 1.15x | pass |
| cpp | gemini-2-5-pro | par | 355.23 | 18.10 | 347.96 | 34.93 | 2.28x | pass |
| cpp | gpt-5 | par | 401.29 | 20.75 | 395.53 | 32.00 | 2.02x | pass |
| csharp | baseline | seq | 1965.65 | 76.42 | 1937.67 | 148.61 | 1.00x | pass |
| csharp | claude-sonnet-4-5 | par | 3471.35 | 86.97 | 3461.12 | 145.17 | 0.57x | pass |
| csharp | gemini-2-5-pro | par | 3509.73 | 21.16 | 3520.37 | 36.78 | 0.56x | pass |
| csharp | gpt-5 | par | 1060.46 | 12.04 | 1059.78 | 18.72 | 1.85x | pass |
| go | baseline | seq | 2279.55 | 45.62 | 2261.66 | 73.68 | 1.00x | pass |
| go | claude-sonnet-4-5 | par | 628.99 | 19.65 | 619.62 | 31.83 | 3.62x | pass |
| go | gemini-2-5-pro | par | 1951.43 | 11.72 | 1955.42 | 21.00 | 1.17x | pass |
| go | gpt-5 | par | 1191.05 | 70.39 | 1165.63 | 108.14 | 1.91x | pass |
| java | baseline | seq | 1297.49 | 51.60 | 1280.84 | 73.08 | 1.00x | pass |
| java | claude-sonnet-4-5 | par | 9727.18 | 147.84 | 9687.49 | 211.12 | 0.13x | pass |
| java | gemini-2-5-pro | par | 12417.00 | 110.88 | 12451.92 | 209.28 | 0.10x | pass |
| java | gpt-5 | par | 33905.97 | 96.46 | 33869.04 | 149.65 | 0.04x | pass |
| python | baseline | seq | 129587.43 | 452.00 | 129528.00 | 642.29 | 1.00x | pass |
| python | claude-sonnet-4-5 | par | 454049.96 | 2448.01 | 453766.73 | 4130.33 | 0.29x | pass |
| python | gemini-2-5-pro | par | 140578.84 | 5062.14 | 138598.86 | 6942.37 | 0.92x | pass |
| python | gpt-5 | par | 30965.79 | 1633.74 | 30354.63 | 2235.97 | 4.18x | pass |
| rust | baseline | seq | 1129.62 | 1.03 | 1129.62 | 1.84 | 1.00x | pass |
| rust | claude-sonnet-4-5 | par | 948.39 | 0.87 | 948.50 | 1.32 | 1.19x | pass |
| rust | gemini-2-5-pro | par | 16898.43 | 193.29 | 16870.65 | 366.12 | 0.07x | pass |
| rust | gpt-5 | par | 59090.11 | 290.11 | 59012.86 | 504.43 | 0.02x | pass |
