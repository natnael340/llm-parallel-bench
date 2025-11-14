import argparse
from typing import List, Tuple, Any
import random
import sys
import time

import pyperf

import gc


#=============================================Graph Section==================================
from typing import List, Set, Tuple
from concurrent.futures import ProcessPoolExecutor
import os

# This is a static/top-level function to be used by the ProcessPoolExecutor.
# It cannot be a method of the Graph class because that would require pickling
# the entire 'self' object, which is inefficient and can fail.
def _minimize_scc_worker(args: Tuple[List[List[int]], List[List[int]], List[int]]) -> List[Tuple[int, int]]:
    """
    Worker function to find essential edges for a single SCC.
    Designed to be run in a separate process.
    """
    adj, rev_adj, scc = args
    if not scc:
        return []

    nodes: Set[int] = set(scc)
    start_node = scc[0]

    # Helper to build a spanning tree, kept local to the worker
    def build_spanning_tree(
        start: int, graph: List[List[int]], nodes_in_scc: Set[int]
    ) -> Set[Tuple[int, int]]:
        spanning_tree: Set[Tuple[int, int]] = set()
        visited: Set[int] = set()
        stack: List[int] = [start]
        visited.add(start)

        while stack:
            node = stack.pop()
            for neighbor in graph[node]:
                if neighbor in nodes_in_scc and neighbor not in visited:
                    spanning_tree.add((node, neighbor))
                    visited.add(neighbor)
                    stack.append(neighbor)
        return spanning_tree

    # Step 1: forward spanning tree using DFS
    forward_tree = build_spanning_tree(start_node, adj, nodes)

    # Step 2: reverse spanning tree using DFS on reversed graph
    reverse_tree = build_spanning_tree(start_node, rev_adj, nodes)

    # Step 3: merge both trees
    essential_edges = list(forward_tree.union(reverse_tree))
    return essential_edges


class Graph:
    def __init__(self, v: int):
        self.V: int = v
        self.adj: List[List[int]] = [[] for _ in range(v)]
        self.rev_adj: List[List[int]] = [[] for _ in range(v)]
        # Threshold to avoid parallel overhead for small number of independent tasks
        self.MIN_SCCS_FOR_PARALLEL = 2

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

    def reduce_edges(self) -> List[Tuple[int, int]]:
        sccs = self.find_sccs()

        if len(sccs) < self.MIN_SCCS_FOR_PARALLEL:
            all_min_edges = []
            for scc in sccs:
                args = (self.adj, self.rev_adj, scc)
                all_min_edges.extend(_minimize_scc_worker(args))
            all_min_edges.sort()
            return all_min_edges

        reduced_edges_per_scc = []
        tasks = [(self.adj, self.rev_adj, scc) for scc in sccs]
        max_workers = os.cpu_count()

        with ProcessPoolExecutor(max_workers=max_workers) as executor:
            reduced_edges_per_scc = list(executor.map(_minimize_scc_worker, tasks))

        all_min_edges = [edge for scc_edges in reduced_edges_per_scc for edge in scc_edges]
        all_min_edges.sort()

        return all_min_edges
#============================================================================================


def ring_scc(start: int, n: int, graph: Any) -> None:
    for i in range(start, n):
        v = (i + 1) % n
        v = v if v != 0 else start

        if (i == v):
            continue
        
        graph.add_edge(i, v) 



def build_graph(n: int, cluster_size: int, no_cluster_in_group: int, graph_class: Any) -> Tuple[Any, List[Tuple[int, int]]]:    
    graph = graph_class(n)
    random.seed(43)
    for i in range(0, n, cluster_size):
        ring_scc(i, min(i + cluster_size, n), graph)
        
        current_cluster = i // cluster_size
        if current_cluster // no_cluster_in_group == (current_cluster + 1) // no_cluster_in_group:
            
            if (i + cluster_size) < n:
                u = random.randrange(i, min(i + cluster_size, n) - 1)
                v = random.randrange(min(i + cluster_size, n), min(i + 2 * cluster_size, n) - 1)
                graph.add_edge(u, v)

    return graph


def add_cmdline_args(cmd, args):
    cmd.extend(["--module", args.module])
    cmd.extend(["--func", args.func])

def main():
    graph_size = 100_000
    cluster_size = 300
    no_cluster_in_group = 3

    if cluster_size * no_cluster_in_group >= 1000:
        raise ValueError("cluster_size * no_cluster_in_group must be less than 1000 to avoid RecursionError.")    


    graph = build_graph(graph_size, cluster_size, no_cluster_in_group, Graph)

    runner = pyperf.Runner(values=100, warmups=5, processes=1)

    gc.disable()
    try:
        runner.bench_func(f"Benchmarking", graph.reduce_edges_parallel, inner_loops=1)
    finally:
        gc.enable()


if __name__ == "__main__":
    main()