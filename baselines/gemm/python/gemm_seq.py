from typing import List, Tuple, Optional
import numbers


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
    C_loc = C # localize lookup
    for i_off, Aik in enumerate(A):
        Ci = C_loc[m0 + i_off]
        A_loc = Aik
        for j_off, Bjk in enumerate(B):
            B_loc = Bjk
            s = 0.0
            for k in range(kb):
                s+= A_loc[k] * B_loc[k]
            Ci[n0 + j_off] += alpha * s


def transpose(matrix: List[List[float]]) -> List[List[float]]:
    return [list(col) for col in zip(*matrix)]


def pack_matrix(matrix: List[List[float]], a0: int, a1: int, b0: int, b1: int) -> List[List[float]]:
    return [row[a0:a1] for row in matrix[b0:b1]]


def gemm(
        A: List[List[float]], 
        B: List[List[float]],
        alpha: float = 1.0, 
        C: Optional[List[List[float]]] = None, 
        beta: float=0,
        MB: int = 64,
        NB: int = 64,
        KB: int = 64,
):
    """
    Compute C := alpha * A * B + beta * C.
    :param A: m x k
    :param B: k x n
    :param alpha: multiplier for A*B
    :param C: optional m x n accumulation buffer (created if None)
    :param beta: multiplier for existing C (applied only if C is provided)
    :param MB,NB,KB: tile sizes
    :return: m x n result (C)
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
            if beta == 0.0:
                for i in range(m):
                    for j in range(n):
                        C[i][j] = 0.0
            else:
                for i in range(m):
                    for j in range(n):
                        C[i][j] *= beta  

    if alpha == 0.0:
        return C
    
    Bt = transpose(B)
    
    for n0 in range(0, n, NB):
        n1 = min(n0 + NB, n)
        for k0 in range(0, k, KB):
            k1 = min(k0 + KB, k)
            kb = k1 - k0
            Bpack = pack_matrix(Bt, k0, k1, n0, n1)

            for m0 in range(0, m, MB):
                m1 = min(m0 + MB, m)
                Apack = pack_matrix(A, k0, k1, m0, m1)
                partial_matmul(Apack, Bpack, C, alpha, m0, n0, kb)
    
    return C


def print_matrix(matrix: List[List[float]]) -> None:
    print("=========================")
    for row in matrix:
        print(row)
    print("=========================")
    

if __name__ == "__main__":
    A = [[1, 2, 3], [4, 5, 6], [7, 8, 9]]
    B = [[1, 4], [2, 5], [3, 6]]

    #print(gemm(A, B, 1))
    print_matrix(A)
    print_matrix(B)
    print_matrix(gemm(A, B, 1))

    
    