tests/python/test_gemm.py .............................GEMM 1000x1000: 345.219s (~0.006 GFLOPs)

what happend is the parallel implementation improved by 4 times, from 1200 sec to 345 which is a great improvemnt
how ever the llm persisted using a naive or sequential gmm for small input

collected 30 items

tests/python/test_gemm.py .............................GEMM 1000x1000: 345.219s (~0.006 GFLOPs)
.

the llm persisted deterministic beheaviour which is a good approach
also distributed the load

but the llm is deciding to use 4 cpu at maximum, be delivered 3 times speed increase

the thing is the multiplication work is devided but beside multiplication we have packing
