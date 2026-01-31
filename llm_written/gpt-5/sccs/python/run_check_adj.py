import random
from algo_parallel import GraphSequential, GraphParallel

random.seed(42)
N=100; M=400

g = GraphSequential(N)
edges=set()
while len(edges)<M:
    u=random.randrange(N); v=random.randrange(N)
    if u==v or (u,v) in edges: continue
    edges.add((u,v))
    g.add_edge(u,v)

p = GraphParallel(N)
for u in range(N):
    for v in g.adj[u]:
        p.add_edge(u,v)

same=True
for u in range(N):
    if g.adj[u]!=p.adj[u]:
        print('adj differ at',u)
        print(g.adj[u][:10], p.adj[u][:10])
        same=False
    if g.rev_adj[u]!=p.rev_adj[u]:
        print('rev differ at',u)
        print(g.rev_adj[u][:10], p.rev_adj[u][:10])
        same=False
print('Adj match:', same)
