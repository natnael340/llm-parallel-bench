from typing import List, Set, Tuple
from concurrent.futures import ProcessPoolExecutor
import os

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
        print(f"Found {len(SCCs)} SCC(s).")

        # Sequential fallback for small graphs
        if len(SCCs) < 4:
            reduced_edges: List[Tuple[int, int]] = []
            for scc in SCCs:
                min_edges = self.minimize_edges_in_scc(scc)
                reduced_edges.extend(min_edges)
            print(f"Reduced SCC edges: {len(reduced_edges)}")
            return reduced_edges

        # Parallel processing for larger graphs
        num_workers = min(os.cpu_count() or 1, len(SCCs))
        reduced_edges: List[Tuple[int, int]] = []
        
        with ProcessPoolExecutor(max_workers=num_workers) as executor:
            # Map each SCC to a worker, preserving order with list()
            results = list(executor.map(_minimize_edges_worker, 
                                       [(scc, self.adj, self.rev_adj) for scc in SCCs]))
        
        # Combine results in fixed order (same as SCC order)
        for edges in results:
            reduced_edges.extend(edges)

        print(f"Reduced SCC edges: {len(reduced_edges)}")
        return reduced_edges


# Top-level function for ProcessPoolExecutor (must be picklable)
def _minimize_edges_worker(args: Tuple[List[int], List[List[int]], List[List[int]]]) -> List[Tuple[int, int]]:
    """Worker function to minimize edges for a single SCC."""
    scc, adj, rev_adj = args
    nodes: Set[int] = set(scc)
    essential_edges: List[Tuple[int, int]] = []

    # Forward spanning tree
    forward_tree = _build_spanning_tree(scc[0], adj, nodes)
    # Reverse spanning tree
    reverse_tree = _build_spanning_tree(scc[0], rev_adj, nodes)
    
    essential_edges.extend(forward_tree)
    essential_edges.extend(reverse_tree)
    
    return essential_edges


def _build_spanning_tree(
    start: int, graph: List[List[int]], nodes: Set[int]
) -> Set[Tuple[int, int]]:
    """Build spanning tree from start node within given node set."""
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
