As the other one gemini is also using a shorter route swhich is nice and better
and also used the whole process to parallelize block of the code, making it faster
than open ai implementation which is good this result in in creadible and faster run

Sequential: gemm_test.go:531: GEMM 1000x1000: 11.981s (~1.669 GFLOPs)
Parallel: gemm_test.go:531: GEMM 1000x1000: 1.796s (~11.136 GFLOPs)

while perfoming the test we disabled the shorter route to make sure that algorithm written is
works for all our test cases
