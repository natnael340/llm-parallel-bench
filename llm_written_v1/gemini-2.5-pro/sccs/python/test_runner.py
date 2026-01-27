import sys
import time
import random
import hashlib
from typing import List, Tuple, Any

# Import the sequential and parallel implementations
from algo_sequential import Graph as SequentialGraph
from algo_parallel import Graph as ParallelGraph

# --- Test Case Generation ---

def generate_graph_with_sccs(
    num_vertices: int, num_edges: int, num_sccs: int, min_scc_size: int = 3
) -> Tuple[int, List[Tuple[int, int]]]:
    """
    Generates a graph with a specified number of SCCs.
    """
    if num_sccs * min_scc_size > num_vertices:
        raise ValueError("Not enough vertices to create the desired number of SCCs with the given minimum size.")

    edges: List[Tuple[int, int]] = []
    nodes = list(range(num_vertices))
    random.shuffle(nodes)

    # 1. Create the SCCs
    scc_nodes_list = []
    node_idx = 0
    for _ in range(num_sccs):
        scc_size = min_scc_size + random.randint(0, (num_vertices - node_idx - min_scc_size) // (num_sccs - len(scc_nodes_list)))
        scc = nodes[node_idx : node_idx + scc_size]
        scc_nodes_list.append(scc)
        node_idx += scc_size

        # Create a cycle within the SCC to ensure it's strongly connected
        for i in range(len(scc)):
            edges.append((scc[i], scc[(i + 1) % len(scc)]))

    # 2. Add random edges within SCCs
    edges_per_scc = (num_edges // (num_sccs if num_sccs > 0 else 1)) // 2
    for scc in scc_nodes_list:
        if len(scc) > 1:
            for _ in range(edges_per_scc):
                u, v = random.sample(scc, 2)
                edges.append((u, v))

    # 3. Add edges between SCCs (forming a DAG of SCCs)
    for i in range(num_sccs - 1):
        u = random.choice(scc_nodes_list[i])
        v = random.choice(scc_nodes_list[i + 1])
        edges.append((u, v))

    # 4. Add remaining random edges
    remaining_edges = num_edges - len(edges)
    for _ in range(remaining_edges):
        u, v = random.randint(0, num_vertices - 1), random.randint(0, num_vertices - 1)
        if u != v:
            edges.append((u, v))

    return num_vertices, list(set(edges))


# --- Utility Functions ---

def build_graph(graph_class, v: int, edges: List[Tuple[int, int]]):
    g = graph_class(v)
    for u, w in edges:
        g.add_edge(u, w)
    return g

def result_to_hash(result: List[Any]) -> str:
    """Computes a stable hash for a list of results."""
    # Sort the list of tuples to ensure hash is order-independent
    sorted_result = sorted(result)
    s = str(sorted_result).encode()
    return hashlib.sha256(s).hexdigest()

# --- Test Runner ---

def run_test(test_case: Tuple[int, List[Tuple[int, int]]], test_name: str):
    """
    Runs a single differential test.
    """
    num_vertices, edges = test_case
    print(f"--- Running Test: {test_name} ---")
    print(f"Vertices: {num_vertices}, Edges: {len(edges)}")

    # --- Sequential Execution ---
    seq_graph = build_graph(SequentialGraph, num_vertices, edges)
    start_time = time.perf_counter()
    seq_result = seq_graph.reduce_edges()
    seq_duration = time.perf_counter() - start_time
    seq_hash = result_to_hash(seq_result)
    print(f"Sequential: Time={seq_duration:.4f}s, Result Hash={seq_hash}")

    # --- Parallel Execution (Run 1) ---
    par_graph1 = build_graph(ParallelGraph, num_vertices, edges)
    start_time = time.perf_counter()
    par_result1 = par_graph1.reduce_edges()
    par_duration1 = time.perf_counter() - start_time
    par_hash1 = result_to_hash(par_result1)
    print(f"Parallel (1): Time={par_duration1:.4f}s, Result Hash={par_hash1}")

    # --- Parallel Execution (Run 2 - for determinism check) ---
    par_graph2 = build_graph(ParallelGraph, num_vertices, edges)
    start_time = time.perf_counter()
    par_result2 = par_graph2.reduce_edges()
    par_duration2 = time.perf_counter() - start_time
    par_hash2 = result_to_hash(par_result2)
    print(f"Parallel (2): Time={par_duration2:.4f}s, Result Hash={par_hash2}")

    # --- Verification ---
    correctness_ok = (seq_hash == par_hash1)
    determinism_ok = (par_hash1 == par_hash2)
    
    print(f"✅ Correctness Check (Seq vs Par1): {'PASS' if correctness_ok else 'FAIL'}")
    print(f"✅ Determinism Check (Par1 vs Par2): {'PASS' if determinism_ok else 'FAIL'}")

    # Performance check (only for larger cases)
    speedup = 0
    perf_ok = True
    if num_vertices > 500:
        if par_duration1 > 0:
            speedup = seq_duration / par_duration1
            print(f"🚀 Speedup: {speedup:.2f}x")
            if speedup < 1.1:
                print("⚠️ Performance Warning: Speedup is less than 1.1x.")
                perf_ok = False
        else:
            print("⚠️ Division by zero in speedup calculation.")

    print("-" * (len(test_name) + 20))

    if not (correctness_ok and determinism_ok):
        print("\n❌ Test Failed!")
        # For debugging, print results if they differ
        if not correctness_ok:
            print("Sequential Result:", sorted(seq_result)[:10])
            print("Parallel Result:", sorted(par_result1)[:10])
        if not determinism_ok:
            print("Parallel Run 1:", sorted(par_result1)[:10])
            print("Parallel Run 2:", sorted(par_result2)[:10])
        return False, 0.0

    return True, speedup


def main():
    # Seed for reproducibility
    random.seed(42)

    test_cases = {
        "empty": (0, []),
        "single_node": (1, []),
        "small_dag": (5, [(0, 1), (1, 2), (0, 2), (3, 4)]),
        "small_scc": (4, [(0, 1), (1, 2), (2, 0), (2, 3)]),
        "medium": generate_graph_with_sccs(1000, 5000, 10),
        "large": generate_graph_with_sccs(5000, 25000, 50),
        "huge_sccs": generate_graph_with_sccs(10000, 50000, 200),
    }

    results = []
    overall_success = True

    for name, case in test_cases.items():
        success, speedup = run_test(case, name)
        results.append({"name": name, "success": success, "speedup": speedup})
        if not success:
            overall_success = False

    print("\n--- Overall Summary ---")
    for res in results:
        status = "✅ PASS" if res["success"] else "❌ FAIL"
        print(f"{res['name']:<15} | Status: {status} | Speedup: {res['speedup']:.2f}x")
    
    if not overall_success:
        print("\nSome tests failed.")
        sys.exit(1)
    else:
        print("\nAll tests passed successfully!")
        sys.exit(0)

if __name__ == "__main__":
    main()
