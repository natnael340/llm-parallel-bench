from typing import List, Set, Tuple

class Graph:
    def __init__(self, v: int):
        self.V: int = v
        self.adj: List[List[int]] = [[] for _ in range(v)]
        self.rev_adj: List[List[int]] = [[] for _ in range(v)]

    def add_edge(self, v: int, w: int) -> None:
        self.adj[v].append(w)
        self.rev_adj[w].append(v)

    def tarjan_dfs_iterative(
        self,
        start_node: int,
        disc: List[int],
        low: List[int],
        stack: List[int],
        in_stack: List[bool],
        time_ref: List[int],
        scc_list: List[List[int]],
    ):
        """Iterative version of Tarjan's DFS to avoid recursion depth errors."""
        call_stack = [(start_node, 0)]  # (node, neighbor_index)

        while call_stack:
            u, neighbor_idx = call_stack[-1]

            if neighbor_idx == 0:
                # First time visiting u
                time_ref[0] += 1
                disc[u] = low[u] = time_ref[0]
                stack.append(u)
                in_stack[u] = True

            if neighbor_idx < len(self.adj[u]):
                # Process next neighbor
                v = self.adj[u][neighbor_idx]
                call_stack[-1] = (u, neighbor_idx + 1) # Update parent state

                if disc[v] == -1:
                    call_stack.append((v, 0)) # Recurse on child
                elif in_stack[v]:
                    low[u] = min(low[u], disc[v])
            else:
                # Finished with all of u's neighbors, process u
                call_stack.pop()
                if low[u] == disc[u]:
                    scc: List[int] = []
                    while True:
                        w = stack.pop()
                        in_stack[w] = False
                        scc.append(w)
                        if w == u:
                            break
                    scc_list.append(scc)
                
                # After processing, update parent's low-link value
                if call_stack:
                    parent, _ = call_stack[-1]
                    low[parent] = min(low[parent], low[u])

    def find_sccs(self) -> List[List[int]]:
        disc = [-1] * self.V
        low = [-1] * self.V
        in_stack = [False] * self.V
        stack: List[int] = []
        scc_list: List[List[int]] = []
        time_ref = [0]

        for i in range(self.V):
            if disc[i] == -1:
                self.tarjan_dfs_iterative(i, disc, low, stack, in_stack, time_ref, scc_list)

        return scc_list

    def minimize_edges_in_scc(self, scc: List[int]) -> List[Tuple[int, int]]:
        if not scc:
            return []
        nodes: Set[int] = set(scc)
        
        forward_tree = self.build_spanning_tree(scc[0], self.adj, nodes)
        reverse_tree = self.build_spanning_tree(scc[0], self.rev_adj, nodes)
        essential_edges = list(forward_tree.union(reverse_tree))

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
        
        reduced_edges: List[Tuple[int, int]] = []
        for scc in SCCs:
            min_edges = self.minimize_edges_in_scc(scc)
            reduced_edges.extend(min_edges)

        # Sort for deterministic output
        reduced_edges.sort()
        return reduced_edges
