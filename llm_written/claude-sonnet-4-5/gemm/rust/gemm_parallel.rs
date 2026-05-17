use std::sync::{Arc, Mutex};
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

fn get_num_threads() -> usize {
    thread::available_parallelism()
        .map(|n| n.get())
        .unwrap_or(4)
}

/// Compute C := alpha * A * B + beta * C
///
/// # Arguments
/// * `a` - m x k matrix
/// * `b` - k x n matrix
/// * `alpha` - Multiplier for A*B
/// * `c` - Optional m x n accumulation buffer (created if None)
/// * `beta` - Multiplier for existing C (applied only if C is provided)
/// * `mb` - Tile size for M dimension
/// * `nb` - Tile size for N dimension
/// * `kb` - Tile size for K dimension
///
/// # Returns
/// m x n result matrix (C)
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

    let c = match c {
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

    // Threshold for using parallel execution (avoid overhead for small matrices)
    const PARALLEL_THRESHOLD: usize = 128;
    let total_work = m * n;
    
    if total_work < PARALLEL_THRESHOLD * PARALLEL_THRESHOLD {
        // Sequential fallback for small matrices
        return gemm_sequential_internal(a, b, alpha, c, m, n, k, mb, nb, kb);
    }

    let bt = transpose(b);

    // Pre-compute all (n0, m0) tile coordinates
    let mut tile_coords = Vec::new();
    let mut n0 = 0;
    while n0 < n {
        let n1 = (n0 + nb).min(n);
        let mut m0 = 0;
        while m0 < m {
            let m1 = (m0 + mb).min(m);
            tile_coords.push((m0, m1, n0, n1));
            m0 += mb;
        }
        n0 += nb;
    }

    // Wrap C in Arc<Mutex> for safe concurrent access
    let c_shared = Arc::new(Mutex::new(c));
    let a_shared = Arc::new(a.clone());
    let bt_shared = Arc::new(bt);
    
    let num_threads = get_num_threads();
    let tiles_per_thread = (tile_coords.len() + num_threads - 1) / num_threads;
    
    let mut handles = vec![];
    
    for thread_id in 0..num_threads {
        let start_idx = thread_id * tiles_per_thread;
        if start_idx >= tile_coords.len() {
            break;
        }
        let end_idx = ((thread_id + 1) * tiles_per_thread).min(tile_coords.len());
        
        let thread_tiles: Vec<_> = tile_coords[start_idx..end_idx].to_vec();
        let a_ref = Arc::clone(&a_shared);
        let bt_ref = Arc::clone(&bt_shared);
        let c_ref = Arc::clone(&c_shared);
        
        let handle = thread::spawn(move || {
            for &(m0, m1, n0, n1) in &thread_tiles {
                // Allocate a local tile buffer for this worker
                let tile_rows = m1 - m0;
                let tile_cols = n1 - n0;
                let mut local_tile = vec![vec![0.0; tile_cols]; tile_rows];

                // Accumulate over k0 dimension sequentially (preserves determinism)
                let mut k0 = 0;
                while k0 < k {
                    let k1 = (k0 + kb).min(k);
                    let kb_len = k1 - k0;

                    let bpack = pack_matrix(&bt_ref, k0, k1, n0, n1);
                    let apack = pack_matrix(&a_ref, k0, k1, m0, m1);

                    // Compute into local tile (no shared state)
                    for (i_off, aik) in apack.iter().enumerate() {
                        for (j_off, bjk) in bpack.iter().enumerate() {
                            let mut s = 0.0;
                            for k_idx in 0..kb_len {
                                s += aik[k_idx] * bjk[k_idx];
                            }
                            local_tile[i_off][j_off] += alpha * s;
                        }
                    }

                    k0 += kb;
                }

                // Write local tile back to C (single lock per tile)
                let mut c_guard = c_ref.lock().unwrap();
                for i in 0..tile_rows {
                    for j in 0..tile_cols {
                        c_guard[m0 + i][n0 + j] += local_tile[i][j];
                    }
                }
            }
        });
        
        handles.push(handle);
    }
    
    // Wait for all threads to complete
    for handle in handles {
        handle.join().unwrap();
    }

    let c = Arc::try_unwrap(c_shared).unwrap().into_inner().unwrap();
    Ok(c)
}

// Sequential fallback for small matrices
fn gemm_sequential_internal(
    a: &Matrix,
    b: &Matrix,
    alpha: f64,
    mut c: Matrix,
    m: usize,
    n: usize,
    k: usize,
    mb: usize,
    nb: usize,
    kb: usize,
) -> Result<Matrix, GemmError> {
    let bt = transpose(b);
    
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
                
                // Inline partial_matmul
                for (i_off, aik) in apack.iter().enumerate() {
                    let ci = &mut c[m0 + i_off];
                    for (j_off, bjk) in bpack.iter().enumerate() {
                        let mut s = 0.0;
                        for k_idx in 0..kb_len {
                            s += aik[k_idx] * bjk[k_idx];
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

    Ok(c)
}
