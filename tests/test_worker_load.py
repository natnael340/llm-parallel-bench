import time
import os
from concurrent.futures import ProcessPoolExecutor

def noop(x):
    pass

if __name__ == "__main__":
    t0 = time.perf_counter()
    N = 100_000

    for i in range(N):
        noop(i)
    t1 = time.perf_counter()
    print(f"Sequential noop: {(t1 - t0)*1000:.1f} ms")

    t2 = time.perf_counter()
    cpu_count = os.cpu_count()
    with ProcessPoolExecutor(max_workers=cpu_count) as ex:
        list(ex.map(noop, range(N), chunksize=N//cpu_count))
    t3 = time.perf_counter()
    print(f"Parallel noop: {(t3 - t2)*1000:.1f} ms for {cpu_count} workers")

