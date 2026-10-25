# Benchmark summary

## bfs

| lang | model | impl | mean (ms) | SD | median (ms) | IQR | speedup (mean) | tests |
|------|-------|------|-----------|----|-------------|-----|----------------|-------|
| cpp | baseline | seq | 64.37 | 0.76 | 64.14 | 1.31 | 1.00x | pass |
| cpp | claude-sonnet-4-5 | par | 73.08 | 0.93 | 73.06 | 1.75 | 0.88x | pass |
| cpp | gemini-2-5-pro | par | 2389.16 | 16.51 | 2383.85 | 28.86 | 0.03x | pass |
| cpp | gpt-5 | par | 92.39 | 1.99 | 92.40 | 3.71 | 0.70x | pass |
| csharp | baseline | seq | 185.92 | 9.00 | 188.71 | 17.55 | 1.00x | pass |
| csharp | claude-sonnet-4-5 | par | 185.35 | 5.06 | 182.72 | 8.71 | 1.00x | pass |
| csharp | gemini-2-5-pro | par | 186.48 | 10.39 | 187.71 | 18.79 | 1.00x | pass |
| csharp | gpt-5 | par | 15.68 | 1.97 | 15.36 | 3.26 | 11.86x | pass |
| go | baseline | seq | 194.26 | 5.86 | 197.16 | 10.71 | 1.00x | pass |
| go | claude-sonnet-4-5 | par | 577.31 | 3.98 | 577.95 | 7.67 | 0.34x | FAIL |
| go | gemini-2-5-pro | par | 78.10 | 2.09 | 78.31 | 3.20 | 2.49x | pass |
| go | gpt-5 | par | 19.99 | 0.99 | 19.71 | 1.44 | 9.72x | pass |
| java | baseline | seq | 782.21 | 40.34 | 765.04 | 76.36 | 1.00x | pass |
| java | claude-sonnet-4-5 | par | 171.34 | 8.34 | 168.82 | 11.81 | 4.57x | pass |
| java | gemini-2-5-pro | par | 26.35 | 1.69 | 25.79 | 2.55 | 29.68x | FAIL |
| java | gpt-5 | par | 190.06 | 29.51 | 179.17 | 38.31 | 4.12x | FAIL |
| python | baseline | seq | 1151.26 | 7.42 | 1151.27 | 11.72 | 1.00x | pass |
| python | claude-sonnet-4-5 | par | 25650.64 | 148.00 | 25736.88 | 268.72 | 0.04x | pass |
| python | gemini-2-5-pro | par | 8517.34 | 26.43 | 8519.55 | 49.61 | 0.14x | pass |
| python | gpt-5 | par | 27996.28 | 69.39 | 27984.29 | 105.77 | 0.04x | pass |
| rust | baseline | seq | 205.78 | 2.76 | 204.52 | 4.71 | 1.00x | pass |
| rust | claude-sonnet-4-5 | par | 17.09 | 0.14 | 17.04 | 0.22 | 12.04x | pass |
| rust | gemini-2-5-pro | par | 205.86 | 2.55 | 204.53 | 4.16 | 1.00x | pass |
| rust | gpt-5 | par | 22.43 | 0.43 | 22.21 | 0.79 | 9.18x | pass |

## gemm

