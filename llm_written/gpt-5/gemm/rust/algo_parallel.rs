use std::thread;

pub type Matrix = Vec<Vec<f64>>;

#[derive(Debug)]
pub struct GemmError(pub String);

impl std::fmt::Display for GemmError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "{}", self.0)
    }
}

impl std::error::Error for GemmError {}

pub fn get_size(matrix: &Matrix) -> (usize, usize) {
    (matrix.len(), matrix[0].len())
}

pub fn validate_matrix(matrix: &Matrix, name: &str) -> Result<(), GemmError> {
    if matrix.is_empty() {
        return Err(GemmError(format!("{} must be a non-empty array of rows.", name)));
    }
    if matrix[0].is_empty() {
        return Err(GemmError(format!("{} must have at least one column.", name)));
    }
    let cols = matrix[0].len();
    for (r, row) in matrix.iter().enumerate() {
        if row.len() != cols {
            return Err(GemmError(format!(
                "{} is ragged: row {} has {} cols, expected {}.",
                name, r, row.len(), cols
            )));
        }
    }
    Ok(())
}

pub fn zeros(rows: usize, cols: usize) -> Matrix {
    vec![vec![0.0; cols]; rows]
}

pub fn transpose(matrix: &Matrix) -> Matrix {
    let rows = matrix.len();
    let cols = matrix[0].len();
    let mut result = vec![vec![0.0; rows]; cols];
    for j in 0..cols {
        for i in 0..rows {
            result[j][i] = matrix[i][j];
        }
    }
    result
}

pub fn pack_matrix(matrix: &Matrix, a0: usize, a1: usize, b0: usize, b1: usize) -> Matrix {
    let rows = b1 - b0;
    let mut result = Vec::with_capacity(rows);
    for i in 0..rows {
        result.push(matrix[b0 + i][a0..a1].to_vec());
    }
    result
}

fn partial_matmul_add_into(
    a: &Matrix,
    b: &Matrix,
    c_tile: &mut Matrix,
    alpha: f64,
    kb: usize,
) {
    for (i_off, aik) in a.iter().enumerate() {
        let ci = &mut c_tile[i_off];
        for (j_off, bjk) in b.iter().enumerate() {
            let mut s = 0.0;
            for k in 0..kb {
                s += aik[k] * bjk[k];
            }
            ci[j_off] += alpha * s;
        }
    }
}

