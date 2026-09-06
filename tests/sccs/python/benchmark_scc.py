import argparse
import os
import pathlib
import random
import sys
from typing import Any

# Add project root to sys.path so `from tests import bench_utils` resolves
# when this script is run directly from any working directory.
# parents: [0]=tests/sccs/python  [1]=tests/sccs  [2]=tests  [3]=project root
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3]))
# Add this script's dir so the staged implementation package resolves.
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from tests import bench_utils
# The implementation under test is staged by bench/run.py (see
# bench/manifests/sccs/python.json); the adapter exposes the canonical entry.
from staging.impl_adapter import BenchGraph


# --- correctness: SCC strong-check heuristic (mirrors the Go harness) ---
# For SCC of size k>1: (k-1) <= internal edges <= 2*(k-1), and every SCC
# node appears in at least one kept internal edge.
def is_scc_strong(scc_nodes: list, edges: list) -> bool:
    node_set = set(scc_nodes)
    k = len(scc_nodes)
    if k <= 1:
        return True

    internal_edges = 0
    touched = set()
    for u, v in edges:
        if u in node_set and v in node_set:
            internal_edges += 1
            touched.add(u)
            touched.add(v)

    if internal_edges < k - 1:
        return False
    if internal_edges > 2 * (k - 1):
        return False
    if len(touched) < k:
        return False
    return True


def check_all_sccs(graph: Any) -> bool:
    edges = graph.reduce_edges()
    return all(is_scc_strong(scc, edges) for scc in graph.find_sccs())


def run_correctness_checks() -> int:
    failures = 0

    def report(name: str, ok: bool) -> int:
        print(f"{name} {'passed' if ok else 'failed'}")
        return 0 if ok else 1

    g1 = BenchGraph(3)
    g1.add_edge(0, 1); g1.add_edge(1, 2); g1.add_edge(2, 0)
    failures += report("test_scc_3cycle", check_all_sccs(g1))

    g2 = BenchGraph(2)
    g2.add_edge(0, 1); g2.add_edge(1, 0)
    failures += report("test_scc_2node_mutual", check_all_sccs(g2))

    g3 = BenchGraph(5)
    g3.add_edge(0, 1); g3.add_edge(1, 2); g3.add_edge(2, 0)
    g3.add_edge(3, 4); g3.add_edge(4, 3)
    g3.add_edge(2, 3)
    failures += report("test_scc_multiple", check_all_sccs(g3))

    g4 = BenchGraph(7)
    for u, v in [(0, 1), (1, 2), (1, 3), (1, 4), (2, 0), (2, 3),
                 (3, 5), (5, 3), (5, 4), (5, 6), (6, 4), (4, 6)]:
        g4.add_edge(u, v)
    failures += report("test_scc_7node", check_all_sccs(g4))

    return failures


# --- benchmark graph construction (shared with all languages) ---

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
    parser.add_argument("--out", default=None,
                        help="Output JSON file path (default: BENCH_OUT env)")
    args = parser.parse_args()
    if args.out:
        os.environ["BENCH_OUT"] = args.out

    failures = run_correctness_checks()
    if failures:
        print(f"{failures} correctness check(s) failed — skipping benchmark")
        sys.exit(1)

    graph_size = 100_000
    cluster_size = 300
    no_cluster_in_group = 3

    graph = build_graph(graph_size, cluster_size, no_cluster_in_group, BenchGraph)

    config = bench_utils.get_bench_config(default_reps=5, default_iters=20)
    reps, iters = config["reps"], config["iters"]
    bm = bench_utils.run_benchmark(
        lambda: graph.reduce_edges(),
        reps=reps, iters=iters, warmup=1, disable_gc=True,
    )

    print(bench_utils.format_result(f"SCC reduce_edges | graph_size={graph_size}", bm))

    bench_utils.write_result(
        bm, algo="sccs", lang="python", impl=config["impl"], iters_per_rep=iters,
        params={
            "graph_size": graph_size,
            "cluster_size": cluster_size,
            "no_cluster_in_group": no_cluster_in_group,
        },
    )


if __name__ == "__main__":
    main()
