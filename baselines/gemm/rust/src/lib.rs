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

fn partial_matmul(
    a: &Matrix,
    b: &Matrix,
    c: &mut Matrix,
    alpha: f64,
    m0: usize,
    n0: usize,
    kb: usize,
) {
    for (i_off, aik) in a.iter().enumerate() {
        let ci = &mut c[m0 + i_off];
        for (j_off, bjk) in b.iter().enumerate() {
            let mut s = 0.0;
            for k in 0..kb {
                s += aik[k] * bjk[k];
            }
            ci[n0 + j_off] += alpha * s;
        }
    }
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
                partial_matmul(&apack, &bpack, &mut c, alpha, m0, n0, kb_len);

                m0 += mb;
            }
            k0 += kb;
        }
        n0 += nb;
    }

    Ok(c)
}

