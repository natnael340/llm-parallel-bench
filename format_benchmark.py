from typing import List, Set


BENCHMARK_DATA = """
BenchmarkGraph-16    	      12	  98023509 ns/op
BenchmarkGraph-16    	      12	  97169388 ns/op
BenchmarkGraph-16    	      12	  98466460 ns/op
BenchmarkGraph-16    	      12	  98484918 ns/op
BenchmarkGraph-16    	      12	  95327256 ns/op
BenchmarkGraph-16    	      12	  94904708 ns/op
BenchmarkGraph-16    	      10	 101302074 ns/op
BenchmarkGraph-16    	      12	 100589757 ns/op
BenchmarkGraph-16    	      12	 102556907 ns/op
BenchmarkGraph-16    	      12	  99811048 ns/op
BenchmarkGraph-16    	      12	  96206956 ns/op
BenchmarkGraph-16    	      12	  95984670 ns/op
BenchmarkGraph-16    	      12	  94875487 ns/op
BenchmarkGraph-16    	      12	  92030174 ns/op
BenchmarkGraph-16    	      13	  99256628 ns/op
BenchmarkGraph-16    	      12	  93457550 ns/op
BenchmarkGraph-16    	      12	  95007019 ns/op
BenchmarkGraph-16    	      12	  93805992 ns/op
BenchmarkGraph-16    	      12	  94883342 ns/op
BenchmarkGraph-16    	      10	 100461347 ns/op
BenchmarkGraph-16    	      12	  95479546 ns/op
BenchmarkGraph-16    	      12	  98179987 ns/op
BenchmarkGraph-16    	      12	  98667186 ns/op
BenchmarkGraph-16    	      12	  94109784 ns/op
BenchmarkGraph-16    	      12	  96641096 ns/op
BenchmarkGraph-16    	      12	  94822848 ns/op
BenchmarkGraph-16    	      12	  95682808 ns/op
BenchmarkGraph-16    	      12	  93990151 ns/op
BenchmarkGraph-16    	      12	  96037135 ns/op
BenchmarkGraph-16    	      12	  97206554 ns/op
BenchmarkGraph-16    	      12	  98368496 ns/op
BenchmarkGraph-16    	      12	  96900915 ns/op
BenchmarkGraph-16    	      12	  95300908 ns/op
BenchmarkGraph-16    	      12	  95668350 ns/op
BenchmarkGraph-16    	      12	  97575780 ns/op
BenchmarkGraph-16    	      12	  96468920 ns/op
BenchmarkGraph-16    	      12	  95876073 ns/op
BenchmarkGraph-16    	      12	  96121251 ns/op
BenchmarkGraph-16    	      12	 100626939 ns/op
BenchmarkGraph-16    	      12	  97934141 ns/op
BenchmarkGraph-16    	      12	  98554674 ns/op
BenchmarkGraph-16    	      12	  98910956 ns/op
BenchmarkGraph-16    	      12	  94050422 ns/op
BenchmarkGraph-16    	      12	  97178979 ns/op
BenchmarkGraph-16    	      12	  95968848 ns/op
BenchmarkGraph-16    	      12	  95780729 ns/op
BenchmarkGraph-16    	      12	 101454379 ns/op
BenchmarkGraph-16    	      12	  94321155 ns/op
BenchmarkGraph-16    	      12	  95581843 ns/op
BenchmarkGraph-16    	      12	  94508296 ns/op
BenchmarkGraph-16    	      12	  92467085 ns/op
BenchmarkGraph-16    	      12	  95391467 ns/op
BenchmarkGraph-16    	      12	  95074113 ns/op
BenchmarkGraph-16    	      12	  93306478 ns/op
BenchmarkGraph-16    	      12	  93429472 ns/op
BenchmarkGraph-16    	      13	  95988277 ns/op
BenchmarkGraph-16    	      12	  94581543 ns/op
BenchmarkGraph-16    	      12	  97253917 ns/op
BenchmarkGraph-16    	      13	  98158200 ns/op
BenchmarkGraph-16    	      12	  96405852 ns/op
BenchmarkGraph-16    	      12	  93810967 ns/op
BenchmarkGraph-16    	      12	  95340042 ns/op
BenchmarkGraph-16    	      12	  93803400 ns/op
BenchmarkGraph-16    	      12	  97660247 ns/op
BenchmarkGraph-16    	      13	  93379279 ns/op
BenchmarkGraph-16    	      12	  94283304 ns/op
BenchmarkGraph-16    	      12	  94850308 ns/op
BenchmarkGraph-16    	      12	  93194060 ns/op
BenchmarkGraph-16    	      12	  93650608 ns/op
BenchmarkGraph-16    	      13	  92383569 ns/op
BenchmarkGraph-16    	      13	  93556044 ns/op
BenchmarkGraph-16    	      13	  95798380 ns/op
BenchmarkGraph-16    	      12	  92926568 ns/op
BenchmarkGraph-16    	      12	  96656716 ns/op
BenchmarkGraph-16    	      12	  95561476 ns/op
BenchmarkGraph-16    	      12	  97718709 ns/op
BenchmarkGraph-16    	      12	  94711625 ns/op
BenchmarkGraph-16    	      13	  94662821 ns/op
BenchmarkGraph-16    	      12	 107693337 ns/op
BenchmarkGraph-16    	      12	  92408808 ns/op
BenchmarkGraph-16    	      13	  98074924 ns/op
BenchmarkGraph-16    	      12	  95392482 ns/op
BenchmarkGraph-16    	      12	  98849244 ns/op
BenchmarkGraph-16    	      12	  97237051 ns/op
BenchmarkGraph-16    	      13	  96336021 ns/op
BenchmarkGraph-16    	      12	  92656103 ns/op
BenchmarkGraph-16    	      12	  98632324 ns/op
BenchmarkGraph-16    	      12	  95873301 ns/op
BenchmarkGraph-16    	      12	  93705443 ns/op
BenchmarkGraph-16    	      12	  94989114 ns/op
BenchmarkGraph-16    	      12	  95981661 ns/op
BenchmarkGraph-16    	      12	  95388842 ns/op
BenchmarkGraph-16    	      12	  99078407 ns/op
BenchmarkGraph-16    	      12	  98677840 ns/op
BenchmarkGraph-16    	      12	  97465663 ns/op
BenchmarkGraph-16    	      12	  99644850 ns/op
BenchmarkGraph-16    	      12	  98715446 ns/op
BenchmarkGraph-16    	      12	  97309844 ns/op
BenchmarkGraph-16    	      12	  97701257 ns/op
BenchmarkGraph-16    	      10	 101272138 ns/op
"""

def format_benchmark():
    values = []
    sum_ns = 0.0
    for line in BENCHMARK_DATA.strip().split("\n"):
        parts = line.split()
        if len(parts) == 4:
            ns_per_op = int(parts[2])
            values.append(ns_per_op)
    
    # calculate average and stddev from values array
    if not values:
        print("No data")
        return

    # convert ns values to ms
    values_ms = [x / 1_000_000.0 for x in values]
    avg_ms = sum(values_ms) / len(values_ms)
    sum_sq_diff = sum((x - avg_ms) ** 2 for x in values_ms)
    stddev_ms = (sum_sq_diff / len(values_ms)) ** 0.5

    print(f"Average Time per Operation: {avg_ms:.4f} ms")
    print(f"Standard Deviation: {stddev_ms:.4f} ms")
        


if __name__ == "__main__":
    format_benchmark()