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

Average GEMM runtime : 10038.59 ms/run
Standard deviation : ±166.53 ms
Estimated throughput : 0.214 GFLOPs

## SEQUENTIAL: Go

### Results

Average GEMM runtime : 1480.04 ms/run
Standard deviation : ±12.44 ms
Estimated throughput : 1.451 GFLOPs

## PARALLEL: Go

### Results

Average GEMM runtime : 202.26 ms/run
Standard deviation : ±3.66 ms
Estimated throughput : 10.618 GFLOPs

## SEQUENTIAL: C++

### Results

Average GEMM runtime : 558.61 ms/run
Standard deviation : ±4.08 ms
Estimated throughput : 3.844 GFLOPs

## PARALLEL: C++

### Results

Average GEMM runtime : 110.30 ms/run
Standard deviation : ±2.60 ms
Estimated throughput : 19.470 GFLOPs
