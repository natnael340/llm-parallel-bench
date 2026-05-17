import argparse
import gc
import json
import os
import random
import statistics as stats
import timeit
from typing import Any, List, Set, Tuple
from graph_parallel import Graph as GraphParallel
from graph import Graph as GraphSeq


ALGO = os.getenv("ALGO", "seq").lower()
Graph = GraphParallel if ALGO == "par" else GraphSeq


def ring_scc(start: int, n: int, graph: Any) -> None:
    for i in range(start, n):
        v = (i + 1) % n
        v = v if v != 0 else start

        if (i == v):
            continue
        
        graph.add_edge(i, v) 



def build_graph(n: int, cluster_size: int, no_cluster_in_group: int, graph_class: Any) -> Any:
    graph = graph_class(n)
    random.seed(43)
    for i in range(0, n, cluster_size):
        ring_scc(i, min(i + cluster_size, n), graph)
        
        current_cluster = i // cluster_size
        if current_cluster // no_cluster_in_group == (current_cluster + 1) // no_cluster_in_group:
            
            if (i + cluster_size) < n:
                u = random.randrange(i, min(i + cluster_size, n) - 1)
                v = random.randrange(min(i + cluster_size, n), min(i + 2 * cluster_size, n) - 1)
                graph.add_edge(u, v)

    return graph


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=True, help="Output JSON file path")
    args = parser.parse_args()

    graph_size = 100_000
    cluster_size = 300
    no_cluster_in_group = 3

    graph = build_graph(graph_size, cluster_size, no_cluster_in_group, Graph)

    # warmup
    graph.reduce_edges()

    reps = 5
    iters = 20

    gc.disable()
    try:
        timings = timeit.repeat(lambda: graph.reduce_edges(), repeat=reps, number=iters)
    finally:
        gc.enable()

    per_run_ms = [(t / iters) * 1000 for t in timings]
    avg = stats.mean(per_run_ms)
    sd = stats.pstdev(per_run_ms)

    print(f"SCC reduce_edges | graph_size={graph_size} | {avg:.2f} ms/run ± {sd:.2f} (n={reps})")

    result = {
        "elapsed_ms": per_run_ms,
        "mean": avg,
        "sd": sd,
        "iterations": reps,
    }

    with open(args.out, "w") as f:
        json.dump(result, f, indent=2)


if __name__ == "__main__":
    main()