/// Parallel GEMM computing C := alpha * A * B + beta * C
/// Deterministic, resource-bounded: parallelizes over M-row tiles; each thread owns disjoint rows.
pub fn gemm(
    a: &Matrix,
    b: &Matrix,
    alpha: f64,
    c: Option<Matrix>,
    beta: f64,
    mb: usize,
    nb: usize,
    kb: usize,
) -> Result<Matrix, GemmError> {
    validate_matrix(a, "A")?;
    validate_matrix(b, "B")?;

    let (m, k) = get_size(a);
    let (k2, n) = get_size(b);

    if k != k2 {
        return Err(GemmError(format!(
            "Shape mismatch: A is ({},{}), B is ({},{}).",
            m, k, k2, n
        )));
    }

    let mut c = match c {
        None => zeros(m, n),
        Some(mut c_matrix) => {
            validate_matrix(&c_matrix, "C")?;
            let (m2, n2) = get_size(&c_matrix);
            if m2 != m || n2 != n {
                return Err(GemmError(format!(
                    "C has shape ({},{}); expected ({},{}).",
                    m2, n2, m, n
                )));
            }
            if beta != 1.0 {
                for i in 0..m {
                    for j in 0..n {
                        c_matrix[i][j] *= beta;
                    }
                }
            }
            c_matrix
        }
    };

    if alpha == 0.0 {
        return Ok(c);
    }

    let bt = transpose(b);

    // Small-N fallback: strict sequential order identical to baseline
    let total_ops = m * n * k;
    if total_ops <= 64 * 64 * 32 {
        let mut n0 = 0;
        while n0 < n {
            let n1 = (n0 + nb).min(n);
            let mut k0 = 0;
            while k0 < k {
                let k1 = (k0 + kb).min(k);
                let bpack = pack_matrix(&bt, k0, k1, n0, n1);
                let mut m0 = 0;
                while m0 < m {
                    let m1 = (m0 + mb).min(m);
                    let apack = pack_matrix(a, k0, k1, m0, m1);
                    let kb_len = k1 - k0;
                    for (i_off, aik) in apack.iter().enumerate() {
                        let ci = &mut c[m0 + i_off];
                        for (j_off, bjk) in bpack.iter().enumerate() {
                            let mut s = 0.0;
                            for kk in 0..kb_len {
                                s += aik[kk] * bjk[kk];
                            }
                            ci[n0 + j_off] += alpha * s;
                        }
                    }
                    m0 += mb;
                }
                k0 += kb;
            }
            n0 += nb;
        }
        return Ok(c);
    }

    // Parallel over M-row tiles
    let m_chunks = (m + mb - 1) / mb;

    let max_threads = std::thread::available_parallelism()
        .map(|n| n.get())
        .unwrap_or(1);
    let num_threads = max_threads.min(m_chunks.max(1));

    let chunks_per_thread = (m_chunks + num_threads - 1) / num_threads;

    // Prepare the deterministic bands of chunk indices
    let mut bands: Vec<(usize, usize)> = Vec::new();
    for t in 0..num_threads {
        let start_chunk = t * chunks_per_thread;
        let end_chunk = ((t + 1) * chunks_per_thread).min(m_chunks);
        if start_chunk < end_chunk {
            bands.push((start_chunk, end_chunk));
        }
    }

    let mut collected: Vec<(usize, Vec<f64>)> = Vec::with_capacity(m);

    thread::scope(|scope| {
        let mut handles = Vec::with_capacity(bands.len());
        for (start_chunk, end_chunk) in bands.iter().copied() {
            let a_ref = a;
            let bt_ref = &bt;
            let c_ref = &c; // read-only during thread scope
            let handle = scope.spawn(move || {
                let mut c_rows: Vec<Vec<f64>> = Vec::new();
                let mut row_indices: Vec<usize> = Vec::new();
                for chunk_idx in start_chunk..end_chunk {
                    let m0 = chunk_idx * mb;
                    let m1 = (m0 + mb).min(m);
                    for r in m0..m1 {
                        row_indices.push(r);
                        c_rows.push(c_ref[r].clone());
                    }
                }

                let mut offset = 0usize;
                for chunk_idx in start_chunk..end_chunk {
                    let m0 = chunk_idx * mb;
                    let m1 = (m0 + mb).min(m);
                    let rows_this_chunk = m1 - m0;

                    let mut n0 = 0usize;
                    while n0 < n {
                        let n1 = (n0 + nb).min(n);

                        let mut k0 = 0usize;
                        while k0 < k {
                            let k1 = (k0 + kb).min(k);
                            let apack = pack_matrix(a_ref, k0, k1, m0, m1);
                            let bpack = pack_matrix(bt_ref, k0, k1, n0, n1);
                            let kb_len = k1 - k0;
                            let mut tile = zeros(rows_this_chunk, n1 - n0);
                            partial_matmul_add_into(&apack, &bpack, &mut tile, alpha, kb_len);
                            for ii in 0..rows_this_chunk {
                                let row = &mut c_rows[offset + ii];
                                for jj in 0..(n1 - n0) {
                                    row[n0 + jj] += tile[ii][jj];
                                }
                            }
                            k0 += kb;
                        }
                        n0 += nb;
                    }

                    offset += rows_this_chunk;
                }
                (row_indices, c_rows)
            });
            handles.push(handle);
        }
        for h in handles {
            let (idxs, rows) = h.join().unwrap();
            for (i, r) in idxs.into_iter().zip(rows.into_iter()) {
                collected.push((i, r));
            }
        }
    });

    collected.sort_by_key(|(i, _)| *i);
    for (i, row) in collected.into_iter() {
        c[i] = row;
    }

    Ok(c)
}

/// Convenience function with default parameters
pub fn gemm_simple(a: &Matrix, b: &Matrix) -> Result<Matrix, GemmError> {
    gemm(a, b, 1.0, None, 0.0, 64, 64, 64)
}
