import random
import sys
from typing import List

# Import baseline and parallel modules
import llm_written.python.bfs_baseline as bl
import llm_written.python.bfs_parallel as pl


def make_graph(edges):
    g1 = bl.Graph()
    g2 = pl.Graph()
    for u, v in edges:
        g1.add_edge(u, v)
        g2.add_edge(u, v)
    return g1, g2


def run_single_case(edges, start):
    g1, g2 = make_graph(edges)
    r1 = bl.bfs(g1, start)
    r2 = pl.bfs(g2, start)
    return r1, r2


def test_fixed_cases():
    # Empty graph
    r1, r2 = run_single_case([], 0)
    assert r2 == r1

    # Single node self-loop
    r1, r2 = run_single_case([(1, 1)], 1)
    assert r2 == r1

    # Line graph
    edges = [(i, i+1) for i in range(10)]
    r1, r2 = run_single_case(edges, 0)
    assert r2 == r1

    # Star graph
    edges = [(0, i) for i in range(1, 50)]
    r1, r2 = run_single_case(edges, 0)
    assert r2 == r1

    # Disconnected component start not present
    edges = [(1,2), (2,3)]
    r1, r2 = run_single_case(edges, 5)
    assert r2 == r1


def test_random_cases():
    random.seed(12345)
    for n in [1, 2, 5, 10, 50, 100]:
        for p_times_100 in [0, 5, 10, 20, 50, 80, 100]:
            p = p_times_100 / 100.0
            for _ in range(10):
                edges = []
                for i in range(n):
                    for j in range(i+1, n):
                        if random.random() < p:
                            edges.append((i, j))
                start = random.randrange(0, n)
                r1, r2 = run_single_case(edges, start)
                assert r2 == r1


def test_determinism_repeated_runs():
    # Build one medium graph and compare multiple runs of parallel bfs
    edges = []
    n = 200
    random.seed(42)
    for i in range(n):
        # sparse-ish random graph
        for j in range(i+1, min(n, i+10)):
            if random.random() < 0.3:
                edges.append((i, j))
    g = pl.Graph()
    for u, v in edges:
        g.add_edge(u, v)
    r_first = pl.bfs(g, 0)
    for _ in range(5):
        r_again = pl.bfs(g, 0)
        assert r_again == r_first


if __name__ == "__main__":
    # Simple runner to avoid external test frameworks
    failures = 0
    try:
        test_fixed_cases()
        print("Fixed cases: OK")
    except AssertionError:
        failures += 1
        print("Fixed cases: FAIL")

    try:
        test_random_cases()
        print("Random cases: OK")
    except AssertionError:
        failures += 1
        print("Random cases: FAIL")

    try:
        test_determinism_repeated_runs()
        print("Determinism: OK")
    except AssertionError:
        failures += 1
        print("Determinism: FAIL")

    if failures == 0:
        print("ALL TESTS PASSED")
    else:
        print(f"TESTS FAILED: {failures} failing groups")
        sys.exit(1)
