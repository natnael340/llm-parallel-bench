# Temporary debug runner to locate mismatch cause
import random
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
seq_edges = canonicalize_edges(g.reduce_edges())

# Parallel
p = GraphParallel(n)
for u in range(n):
    for v in g.adj[u]:
        p.add_edge(u, v)
par_sccs = p.find_sccs()
par_edges = p.reduce_edges()

print('SCC match:', sorted([sorted(x) for x in seq_sccs]) == sorted([sorted(x) for x in par_sccs]))
print('Seq edges:', len(seq_edges), 'Par edges:', len(par_edges))

sset = set(seq_edges)
pset = set(par_edges)
print('Only in seq:', len(sset-pset), 'Only in par:', len(pset-sset))
print('Sample only in seq:', list(sorted(sset-pset))[:20])
print('Sample only in par:', list(sorted(pset-sset))[:20])
