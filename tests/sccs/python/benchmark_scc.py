import argparse
import json
import os
import pathlib
import random
import sys
from typing import Any

# Add project root to sys.path so `from tests import bench_utils` resolves
# when this script is run directly from any working directory.
# parents: [0]=tests/sccs/python  [1]=tests/sccs  [2]=tests  [3]=project root
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3]))

from tests import bench_utils
from graph_parallel import Graph as GraphParallel
from graph import Graph as GraphSeq


IMPL = os.getenv("IMPL", "seq").lower()
Graph = GraphParallel if IMPL == "par" else GraphSeq


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

    reps, iters = 5, 20
    bm = bench_utils.run_benchmark(
        lambda: graph.reduce_edges(),
        reps=reps, iters=iters, warmup=1, disable_gc=True,
    )

    print(bench_utils.format_result(f"SCC reduce_edges | graph_size={graph_size}", bm))

    result = {
        "algo": "sccs",
        "lang": "python",
        "impl": IMPL,
        "elapsed_ms": bm["elapsed_ms"],
        "median": bm["median"],
        "iqr": bm["iqr"],
        "reps": bm["iterations"],
        "iters_per_rep": iters,
    }

    with open(args.out, "w") as f:
        json.dump(result, f, indent=2)


if __name__ == "__main__":
    main()
