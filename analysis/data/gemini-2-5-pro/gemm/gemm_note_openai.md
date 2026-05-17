# GEMM Performance Report

Matrix dimensions : A(1024×1024), B(1024×1024)
Operation : GEMM with β = 0 and α = 1
Measurement : timeit (5 repeats, 20 iterations per repeat)

## SEQUENTIAL: Python

### Results

Average GEMM runtime : 48052.31 ms/run
Standard deviation : ±44.28 ms
Estimated throughput : 0.045 GFLOPs

## PARALLEL: Python

### Results

Average GEMM runtime : 21625.38 ms/run
Standard deviation : ±354.10 ms
Estimated throughput : 0.099 GFLOPs

## SEQUENTIAL: Go

### Results

Average GEMM runtime : 1480.04 ms/run
Standard deviation : ±12.44 ms
Estimated throughput : 1.451 GFLOPs

## PARALLEL: Go

### Results

Average GEMM runtime : 247.27 ms/run
Standard deviation : ±4.40 ms
Estimated throughput : 8.864 GFLOPs

## SEQUENTIAL: C++

### Results

Average GEMM runtime : 558.61 ms/run
Standard deviation : ±4.08 ms
Estimated throughput : 3.844 GFLOPs

## PARALLEL: C++

### Results

Average GEMM runtime : 164.39 ms/run
Standard deviation : ±5.61 ms
Estimated throughput : 13.064 GFLOPs
