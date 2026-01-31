import random
from typing import List, Tuple
from algo_parallel import GraphSequential, GraphParallel, canonicalize_edges


def build_graph(n: int, m: int, seed: int = 0) -> GraphSequential:
    random.seed(seed)
    g = GraphSequential(n)
    edges = set()
    while len(edges) < m:
        u = random.randrange(0, n)
        v = random.randrange(0, n)
        if u == v:
            continue
        e = (u, v)
        if e in edges:
            continue
        edges.add(e)
        g.add_edge(u, v)
    return g

n=100; m=400; seed=42

g = build_graph(n, m, seed)
seq_sccs = g.find_sccs()

p = GraphParallel(n)
for u in range(n):
    for v in g.adj[u]:
        p.add_edge(u, v)
par_sccs = p.find_sccs()

# Build mapping of SCCs by sorted node tuple
seq_map = {tuple(sorted(s)): s for s in seq_sccs}
par_map = {tuple(sorted(s)): s for s in par_sccs}

for key in seq_map:
    s1 = seq_map[key]
    s2 = par_map[key]
    e_seq = set(g.minimize_edges_in_scc(s1))
    e_par = set(p._minimize_edges_in_scc_seq(s2))
    if e_seq != e_par:
        print('Mismatch in SCC', key)
        print('Start seq', s1[0], 'Start par', s2[0])
        print('Only in seq:', sorted(list(e_seq - e_par))[:20])
        print('Only in par:', sorted(list(e_par - e_seq))[:20])
        break
else:
    print('All SCC edge sets match')
