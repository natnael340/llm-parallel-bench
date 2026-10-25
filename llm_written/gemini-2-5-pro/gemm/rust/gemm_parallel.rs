// To run this code, you need a Rust environment and Cargo with 'rayon' dependency.
// Assuming 'rayon' is available in the environment.
// Command: cargo run --release

use rayon::prelude::*;
use std::time::Instant;
use std::fs::File;
use std::io::Write;
use std::error::Error;

// --- Data Structures and Error Handling ---

pub type Matrix = Vec<Vec<f64>>;

#[derive(Debug)]
pub struct GemmError(pub String);

impl std::fmt::Display for GemmError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "{}", self.0)
    }
}

impl Error for GemmError {}

// --- Matrix Utilities ---

pub fn get_size(matrix: &Matrix) -> (usize, usize) {
    if matrix.is_empty() {
        return (0, 0);
    }
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
    let (rows, cols) = get_size(matrix);
    if rows == 0 || cols == 0 {
        return vec![];
    }
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

// --- Sequential GEMM Implementation (Baseline) ---

fn partial_matmul_sequential(
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

pub fn gemm_sequential(
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

    let mut c_out = match c {
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
        return Ok(c_out);
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
                partial_matmul_sequential(&apack, &bpack, &mut c_out, alpha, m0, n0, kb_len);
                m0 += mb;
            }
            k0 += kb;
        }
        n0 += nb;
    }

    Ok(c_out)
}

// --- Parallel GEMM Implementation ---

pub fn gemm_parallel(
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
    
    // Fallback for small matrices where parallel overhead isn't worth it.
    if m < mb * 2 || n < nb * 2 {
        return gemm_sequential(a, b, alpha, c, beta, mb, nb, kb);
    }

    let mut c_out = match c {
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
                c_matrix.par_iter_mut().for_each(|row| {
                    for val in row {
                        *val *= beta;
                    }
                });
            }
            c_matrix
        }
    };

    if alpha == 0.0 {
        return Ok(c_out);
    }

    let bt = transpose(b);

    let mut n0 = 0;
    while n0 < n {
        let n1 = (n0 + nb).min(n);
        let mut k0 = 0;
        while k0 < k {
            let k1 = (k0 + kb).min(k);
            let bpack = pack_matrix(&bt, k0, k1, n0, n1);
            let kb_len = k1 - k0;

            c_out
                .par_chunks_mut(mb)
                .enumerate()
                .for_each(|(m_chunk_idx, c_chunk)| {
                    let m0 = m_chunk_idx * mb;
                    let m1 = (m0 + c_chunk.len()).min(m);
                    let apack = pack_matrix(a, k0, k1, m0, m1);
                    
                    // Inlined partial_matmul logic
                    for (i_off, aik) in apack.iter().enumerate() {
                        let ci = &mut c_chunk[i_off];
                        for (j_off, bjk) in bpack.iter().enumerate() {
                            let mut s = 0.0;
                            for k_inner in 0..kb_len {
                                s += aik[k_inner] * bjk[k_inner];
                            }
                            ci[n0 + j_off] += alpha * s;
                        }
                    }
                });
            
            k0 += kb;
        }
        n0 += nb;
    }

    Ok(c_out)
}


// --- Test Harness (No external dependencies) ---

fn deterministic_matrix(rows: usize, cols: usize, seed: f64) -> Matrix {
    (0..rows)
        .map(|i| {
            (0..cols)
                .map(|j| {
                    let val = (i as f64 * 1.1 + j as f64 * 0.7 + seed).sin();
                    (val * 100.0).round() / 100.0 // Keep precision reasonable
                })
                .collect()
        })
        .collect()
}

fn are_matrices_equal(a: &Matrix, b: &Matrix, tolerance: f64) -> bool {
    let (r1, c1) = get_size(a);
    let (r2, c2) = get_size(b);
    if r1 != r2 || c1 != c2 {
        return false;
    }
    for i in 0..r1 {
        for j in 0..c1 {
            if (a[i][j] - b[i][j]).abs() > tolerance {
                eprintln!("Mismatch at ({},{}): a = {}, b = {}", i, j, a[i][j], b[i][j]);
                return false;
            }
        }
    }
    true
}

