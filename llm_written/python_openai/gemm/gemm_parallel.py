from typing import List, Tuple, Optional
import numbers
import os
from concurrent.futures import ProcessPoolExecutor, as_completed

# Keep the public API (function names, signatures) the same as the sequential version


def get_size(matrix: List[List[float]]) -> Tuple[int, int]:
    """Return (rows, cols) of a rectangular matrix."""
    return len(matrix), len(matrix[0])


def validate_matrix(matrix: List[List[float]], name: str = "Matrix"):
    """Validate matrix is a non-empty rectangular list-of-lists of numbers."""
    if matrix is None or not isinstance(matrix, list):
        raise ValueError(f"{name} must be a non-empty list of rows.")
    if len(matrix) == 0:
        raise ValueError(f"{name}  must have at least one row.")
    if not isinstance(matrix[0], list) or len(matrix[0]) == 0:
        raise ValueError(f"{name} must have at least one column.")

    cols = len(matrix[0])
    for r, row in enumerate(matrix):
        if not isinstance(row, list):
            raise ValueError(f"{name} row {r} is not a list.")
        if len(row) != cols:
            raise ValueError(
                f"{name} is ragged: row {r} has {len(row)} cols, expected {cols}."
            )
        for c, v in enumerate(row):
            if not isinstance(v, numbers.Real):
                raise ValueError(f"{name}[{r}][{c}] is not a real number: {v!r}")


def generate_matrix(rows: int, cols: int) -> List[List[float]]:
    return [[0.0] * cols for _ in range(rows)]


def transpose(matrix: List[List[float]]) -> List[List[float]]:
    return [list(col) for col in zip(*matrix)]


def pack_matrix(
    matrix: List[List[float]], a0: int, a1: int, b0: int, b1: int
) -> List[List[float]]:
    return [row[a0:a1] for row in matrix[b0:b1]]


# Worker: compute contributions for a single (m-block x n-block) at a given k-slab
# Returns a dense block with alpha-scaled contributions for this slab only

def _compute_block_contrib(
    Apack: List[List[float]], Bpack: List[List[float]], kb: int, alpha: float
) -> List[List[float]]:
    # Apack shape: (mb x kb), Bpack shape: (nb x kb), both contiguous lists
    mb = len(Apack)
    nb = len(Bpack)
    # initialize result block (mb x nb) with zeros
    block = [[0.0] * nb for _ in range(mb)]

    # For each i in mb and j in nb, compute s = dot(Apack[i][:kb], Bpack[j][:kb])
    # Accumulate deterministically in the same k-order as baseline
    for i_off, Aik in enumerate(Apack):
        row_out = block[i_off]
        for j_off, Bjk in enumerate(Bpack):
            s = 0.0
            # fixed left-to-right summation order over k
            for k in range(kb):
                s += Aik[k] * Bjk[k]
            row_out[j_off] = alpha * s
    return block


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
    Compute C := alpha * A * B + beta * C.

    A is (m x k), B is (k x n), C is (m x n). If C is None, a zero matrix is used.
    """
    from llm_written.python_openai.gemm.gemm_seq import gemm as seq_gemm  # for small-input fast path

    validate_matrix(A, "A")
    validate_matrix(B, "B")

    m, k = get_size(A)
    k2, n = get_size(B)

    if k != k2:
        raise ValueError(f"Shape mismatch: A is ({m},{k}), B is ({k2},{n}).")

    # Prepare C and scale by beta if needed (same semantics as baseline)
    if C is not None:
        validate_matrix(C, "C")
        m2, n2 = get_size(C)
        if m2 != m or n2 != n:
            raise ValueError(f"C has shape ({m2},{n2}); expected ({m},{n}).")
        if beta != 1.0:
            for i in range(m):
                row = C[i]
                for j in range(n):
                    row[j] *= beta
    else:
        C = generate_matrix(m, n)

    if alpha == 0.0:
        return C

    # Small-input or single-core fast path: defer to sequential reference
    total_elems = m * n
    cpu_cnt = os.cpu_count() or 1
    # Heuristic threshold: below this, the overhead of processes dominates
    if total_elems <= 1024 or cpu_cnt <= 1:
        return seq_gemm(A, B, alpha=alpha, C=C, beta=1.0, MB=MB, NB=NB, KB=KB)
        # beta is already applied above, so pass beta=1.0 to avoid rescaling

    Bt = transpose(B)

    # Set up a reusable process pool bounded by CPU and by 4 to avoid oversubscription
    max_workers_global = min(cpu_cnt, max(1, (m + MB - 1) // MB), 4)

    executor: Optional[ProcessPoolExecutor] = None
    try:
        if max_workers_global > 1:
            executor = ProcessPoolExecutor(max_workers=max_workers_global)
    except Exception:
        executor = None  # Fallback to sequential in restricted environments

    try:
        # Outer loops over tiles in deterministic order matching baseline
        for n0 in range(0, n, NB):
            n1 = min(n0 + NB, n)
            for k0 in range(0, k, KB):
                k1 = min(k0 + KB, k)
                kb = k1 - k0
                # Pack B for this (n0, k0)
                Bpack = pack_matrix(Bt, k0, k1, n0, n1)

                # Create tasks across m-tiles for this (n0, k0)
                m_tiles = []
                tasks = []
                for m0 in range(0, m, MB):
                    m1 = min(m0 + MB, m)
                    Apack = pack_matrix(A, k0, k1, m0, m1)
                    m_tiles.append((m0, m1))
                    tasks.append((m0, Apack))

                blocks_by_m0 = {}
                if executor is None:
                    # Sequential fallback
                    for m0, Apack in tasks:
                        block = _compute_block_contrib(Apack, Bpack, kb, alpha)
                        blocks_by_m0[m0] = block
                else:
                    future_map = {}
                    try:
                        for (m0, Apack) in tasks:
                            fut = executor.submit(
                                _compute_block_contrib, Apack, Bpack, kb, alpha
                            )
                            future_map[fut] = m0
                    except Exception:
                        # Submission failure => fallback to sequential for this slab
                        executor = None
                        blocks_by_m0.clear()
                        for m0, Apack in tasks:
                            block = _compute_block_contrib(Apack, Bpack, kb, alpha)
                            blocks_by_m0[m0] = block
                    else:
                        for f in as_completed(future_map):
                            m0_key = future_map[f]
                            block = f.result()
                            blocks_by_m0[m0_key] = block

                # Merge results into C in deterministic m0 order
                for m0, m1 in m_tiles:
                    block = blocks_by_m0[m0]
                    mb = m1 - m0
                    nb = n1 - n0
                    for i_off in range(mb):
                        Ci = C[m0 + i_off]
                        brow = block[i_off]
                        for j_off in range(nb):
                            Ci[n0 + j_off] += brow[j_off]
    finally:
        if executor is not None:
            executor.shutdown()

    return C
