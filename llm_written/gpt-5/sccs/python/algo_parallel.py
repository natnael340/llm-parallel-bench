from typing import List, Set, Tuple, Iterable
import os
from concurrent.futures import ProcessPoolExecutor
import multiprocessing as mp

# Baseline Graph implementation with Tarjan SCC and edge reduction.
# We will add a deterministic parallel reducer for SCC edge minimization.

class Graph:
    def __init__(self, v: int):
        self.V: int = v
        self.adj: List[List[int]] = [[] for _ in range(v)]
        self.rev_adj: List[List[int]] = [[] for _ in range(v)]

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
        essential_edges.extend(sorted(forward_tree))
        essential_edges.extend(sorted(reverse_tree))

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
        # Deterministic ordering of SCCs for reproducible results
        SCCs_sorted = sorted((sorted(s) for s in SCCs), key=lambda s: (len(s), s))

        reduced_edges: List[Tuple[int, int]] = []
        for scc in SCCs_sorted:
            min_edges = self.minimize_edges_in_scc(scc)
            reduced_edges.extend(min_edges)

        return reduced_edges

    def _minimize_edges_in_scc_static(self, scc: List[int]) -> List[Tuple[int, int]]:
        # helper to allow staticmethod-like picklable call; uses instance data by closure
        return self.minimize_edges_in_scc(scc)

    def reduce_edges_parallel(self, max_workers: int | None = None, small_threshold: int = 3) -> List[Tuple[int, int]]:
        """
        Parallel version of reduce_edges:
        - Computes SCCs sequentially (Tarjan is stack/time dependent)
        - Sorts SCCs deterministically
        - Splits SCCs across a bounded process pool
        - Merges partial results in the same SCC order
        Deterministic for a fixed graph and worker count.
        """
        SCCs = self.find_sccs()
        SCCs_sorted = sorted((sorted(s) for s in SCCs), key=lambda s: (len(s), s))

        n = len(SCCs_sorted)
        if n == 0:
            return []
        if n <= small_threshold:
            # tiny input: keep sequential to avoid overhead
            return self.reduce_edges()

        if max_workers is None:
            try:
                cpu = os.cpu_count() or 1
            except Exception:
                cpu = 1
            max_workers = max(1, cpu)

        # Prepare serializable payload: adjacency lists and reverse as plain lists
        adj = self.adj
        rev_adj = self.rev_adj

        # We cannot directly pickle bound methods with large state easily.
        # Define a top-level worker function below and pass necessary data.
        tasks = [(scc, adj, rev_adj) for scc in SCCs_sorted]

        results: List[List[Tuple[int,int]]] = []
        # Fixed chunksize=1 to preserve submission order mapping to result order
        with ProcessPoolExecutor(max_workers=max_workers, mp_context=mp.get_context("fork" if os.name != "nt" else "spawn")) as ex:
            for res in ex.map(_worker_minimize_edges_in_scc, tasks, chunksize=1):
                results.append(res)

        # Deterministic merge in SCC order
        reduced_edges: List[Tuple[int, int]] = []
        for part in results:
            reduced_edges.extend(part)
        return reduced_edges


def _worker_minimize_edges_in_scc(args: Tuple[List[int], List[List[int]], List[List[int]]]) -> List[Tuple[int,int]]:
    scc, adj, rev_adj = args
    nodes: Set[int] = set(scc)

    def build(start: int, graph: List[List[int]], nodes: Set[int]) -> Set[Tuple[int,int]]:
        spanning_tree: Set[Tuple[int,int]] = set()
        visited: Set[int] = set([start])
        stack: List[int] = [start]
        while stack:
            node = stack.pop()
            for neighbor in graph[node]:
                if neighbor in nodes and neighbor not in visited:
                    spanning_tree.add((node, neighbor))
                    visited.add(neighbor)
                    stack.append(neighbor)
        return spanning_tree

    forward_tree = build(scc[0], adj, nodes)
    reverse_tree = build(scc[0], rev_adj, nodes)
    essential_edges: List[Tuple[int,int]] = []
    essential_edges.extend(sorted(forward_tree))
    essential_edges.extend(sorted(reverse_tree))
    return essential_edges


if __name__ == "__main__":
    # Simple manual sanity run
    g = Graph(5)
    edges = [(0,1),(1,2),(2,0),(1,3),(3,4),(4,3)]
    for u,v in edges:
        g.add_edge(u,v)
    seq = g.reduce_edges()
    par = g.reduce_edges_parallel()
    print("seq edges:", len(seq))
    print("par edges:", len(par))
    print("equal:", seq == par)
