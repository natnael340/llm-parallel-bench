With parallelization go impoved over 3 times better speed with more Gflops

here are the result, but the llm is persistant in using a short cut for small inputs

gemm_test.go:531: GEMM 1000x1000: 29.480s (~0.678 GFLOPs) parallel

gemm_test.go:531: GEMM 1000x1000: 8.712s (~2.296 GFLOPs)