fn main() -> Result<(), Box<dyn Error>> {
    let mut summary = String::new();
    let mut perf_results = String::new();

    println!("Running Correctness Tests...");
    summary.push_str("--- Correctness Tests ---\n");

    let tests = vec![
        ("Edge Case (1x1)", 1, 1, 1),
        ("Small (10x10)", 10, 10, 10),
        ("Rectangular (32x64x16)", 32, 64, 16),
        ("Medium (128x128)", 128, 128, 128),
        ("Large (512x512)", 512, 512, 512),
    ];

    let mut all_correctness_passed = true;
    for (name, m, k, n) in tests {
        let a = deterministic_matrix(m, k, 42.0);
        let b = deterministic_matrix(k, n, 43.0);

        let sequential_result = gemm_sequential(&a, &b, 1.0, None, 0.0, 64, 64, 64)?;
        let parallel_result = gemm_parallel(&a, &b, 1.0, None, 0.0, 64, 64, 64)?;

        let passed = are_matrices_equal(&sequential_result, &parallel_result, 1e-9);
        let status = if passed { "PASS" } else { "FAIL" };
        println!("[{}] {}: {}x{} * {}x{}", status, name, m, k, k, n);
        summary.push_str(&format!("[{}] {}: {}x{} * {}x{}\n", status, name, m, k, k, n));
        if !passed {
            all_correctness_passed = false;
        }
    }

    if !all_correctness_passed {
        println!("\nCorrectness tests failed. Aborting further tests.");
        summary.push_str("\nCorrectness tests failed. Aborting further tests.\n");
        let mut file = File::create("run_summary.txt")?;
        file.write_all(summary.as_bytes())?;
        return Ok(());
    }

    println!("\nRunning Determinism Tests...");
    summary.push_str("\n--- Determinism Tests ---\n");
    let m_det = 256;
    let k_det = 256;
    let n_det = 256;
    let a_det = deterministic_matrix(m_det, k_det, 101.0);
    let b_det = deterministic_matrix(k_det, n_det, 102.0);

    let res1 = gemm_parallel(&a_det, &b_det, 1.0, None, 0.0, 64, 64, 64)?;
    let res2 = gemm_parallel(&a_det, &b_det, 1.0, None, 0.0, 64, 64, 64)?;

    let passed = are_matrices_equal(&res1, &res2, 0.0); // Exact match for determinism
    let status = if passed { "PASS" } else { "FAIL" };
    println!("[{}] Determinism ({}x{})", status, m_det, n_det);
    summary.push_str(&format!("[{}] Determinism ({}x{}): Exact match\n", status, m_det, n_det));

    println!("\nRunning Performance Test...");
    summary.push_str("\n--- Performance Test ---\n");
    perf_results.push_str("--- Performance Test ---\n");

    let m_perf = 1024;
    let k_perf = 1024;
    let n_perf = 1024;
    let mb = 64;
    let nb = 64;
    let kb = 64;
    println!("Matrix size: {}x{} * {}x{}", m_perf, k_perf, k_perf, n_perf);
    println!("Tile size: mb={}, nb={}, kb={}", mb, nb, kb);

    let a_perf = deterministic_matrix(m_perf, k_perf, 201.0);
    let b_perf = deterministic_matrix(k_perf, n_perf, 202.0);

    let start_seq = Instant::now();
    let _ = gemm_sequential(&a_perf, &b_perf, 1.0, None, 0.0, mb, nb, kb)?;
    let dur_seq = start_seq.elapsed();

    let start_par = Instant::now();
    let _ = gemm_parallel(&a_perf, &b_perf, 1.0, None, 0.0, mb, nb, kb)?;
    let dur_par = start_par.elapsed();

    let speedup = dur_seq.as_secs_f64() / dur_par.as_secs_f64();
    let num_threads = rayon::current_num_threads();
    let efficiency = if num_threads > 0 { speedup / num_threads as f64 } else { 0.0 };

    println!("Sequential time: {:.4}s", dur_seq.as_secs_f64());
    println!("Parallel time:   {:.4}s", dur_par.as_secs_f64());
    println!("Threads used:    {}", num_threads);
    println!("Speedup:         {:.2}x", speedup);
    println!("Efficiency:      {:.2}%", efficiency * 100.0);

    let perf_line = format!(
        "N={}: t_seq={:.4}s, t_par={:.4}s, speedup={:.2}x, threads={}, efficiency={:.2}%",
        n_perf, dur_seq.as_secs_f64(), dur_par.as_secs_f64(), speedup, num_threads, efficiency * 100.0
    );
    summary.push_str(&perf_line);
    summary.push_str("\n");
    perf_results.push_str(&perf_line);
    perf_results.push_str("\n");

    let mut summary_file = File::create("run_summary.txt")?;
    summary_file.write_all(summary.as_bytes())?;
    
    let mut perf_file = File::create("perf.txt")?;
    perf_file.write_all(perf_results.as_bytes())?;

    println!("\nTests finished. Results saved to run_summary.txt and perf.txt.");
    Ok(())
}
