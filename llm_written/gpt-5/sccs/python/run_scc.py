import argparse
import json
import os
import random
import time
from typing import List, Tuple

from algo_parallel import GraphSequential, GraphParallel, canonicalize_edges


def build_edges(n: int, m: int, seed: int = 0) -> List[Tuple[int,int]]:
    random.seed(seed)
    edges = []
    seen = set()
    while len(edges) < m:
        u = random.randrange(0, n)
        v = random.randrange(0, n)
        if u == v:
            continue
        e = (u, v)
        if e in seen:
            continue
        seen.add(e)
        edges.append(e)
    return edges


def run_once(n: int, m: int, seed: int, verbose: bool = False) -> Tuple[List[List[int]], List[Tuple[int,int]]]:
    edges = build_edges(n, m, seed)

    g = GraphSequential(n)
    for (u, v) in edges:
        g.add_edge(u, v)
    seq_sccs = g.find_sccs()
    seq_edges = canonicalize_edges(g.reduce_edges())

    gp = GraphParallel(n, verbose=verbose)
    for (u, v) in edges:
        gp.add_edge(u, v)

    par_sccs = gp.find_sccs()  # should match seq structurally and order
    par_edges = gp.reduce_edges()

    return (sorted([sorted(x) for x in seq_sccs]), seq_edges), (sorted([sorted(x) for x in par_sccs]), par_edges)


def determinism_check(n: int, m: int, seed: int) -> Tuple[List[Tuple[int,int]], List[Tuple[int,int]]]:
    edges = build_edges(n, m, seed)
    gp1 = GraphParallel(n)
    gp2 = GraphParallel(n)
    for (u, v) in edges:
        gp1.add_edge(u, v)
        gp2.add_edge(u, v)
    e1 = gp1.reduce_edges()
    e2 = gp2.reduce_edges()
    return e1, e2


def perf_run(n: int, m: int, seed: int, repeats: int = 1):
    edges = build_edges(n, m, seed)
    g = GraphSequential(n)
    for (u, v) in edges:
        g.add_edge(u, v)
    t0 = time.time()
    seq_edges = canonicalize_edges(g.reduce_edges())
    t1 = time.time()

    gp = GraphParallel(n)
    for (u, v) in edges:
        gp.add_edge(u, v)
    t2 = time.time()
    par_edges = gp.reduce_edges()
    t3 = time.time()

    return {
        'n': n,
        'm': m,
        't_seq': t1 - t0,
        't_par': t3 - t2,
        'speedup': (t1 - t0) / (t3 - t2 + 1e-12),
        'seq_edges_count': len(seq_edges),
        'par_edges_count': len(par_edges),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--mode', choices=['test', 'perf'], default='test')
    parser.add_argument('--seed', type=int, default=42)
    args = parser.parse_args()

    summary_lines = []

    # Edge cases and small/medium/large
    cases = [
        (0, 0),
        (1, 0),
        (5, 0),
        (5, 4),
        (10, 20),
        (100, 400),
    ]

    # Correctness and determinism tests
    all_pass = True
    for (n, m) in cases:
        try:
            (seq_sccs, seq_edges), (par_sccs, par_edges) = run_once(n, m, args.seed)
            ok1 = (seq_sccs == par_sccs)
            ok2 = (seq_edges == par_edges)
            # Determinism: repeat parallel 3 times
            hashes = []
            import hashlib
            for r in range(3):
                e1, e2 = determinism_check(n, m, args.seed + r)
                h1 = hashlib.sha256(str(e1).encode()).hexdigest()
                h2 = hashlib.sha256(str(e2).encode()).hexdigest()
                hashes.append((h1, h2))
            det_ok = all(h1 == h2 for (h1, h2) in hashes)
            line = f"N={n} M={m} SCCs_ok={ok1} Edges_ok={ok2} Determinism_ok={det_ok}"
            summary_lines.append(line)
            if not (ok1 and ok2 and det_ok):
                all_pass = False
        except Exception as e:
            summary_lines.append(f"N={n} M={m} ERROR: {e}")
            all_pass = False

    with open('run_summary.txt', 'w') as f:
        f.write('\n'.join(summary_lines) + '\n')

    print('\n'.join(summary_lines))

    if args.mode == 'perf':
        perf_cases = [
            (2000, 6000),
            (5000, 20000),
        ]
        perf_lines = []
        for (n, m) in perf_cases:
            stats = perf_run(n, m, args.seed)
            perf_lines.append(json.dumps(stats))
        with open('perf.txt', 'w') as f:
            f.write('\n'.join(perf_lines) + '\n')
        print('Perf written to perf.txt')

    exit(0 if all_pass else 1)


if __name__ == '__main__':
    main()
