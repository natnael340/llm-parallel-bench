from __future__ import annotations
from typing import List, Set, Tuple, Iterable, Optional
import os
from concurrent.futures import ProcessPoolExecutor

# ---------------------- Baseline (sequential, as provided) ----------------------
class GraphSequential:
    def __init__(self, v: int, verbose: bool = False) -> None:
        self.V: int = v
        self.adj: List[List[int]] = [[] for _ in range(v)]
        self.rev_adj: List[List[int]] = [[] for _ in range(v)]
        self.verbose = verbose

    def add_edge(self, v: int, w: int) -> None:
        self.adj[v].append(w)
        self.rev_adj[w].append(v)
    
    def tarjan_dfs(self,
        u: int,
        disc: List[int],
        low: List[int],
        stack: List[int],
        in_stack: List[bool],
        time_ref: List[int],
        scc_list: List[List[int]],
    ) -> None:
        time_ref[0] += 1
        disc[u] = low[u] = time_ref[0]
        stack.append(u)
        in_stack[u] = True                

        for v in self.adj[u]:
            if disc[v] == -1:
                self.tarjan_dfs(v, disc, low, stack, in_stack, time_ref, scc_list)
                low[u] = min(low[u], low[v])
            elif in_stack[v]:
                low[u] = min(low[u], disc[v])
        
        if low[u] == disc[u]:
            scc: List[int] = []
            while True:
                w = stack.pop()
                in_stack[w] = False
                scc.append(w)
                if w == u:
                    break
            scc_list.append(scc)

    
    def find_sccs(self) -> List[List[int]]:
        disc = [-1] * self.V
        low = [-1] * self.V
        in_stack = [False] * self.V
        stack: List[int] = []
        scc_list: List[List[int]] = []
        time_ref = [0]  # acts like 'ref int time'

        for i in range(self.V):
            if disc[i] == -1:
                self.tarjan_dfs(i, disc, low, stack, in_stack, time_ref, scc_list)

        return scc_list

    # Minimal SCC Edge Reduction (O(V + E))
    def minimize_edges_in_scc(self, scc: List[int]) -> List[Tuple[int, int]]:
        nodes: Set[int] = set(scc)
        essential_edges: List[Tuple[int, int]] = []

        # Step 1: forward spanning tree using DFS
        forward_tree = self.build_spanning_tree(scc[0], self.adj, nodes)

        # Step 2: reverse spanning tree using DFS on reversed graph
        reverse_tree = self.build_spanning_tree(scc[0], self.rev_adj, nodes)

        # Step 3: merge both trees (each edge appears at most twice)
        essential_edges.extend(forward_tree)
        essential_edges.extend(reverse_tree)

        return essential_edges

    def build_spanning_tree(
        self, start: int, graph: List[List[int]], nodes: Set[int]
    ) -> Set[Tuple[int, int]]:
        spanning_tree: Set[Tuple[int, int]] = set()
        visited: Set[int] = set()
        stack: List[int] = [start]
        visited.add(start)
        
        while stack:
            node = stack.pop()
            for neighbor in graph[node]:
                if neighbor in nodes and neighbor not in visited:
                    spanning_tree.add((node, neighbor))
                    visited.add(neighbor)
                    stack.append(neighbor)
        
        return spanning_tree

    def reduce_edges(self) -> List[Tuple[int, int]]:
        SCCs = self.find_sccs()
        if self.verbose:
            print(f"Found {len(SCCs)} SCC(s).")

        reduced_edges: List[Tuple[int, int]] = []
        for scc in SCCs:
            min_edges = self.minimize_edges_in_scc(scc)
            reduced_edges.extend(min_edges)

        if self.verbose:
            print(f"Reduced SCC edges: {len(reduced_edges)}")
        return reduced_edges


# ---------------------- Parallel, deterministic implementation ----------------------
# Globals used by worker processes (set via initializer)
_G_ADJ: Optional[List[List[int]]] = None
_G_REV: Optional[List[List[int]]] = None
_G_V: Optional[int] = None

def _init_worker_graph(adj: List[List[int]], rev: List[List[int]]) -> None:
    global _G_ADJ, _G_REV, _G_V
    _G_ADJ = adj
    _G_REV = rev
    _G_V = len(adj)


def _worker_minimize_scc(scc: List[int]) -> List[Tuple[int, int]]:
    # Runs inside a worker process; uses globals for adjacency, calls baseline to guarantee exact parity
    if _G_ADJ is None or _G_REV is None or _G_V is None:
        raise RuntimeError("Worker graph not initialized")
    g = GraphSequential(_G_V)
    g.adj = _G_ADJ
    g.rev_adj = _G_REV
    return g.minimize_edges_in_scc(scc)


def canonicalize_edges(edges: Iterable[Tuple[int, int]]) -> List[Tuple[int, int]]:
    # Sort and deduplicate deterministically
    seen = set()
    out: List[Tuple[int, int]] = []
    for e in edges:
        if e not in seen:
            seen.add(e)
            out.append(e)
    out.sort()
    return out


class GraphParallel:
    def __init__(self, v: int, verbose: bool = False, workers: Optional[int] = None, small_threshold: int = 2) -> None:
        self.V: int = v
        self.adj: List[List[int]] = [[] for _ in range(v)]
        self.rev_adj: List[List[int]] = [[] for _ in range(v)]
        self.verbose = verbose
        self.workers = workers if workers and workers > 0 else (os.cpu_count() or 1)
        # If number of SCCs <= small_threshold, run sequential per-SCC to avoid overhead
        self.small_threshold = max(0, small_threshold)

    def add_edge(self, v: int, w: int) -> None:
        self.adj[v].append(w)
        self.rev_adj[w].append(v)

    def find_sccs(self) -> List[List[int]]:
        return self._find_sccs_via_baseline()

    # We delegate SCC computation to the sequential baseline to ensure identical SCC ordering
    def _find_sccs_via_baseline(self) -> List[List[int]]:
        g = GraphSequential(self.V)
        g.adj = [lst[:] for lst in self.adj]
        g.rev_adj = [lst[:] for lst in self.rev_adj]
        return g.find_sccs()

    def _minimize_edges_in_scc_seq(self, scc: List[int]) -> List[Tuple[int, int]]:
        # Use baseline implementation to guarantee identical choice of edges
        g = GraphSequential(self.V)
        g.adj = self.adj
        g.rev_adj = self.rev_adj
        return g.minimize_edges_in_scc(scc)

    def reduce_edges(self) -> List[Tuple[int, int]]:
        # Compute SCCs using the baseline path to match scc[0] choice exactly
        SCCs = self._find_sccs_via_baseline()
        if self.verbose:
            print(f"Found {len(SCCs)} SCC(s). Using up to {self.workers} workers.")
        if len(SCCs) <= self.small_threshold or self.workers == 1:
            combined: List[Tuple[int, int]] = []
            for scc in SCCs:
                combined.extend(self._minimize_edges_in_scc_seq(scc))
            return canonicalize_edges(combined)
        # Parallel per-SCC phase with fixed order combine
        with ProcessPoolExecutor(max_workers=self.workers, initializer=_init_worker_graph, initargs=(self.adj, self.rev_adj)) as ex:
            # map preserves input order; chunksize=1 to avoid grouping across SCCs
            results = list(ex.map(_worker_minimize_scc, SCCs, chunksize=1))
        combined: List[Tuple[int, int]] = []
        for part in results:  # fixed combine order
            combined.extend(part)
        return canonicalize_edges(combined)
