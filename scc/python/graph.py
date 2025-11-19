from typing import List, Set, Tuple

class Graph:
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

Graph.reduce_edges