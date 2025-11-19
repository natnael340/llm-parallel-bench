import os
import random
import time
import hashlib
from typing import List, Tuple

from algo_parallel import Graph


def hash_edges(edges: List[Tuple[int,int]]) -> str:
    # Deterministic hash ignoring order issues since our impl is deterministic. Keep as tuple list.
    h = hashlib.sha256()
    for e in edges:
        h.update(f"{e[0]},{e[1]};".encode())
    return h.hexdigest()


def build_sample_graph() -> Graph:
    g = Graph(8)
    edges = [
        (0,1),(1,2),(2,0),  # scc A: 0-1-2
        (3,4),(4,5),(5,3),  # scc B: 3-4-5
        (2,3),              # bridge A->B
        (6,7),(7,6)         # scc C: 6-7
    ]
    for u,v in edges:
        g.add_edge(u,v)
    return g


def build_chain_sccs(n_scc: int, size: int) -> Graph:
    # Build n_scc SCCs each of 'size' in a cycle internally, chained linearly.
    V = n_scc * size
    g = Graph(V)
    for s in range(n_scc):
        base = s*size
        # make a cycle for SCC
        for i in range(size):
            g.add_edge(base + i, base + ((i+1) % size))
        if s < n_scc - 1:
            # connect to next SCC
            g.add_edge(base + size - 1, base + size)
    return g


def build_random_graph(V: int, E: int, seed: int = 0) -> Graph:
    rnd = random.Random(seed)
    g = Graph(V)
    for _ in range(E):
        u = rnd.randrange(V)
        v = rnd.randrange(V)
        g.add_edge(u,v)
    return g


def run_case(g: Graph, repeats: int = 2):
    seq = g.reduce_edges()
    par = g.reduce_edges_parallel()
    assert seq == par, "Sequential and parallel outputs differ"

    # determinism: run parallel twice
    par2 = g.reduce_edges_parallel()
    assert par == par2, "Parallel runs not deterministic"
    return seq, par


def main():
    os.makedirs('evidence', exist_ok=True)
    summary_lines = []

    # Edge cases
    g_empty = Graph(0)
    seq = g_empty.reduce_edges()
    par = g_empty.reduce_edges_parallel()
    assert seq == par == [], "Empty graph failed"
    summary_lines.append("empty: pass")

    g_single = Graph(1)
    seq = g_single.reduce_edges()
    par = g_single.reduce_edges_parallel()
    assert seq == par == [], "Single node graph failed"
    summary_lines.append("single: pass")

    # Small fixed graph
    g = build_sample_graph()
    seq, par = run_case(g)
    summary_lines.append(f"sample: pass, edges={len(seq)} hash={hash_edges(seq)}")

    # Medium graph: 20 SCCs of size 5
    g_med = build_chain_sccs(20, 5)
    seq, par = run_case(g_med)
    summary_lines.append(f"chain20x5: pass, edges={len(seq)} hash={hash_edges(seq)}")

    # Determinism check with hashes
    h1 = hash_edges(g_med.reduce_edges_parallel())
    h2 = hash_edges(g_med.reduce_edges_parallel())
    assert h1 == h2, "Hashes differ between parallel runs"
    summary_lines.append(f"determinism-hash: {h1}")

    # Performance smoke (keep recursion depth under Python limit):
    # total nodes = n_scc * size; pick <= 600 to avoid recursion issues
    g_perf = build_chain_sccs(60, 10)  # 600 nodes, ~60 SCCs
    t0 = time.time()
    seq_perf = g_perf.reduce_edges()
    t1 = time.time()
    par_perf = g_perf.reduce_edges_parallel()
    t2 = time.time()
    t_seq = t1 - t0
    t_par = t2 - t1
    speedup = t_seq / t_par if t_par > 0 else float('inf')
    summary_lines.append(f"perf: N_scc=60 t_seq={t_seq:.4f}s t_par={t_par:.4f}s speedup={speedup:.2f}x cores={os.cpu_count()}")

    with open('evidence/run_summary.txt', 'w') as f:
        f.write("\n".join(summary_lines) + "\n")

    # Also store perf details separately
    with open('evidence/perf.txt', 'w') as f:
        f.write(summary_lines[-1] + "\n")

    # Print brief summary for CI
    print("SUMMARY:")
    for line in summary_lines:
        print(line)

if __name__ == "__main__":
    main()
