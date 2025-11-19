import time
import math
import random
from typing import List, Tuple

import pytest
from graph import Graph


def ring_scc(start: int, n: int, graph: Graph) -> List[Tuple[int, int]]:
    reduced_sccs = []
    for i in range(start, n):
        v = (i + 1) % n
        v = v if v != 0 else start

        if (i == v):
            continue
        
        graph.add_edge(i, v) 

        if (i+1) != n-1:
            reduced_sccs.append((i, v))

        if i != start:
            u = (i - 1) % n
            u = u if u != 0 else start
            reduced_sccs.append((i , u))
    
    return reduced_sccs


def test_empty_graph():
    g = Graph(0)
    # No crash + trivial behavior
    sccs = g.find_sccs()
    assert sccs == []
    reduced = g.reduce_edges()
    assert reduced == []

def test_singleton_no_edges():
    g = Graph(1)

    assert g.find_sccs() == [[0]]
    assert g.reduce_edges() == []

def test_singleton_self_loop():
    g = Graph(1)
    g.add_edge(0, 0)
    assert g.find_sccs() == [[0]]
    assert g.reduce_edges() == []

def test_simple_cycle_3():
    g = Graph(3)
    g.add_edge(0, 1)
    g.add_edge(1, 2)
    g.add_edge(2, 0)

    assert g.find_sccs() == [[2, 1, 0]]
    assert g.reduce_edges() == [(2, 0), (0, 1), (1, 2), (1, 0)]

def test_two_node_mutual_scc():
    g = Graph(2)
    g.add_edge(0, 1)
    g.add_edge(1, 0)
    
    assert g.find_sccs() == [[1, 0]]
    assert g.reduce_edges() == [(1, 0), (1, 0)]

def test_dense_three_node_scc():
    g = Graph(3)
    for u, v in [(0,1),(1,2),(2,0),(0,2),(2,1),(1,0)]:
        g.add_edge(u, v)
    assert g.find_sccs() == [[2, 1, 0]]
    assert g.reduce_edges() == [(2, 0), (2, 1), (2, 0), (2, 1)]

def test_multiple_sccs_with_cross():
    # SCC1: 0->1->2->0; SCC2: 3<->4; cross 2->3
    g = Graph(5)
    g.add_edge(0, 1)
    g.add_edge(1, 2)
    g.add_edge(2, 0)

    g.add_edge(3, 4)
    g.add_edge(4, 3)

    g.add_edge(2, 3)

    expected = [(4, 3), (4, 3), (2, 0), (0, 1), (2, 1), (1, 0)]
    
    assert g.find_sccs() == [[4, 3], [2, 1, 0]]
    reduced = g.reduce_edges()
    
    assert len(reduced) == len(expected)
    assert set(reduced) == set(expected)

def test_disconnected_with_dag_component():
    # SCC: 0,1,2 ; DAG piece: 3->4->5
    g = Graph(6)
    g.add_edge(0, 1)
    g.add_edge(1, 2)
    g.add_edge(2, 0)

    g.add_edge(3, 4)
    g.add_edge(4, 5)

    expected = [(2, 0), (0, 1), (2, 1), (1, 0)]
    
    assert g.find_sccs() == [[2, 1, 0], [5], [4], [3]]
    reduced = g.reduce_edges()
    
    assert len(reduced) == len(expected)
    assert set(reduced) == set(expected)

def test_star_like_scc():
    # 0 connected both ways with leaves => single SCC
    n = 7
    g = Graph(n)
    for i in range(1, n):
        g.add_edge(0, i)
        g.add_edge(i, 0)
    
    expected_reduced_edges = [(6, 0), (6, 0), (0, 1), (0, 2), (0, 3), (0, 4), (0, 5), (0, 1), (0, 2), (0, 3), (0, 4), (0, 5) ]
    assert g.find_sccs() == [list(reversed(range(n)))]
    reduced = g.reduce_edges()
    
    assert len(reduced) == len(expected_reduced_edges)
    assert set(reduced) == set(expected_reduced_edges)

def test_large_ring_scc():
    n = 300
    g = Graph(n)
    expected_reduced_edges = []
    for i in range(n):
        g.add_edge(i, (i + 1) % n)
        if (i+1) != n-1:
            expected_reduced_edges.append((i, (i + 1) % n))
        if i != 0:
            expected_reduced_edges.append((i , (i -1) % n ))

    assert g.find_sccs() == [list(reversed(range(n)))]
    reduced = g.reduce_edges()
    
    assert len(reduced) == len(expected_reduced_edges)
    assert set(reduced) == set(expected_reduced_edges)


@pytest.mark.parametrize("trial", range(5))
def test_random_sccs(trial):
    # Build SCC by starting with a ring then add extra edges
    n = 80
    g = Graph(n)
    expected_reduced_edges = []
    for i in range(n):
        g.add_edge(i, (i + 1) % n)
        if (i+1) != n-1:
            expected_reduced_edges.append((i, (i + 1) % n))
        if i != 0:
            expected_reduced_edges.append((i , (i -1) % n ))
        
    random.seed(2025 + trial)
    for _ in range(n * 2):
        u, v = random.randrange(n), random.randrange(n)
        if u != v:
            g.add_edge(u, v)
    
    assert g.find_sccs() == [list(reversed(range(n)))]
    reduced = g.reduce_edges()
    assert len(reduced) == len(expected_reduced_edges)
    
