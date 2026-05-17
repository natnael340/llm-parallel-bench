tests/python/test_gemm.py .............................GEMM 1000x1000: 115.062s (~0.017 GFLOPs)

here is the result from the parallel implemnetation as we can see it is fast for 1000 by 1000 matrix multiplication
but the thing is it use all availble cpu core which is 16 of them this might lead to oversubscription
in which openai implementation avoided,

I'm wrong, there is no oversubscription, gemini did the best thing of parallelizing it to all the cores availble while openai implementation was forcing the app to be bound to specific cpu this lead to perfomance degradation

here is the result from the sequential one
tests/python/test_gemm.py .............................GEMM 1000x1000: 534.174s (~0.004 GFLOPs)

what about synchronization, here the code handles synchronization implicitly and elegantly by splitting the output matrix C into non-overlapping blocks, and ensuring that only the main process performs the final write. That’s a smart and safe design.
