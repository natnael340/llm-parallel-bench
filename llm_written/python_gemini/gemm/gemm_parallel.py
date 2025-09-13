
from typing import List, Tuple, Optional
import numbers
import concurrent.futures
import os

# --- Matrix Validation and Helpers (from original code) ---

def get_size(matrix: List[List[float]]) -> Tuple[int, int]:
    """Return (rows, cols) of a rectangular matrix."""
    return len(matrix), len(matrix[0])


def validate_matrix(matrix: List[List[float]], name: str = "Matrix"):
    """Validate matrix is a non-empty rectangular list-of-lists of numbers."""
    if not isinstance(matrix, list) or not matrix:
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


def generate_matrix(rows: int, cols: int) -> List[List[float]]:
    """Generates a matrix of zeros."""
    return [[0.0] * cols for _ in range(rows)]


def transpose(matrix: List[List[float]]) -> List[List[float]]:
    """Transposes a matrix."""
    return [list(col) for col in zip(*matrix)]


def pack_matrix(matrix: List[List[float]], col_start: int, col_end: int, row_start: int, row_end: int) -> List[List[float]]:
    """Extracts a submatrix (pack) for block processing."""
    return [row[col_start:col_end] for row in matrix[row_start:row_end]]


# --- Sequential Implementation ---

def _partial_matmul_sequential(
        A_pack: List[List[float]], 
        B_pack: List[List[float]], 
        C: List[List[float]],
        alpha: float,
        m0: int,
        n0: int,
        kb: int,
) -> None:
    """Helper for the sequential version to perform block multiplication."""
    for i_off, A_ik in enumerate(A_pack):
        C_i = C[m0 + i_off]
        for j_off, B_jk in enumerate(B_pack):
            s = 0.0
            for k in range(kb):
                s += A_ik[k] * B_jk[k]
            C_i[n0 + j_off] += alpha * s


def gemm_sequential(
        A: List[List[float]], 
        B: List[List[float]],
        alpha: float = 1.0, 
        C: Optional[List[List[float]]] = None, 
        beta: float = 0.0,
        MB: int = 64,
        NB: int = 64,
        KB: int = 64,
):
    """
    Sequential implementation of C := alpha * A * B + beta * C.
    This is the original provided algorithm, preserved for baseline and small inputs.
    """
    validate_matrix(A, "A")
    validate_matrix(B, "B")

    m, k = get_size(A)
    k2, n = get_size(B)

    if k != k2:
        raise ValueError(f"Shape mismatch: A is ({m},{k}), B is ({k2},{n}).")
    
    if C is not None:
        validate_matrix(C, "C")
        m2, n2 = get_size(C) 
        if m2 != m or n2 != n:
            raise ValueError(f"C has shape ({m2},{n2}); expected ({m},{n}).")
        if beta != 1.0:
            for i in range(m):
                for j in range(n):
                    C[i][j] *= beta  
    else:
        # If C is not provided, beta is assumed to be 0.
        C = generate_matrix(m, n)

    if alpha == 0.0:
        return C
    
    B_t = transpose(B)
    
    for n0 in range(0, n, NB):
        n1 = min(n0 + NB, n)
        for k0 in range(0, k, KB):
            k1 = min(k0 + KB, k)
            B_pack = pack_matrix(B_t, k0, k1, n0, n1)

            for m0 in range(0, m, MB):
                m1 = min(m0 + MB, m)
                A_pack = pack_matrix(A, k0, k1, m0, m1)

                kb = k1 - k0
                _partial_matmul_sequential(A_pack, B_pack, C, alpha, m0, n0, kb)
    
    return C


# --- Parallel Implementation ---

# Global variables for worker processes to hold shared matrices
_A_shared = None
_Bt_shared = None

def _init_worker(A: List[List[float]], B_t: List[List[float]]):
    """Initializer for each worker process in the pool."""
    global _A_shared, _Bt_shared
    _A_shared = A
    _Bt_shared = B_t

