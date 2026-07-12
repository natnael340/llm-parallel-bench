from typing import List, Tuple, Optional
import numbers
from concurrent.futures import ProcessPoolExecutor
import os


def get_size(matrix: List[List[float]]) -> Tuple[int, int]:
    """Return (rows, cols) of a rectangular matrix."""
    return len(matrix), len(matrix[0])


def validate_matrix(matrix: List[List[float]], name: str = "Matrix"):
    """Validate matrix is a non-empty rectangular list-of-lists of numbers."""
    if matrix is None or not isinstance(matrix, list) or not matrix:
        raise ValueError(f"{name} must be a non-empty list of rows.")
    if not isinstance(matrix[0], list) or not matrix[0]:
        raise ValueError(f"{name} must have at least one column.")
    
    cols = len(matrix[0])
    for r, row in enumerate(matrix):
        if not isinstance(row, list):
            raise ValueError(f"{name} row {r} is not a list.")
        if len(row) != cols:
            raise ValueError(f"{name} is ragged: row {r} has {len(row)} cols, expected {cols}.")
        for c, v in enumerate(row):
            if not isinstance(v, numbers.Real):
                raise ValueError(f"{name}[{r}][{c}] is not a real number: {v!r}")
        

def zeros(rows: int, cols: int) -> List[List[float]]:
    return [[0.0] * cols for _ in range(rows)]


def partial_matmul(
        A: List[List[float]], 
        B: List[List[float]], 
        C: List[List[float]],
        alpha: float,
        m0: int,
        n0: int,
        kb: int,
) -> None:
    """Compute a tile of C using packed A and B tiles."""
    C_loc = C  # localize lookup
    for i_off, Aik in enumerate(A):
        Ci = C_loc[m0 + i_off]
        A_loc = Aik
        for j_off, Bjk in enumerate(B):
            B_loc = Bjk
            s = 0.0
            for k in range(kb):
                s += A_loc[k] * B_loc[k]
            Ci[n0 + j_off] += alpha * s


def transpose(matrix: List[List[float]]) -> List[List[float]]:
    return [list(col) for col in zip(*matrix)]


def pack_matrix(matrix: List[List[float]], a0: int, a1: int, b0: int, b1: int) -> List[List[float]]:
    return [row[a0:a1] for row in matrix[b0:b1]]


def _compute_tile_task(args):
    """
    Worker function to compute one (m0, n0) tile for a given k0 slice.
    Returns a list of updates: [(row_idx, col_idx, value), ...]
    
    This function replicates the exact accumulation logic of the sequential version
    to ensure bit-exact reproducibility.
    """
    A, Bt, alpha, m0, m1, n0, n1, k0, k1, kb = args
    
    # Pack the required slices
    Apack = pack_matrix(A, k0, k1, m0, m1)
    Bpack = pack_matrix(Bt, k0, k1, n0, n1)
    
    # Compute partial results using the EXACT same logic as sequential
    updates = []
    for i_off, Aik in enumerate(Apack):
        A_loc = Aik
        for j_off, Bjk in enumerate(Bpack):
            B_loc = Bjk
            s = 0.0
            # Use the exact same accumulation order as sequential
            for k in range(kb):
                s += A_loc[k] * B_loc[k]
            # Only record non-zero updates to reduce communication overhead
            if s != 0.0:
                updates.append((m0 + i_off, n0 + j_off, alpha * s))
    
    return updates


def gemm(
        A: List[List[float]], 
        B: List[List[float]],
        alpha: float = 1.0, 
        C: Optional[List[List[float]]] = None, 
        beta: float = 0,
        MB: int = 64,
        NB: int = 64,
        KB: int = 64,
):
    """
    Compute C := alpha * A * B + beta * C (parallel version).
    
    This implementation parallelizes the computation across tiles while preserving
    the exact accumulation order of the sequential version for bit-exact reproducibility.
    
    :param A: m x k matrix (list-of-lists)
    :param B: k x n matrix (list-of-lists)
    :param alpha: multiplier for A*B
    :param C: optional m x n accumulation buffer (created if None)
    :param beta: multiplier for existing C (applied only if C is provided)
    :param MB,NB,KB: tile sizes
    :return: m x n result (C) as list-of-lists
    """
    validate_matrix(A, "A")
    validate_matrix(B, "B")

    m, k = get_size(A)
    k2, n = get_size(B)

    if k != k2:
        raise ValueError(f"Shape mismatch: A is ({m},{k}), B is ({k2},{n}).")
    
    if C is None:
        C = zeros(m, n)
    else:
        validate_matrix(C, "C")
        m2, n2 = get_size(C) 
        if m2 != m or n2 != n:
            raise ValueError(f"C has shape ({m2},{n2}); expected ({m},{n}).")
        if beta != 1.0:
            for i in range(m):
                for j in range(n):
                    C[i][j] *= beta  

    if alpha == 0.0:
        return C
    
    # Transpose B once (same as sequential)
    Bt = transpose(B)
    
    # Determine number of workers (cap at CPU count)
    num_workers = min(os.cpu_count() or 1, 8)
    
    # Compute tile counts
    n_tiles = (n + NB - 1) // NB
    m_tiles = (m + MB - 1) // MB
    
    # Threshold for parallel execution: use parallel only if we have enough work
    # For small problems, the overhead of process creation dominates
    min_tiles_for_parallel = num_workers * 2
    total_tiles_per_k = n_tiles * m_tiles
    
    if total_tiles_per_k < min_tiles_for_parallel:
        # Fall back to sequential for small problems
        for n0 in range(0, n, NB):
            n1 = min(n0 + NB, n)
            for k0 in range(0, k, KB):
                k1 = min(k0 + KB, k)
                Bpack = pack_matrix(Bt, k0, k1, n0, n1)
                kb = k1 - k0
                
                for m0 in range(0, m, MB):
                    m1 = min(m0 + MB, m)
                    Apack = pack_matrix(A, k0, k1, m0, m1)
                    partial_matmul(Apack, Bpack, C, alpha, m0, n0, kb)
        return C
    
    # Parallel execution: iterate over k0 sequentially (for deterministic reduction),
    # but parallelize over (n0, m0) pairs
    for k0 in range(0, k, KB):
        k1 = min(k0 + KB, k)
        kb = k1 - k0
        
        # Build task list for this k0 slice in deterministic order
        tasks = []
        for n0 in range(0, n, NB):
            n1 = min(n0 + NB, n)
            for m0 in range(0, m, MB):
                m1 = min(m0 + MB, m)
                tasks.append((A, Bt, alpha, m0, m1, n0, n1, k0, k1, kb))
        
        # Execute tasks in parallel and collect results in order
        with ProcessPoolExecutor(max_workers=num_workers) as executor:
            results = list(executor.map(_compute_tile_task, tasks))
        
        # Apply updates to C in the order tasks were submitted (deterministic)
        for updates in results:
            for row_idx, col_idx, value in updates:
                C[row_idx][col_idx] += value
    
    return C