| lang | model | impl | mean (ms) | SD | median (ms) | IQR | speedup (mean) | tests |
|------|-------|------|-----------|----|-------------|-----|----------------|-------|
| cpp | baseline | seq | 1520.33 | 14.93 | 1517.61 | 29.57 | 1.00x | pass |
| cpp | claude-sonnet-4-5 | par | 222.81 | 2.30 | 222.85 | 4.57 | 6.82x | pass |
| cpp | gemini-2-5-pro | par | 185.54 | 1.81 | 185.72 | 2.86 | 8.19x | pass |
| cpp | gpt-5 | par | 255.61 | 7.01 | 258.57 | 13.33 | 5.95x | pass |
| csharp | baseline | seq | 1909.66 | 18.01 | 1910.64 | 28.53 | 1.00x | pass |
| csharp | claude-sonnet-4-5 | par | 542.02 | 8.13 | 542.08 | 14.91 | 3.52x | pass |
| csharp | gemini-2-5-pro | par | 564.66 | 9.63 | 560.13 | 18.51 | 3.38x | pass |
| csharp | gpt-5 | par | 542.42 | 3.83 | 542.62 | 6.25 | 3.52x | pass |
| go | baseline | seq | 4496.96 | 208.99 | 4574.81 | 380.10 | 1.00x | pass |
| go | claude-sonnet-4-5 | par | 426.66 | 3.79 | 425.79 | 7.08 | 10.54x | pass |
| go | gemini-2-5-pro | par | 318.87 | 6.38 | 318.18 | 12.66 | 14.10x | pass |
| go | gpt-5 | par | 378.25 | 3.89 | 379.82 | 7.32 | 11.89x | pass |
| java | baseline | seq | 1266.43 | 9.41 | 1264.78 | 17.88 | 1.00x | pass |
| java | claude-sonnet-4-5 | par | 138.29 | 4.62 | 135.56 | 7.88 | 9.16x | pass |
| java | gemini-2-5-pro | par | 365.66 | 11.38 | 361.53 | 18.87 | 3.46x | pass |
| java | gpt-5 | par | 148.82 | 10.34 | 144.89 | 19.84 | 8.51x | pass |
| python | baseline | seq | 100978.75 | 117.12 | 100920.62 | 219.38 | 1.00x | pass |
| python | gemini-2-5-pro | par | 14704.68 | 77.70 | 14711.01 | 127.99 | 6.87x | pass |
| python | gpt-5 | par | 34395.30 | 95.35 | 34367.19 | 150.66 | 2.94x | pass |
| rust | baseline | seq | 1662.42 | 14.38 | 1665.32 | 21.80 | 1.00x | pass |
| rust | claude-sonnet-4-5 | par | 242.97 | 7.38 | 245.55 | 13.15 | 6.84x | pass |
| rust | gemini-2-5-pro | par | 1456.11 | 17.93 | 1459.42 | 34.42 | 1.14x | pass |
| rust | gpt-5 | par | 217.17 | 4.61 | 217.55 | 6.80 | 7.65x | pass |

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
| cpp | baseline | seq | 1196.34 | 1.44 | 1196.81 | 2.67 | 1.00x | pass |
| cpp | claude-sonnet-4-5 | par | 1084.36 | 1.73 | 1083.53 | 3.10 | 1.10x | pass |
| cpp | gemini-2-5-pro | par | 711.16 | 5.28 | 711.19 | 10.44 | 1.68x | pass |
| cpp | gpt-5 | par | 789.92 | 9.16 | 787.36 | 15.38 | 1.51x | pass |
| csharp | baseline | seq | 1935.33 | 121.21 | 1869.81 | 207.96 | 1.00x | pass |
| csharp | claude-sonnet-4-5 | par | 3528.68 | 216.88 | 3422.14 | 286.73 | 0.55x | pass |
| csharp | gemini-2-5-pro | par | 3539.12 | 148.97 | 3491.67 | 269.93 | 0.55x | pass |
| csharp | gpt-5 | par | 1154.27 | 184.36 | 1081.30 | 356.00 | 1.68x | pass |
| go | baseline | seq | 2459.54 | 487.36 | 2348.30 | 686.20 | 1.00x | pass |
| go | claude-sonnet-4-5 | par | 660.86 | 134.85 | 652.93 | 240.67 | 3.72x | pass |
| go | gemini-2-5-pro | par | 1958.11 | 212.24 | 1964.51 | 414.62 | 1.26x | pass |
| go | gpt-5 | par | 1082.35 | 93.36 | 1082.89 | 175.02 | 2.27x | pass |
| java | baseline | seq | 1254.80 | 46.62 | 1227.04 | 85.96 | 1.00x | pass |
| java | claude-sonnet-4-5 | par | 10028.62 | 313.50 | 10036.84 | 594.75 | 0.13x | pass |
| java | gemini-2-5-pro | par | 12885.67 | 140.84 | 12850.44 | 263.35 | 0.10x | pass |
| java | gpt-5 | par | 34874.68 | 429.62 | 34997.89 | 648.53 | 0.04x | pass |
| python | baseline | seq | 134854.19 | 2336.65 | 133652.87 | 3157.76 | 1.00x | pass |
| python | claude-sonnet-4-5 | par | 457816.60 | 5148.93 | 457267.66 | 9602.37 | 0.29x | pass |
| python | gemini-2-5-pro | par | 149076.75 | 1554.81 | 149405.42 | 2779.54 | 0.90x | pass |
| python | gpt-5 | par | 43996.40 | 2524.16 | 44860.80 | 4892.66 | 3.07x | pass |
| rust | baseline | seq | 1517.89 | 23.20 | 1513.00 | 38.23 | 1.00x | pass |
| rust | claude-sonnet-4-5 | par | 933.70 | 1.70 | 933.38 | 2.67 | 1.63x | pass |
| rust | gemini-2-5-pro | par | 12059.92 | 140.08 | 12101.72 | 244.73 | 0.13x | pass |
| rust | gpt-5 | par | 59239.63 | 248.39 | 59374.73 | 438.29 | 0.03x | pass |