def _gemm_worker(args: Tuple) -> Tuple[int, int, List[List[float]]]:
    """
    Worker function that computes one block of the output matrix C.
    It reads from the global shared matrices _A_shared and _Bt_shared.
    """
    global _A_shared, _Bt_shared
    alpha, m0, n0, m1, n1, k, KB = args
    
    C_block_rows = m1 - m0
    C_block_cols = n1 - n0
    C_block = generate_matrix(C_block_rows, C_block_cols)

    for k0 in range(0, k, KB):
        k1 = min(k0 + KB, k)
        kb = k1 - k0

        A_pack = pack_matrix(_A_shared, k0, k1, m0, m1)
        B_pack = pack_matrix(_Bt_shared, k0, k1, n0, n1)

        for i_off, A_ik in enumerate(A_pack):
            C_i = C_block[i_off]
            for j_off, B_jk in enumerate(B_pack):
                s = 0.0
                for k_inner in range(kb):
                    s += A_ik[k_inner] * B_jk[k_inner]
                C_i[j_off] += s

    if alpha != 1.0:
        for r in range(C_block_rows):
            for c in range(C_block_cols):
                C_block[r][c] *= alpha

    return m0, n0, C_block


def gemm(
        A: List[List[float]], 
        B: List[List[float]],
        alpha: float = 1.0, 
        C: Optional[List[List[float]]] = None, 
        beta: float = 0.0,
        MB: int = 64,
        NB: int = 64,
        KB: int = 64,
):
    """
    Compute C := alpha * A * B + beta * C using a parallel block-based algorithm.

    A is (m x k), B is (k x n), C is (m x n). If C is None, a zero matrix is used.
    The operation is parallelized by dividing the output matrix C into blocks
    and computing each block in a separate process.
    """
    validate_matrix(A, "A")
    validate_matrix(B, "B")

    m, k = get_size(A)
    k2, n = get_size(B)

    if k != k2:
        raise ValueError(f"Shape mismatch: A is ({m},{k}), B is ({k2},{n}).")

    # Fast path for small matrices where parallel overhead is not worth it.
    num_m_blocks = (m + MB - 1) // MB
    num_n_blocks = (n + NB - 1) // NB
    # Use sequential version if the number of tasks is less than or equal to the number of available cores.
    if num_m_blocks * num_n_blocks <= (os.cpu_count() or 1):
        return gemm_sequential(A, B, alpha, C, beta, MB, NB, KB)

    # Handle the output matrix C and the beta scaling factor.
    if C is not None:
        validate_matrix(C, "C")
        m2, n2 = get_size(C) 
        if m2 != m or n2 != n:
            raise ValueError(f"C has shape ({m2},{n2}); expected ({m},{n}).")
        if beta != 1.0:
            for i in range(m):
                for j in range(n):
                    C[i][j] *= beta  
    else:
        # If C is not provided, beta is assumed to be 0.
        C = generate_matrix(m, n)

    if alpha == 0.0:
        return C
    
    B_t = transpose(B)
    
    tasks = []
    for n0 in range(0, n, NB):
        n1 = min(n0 + NB, n)
        for m0 in range(0, m, MB):
            m1 = min(m0 + MB, m)
            tasks.append((alpha, m0, n0, m1, n1, k, KB))

    num_workers = os.cpu_count() or 1
    with concurrent.futures.ProcessPoolExecutor(
        max_workers=num_workers,
        initializer=_init_worker,
        initargs=(A, B_t)
    ) as executor:
        
        # The results can be processed as they are completed.
        # The order of addition to C does not matter for correctness.
        futures = [executor.submit(_gemm_worker, task) for task in tasks]
        for future in concurrent.futures.as_completed(futures):
            m0_res, n0_res, C_block = future.result()
            
            if not C_block or not C_block[0]:
                continue

            m1_res = m0_res + len(C_block)
            n1_res = n0_res + len(C_block[0])

            # Add the computed block to the final matrix C
            for i in range(m0_res, m1_res):
                for j in range(n0_res, n1_res):
                    C[i][j] += C_block[i - m0_res][j - n0_res]
    
    return C

if __name__ == '__main__':
    # Example usage guard
    A_sample = [[1.0, 2.0, 3.0], [4.0, 5.0, 6.0], [7.0, 8.0, 9.0]]
    B_sample = [[1.0, 4.0], [2.0, 5.0], [3.0, 6.0]]
    
    print("Running sample matrix multiplication...")
    C_result = gemm(A_sample, B_sample, alpha=1.0)
    
    print("Matrix A:")
    for row in A_sample:
        print(row)
    print("\nMatrix B:")
    for row in B_sample:
        print(row)
    print("\nResult C = A * B:")
    for row in C_result:
        print([round(x, 1) for x in row])

    # Expected: [[14.0, 32.0], [32.0, 77.0], [50.0, 122.0]]
