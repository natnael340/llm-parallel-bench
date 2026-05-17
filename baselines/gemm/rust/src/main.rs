/// Imports the parallel GEMM (General Matrix Multiply) implementation and utility functions.
///
/// # Imports
/// - `gemm_parallel` - Aliased as `gemm`, provides the parallel matrix multiplication function
/// - `zeros` - Utility function to create zero-initialized matrices
/// - `Matrix` - The matrix data structure type used in GEMM operations
use gemm::{gemm_parallel as gemm, zeros, Matrix};
use std::time::Instant;

static mut PASSED: u32 = 0;
static mut FAILED: u32 = 0;

fn main() {
    println!("Running GEMM Tests...\n");

    // Identity and basic tests
    test("Identity left multiplication", test_identity_left);
    test("Identity right multiplication", test_identity_right);
    test("Zero matrices yield zero", test_zero_matrices_yield_zero);

    // Alpha/Beta parameter tests
    test("Alpha zero with C=None", test_alpha_zero_with_c_none);
    test("Alpha zero with C, beta=1 preserves C", test_alpha_zero_with_c_beta_one_preserves_c);
    test("Alpha zero with beta scales once", test_alpha_zero_with_beta_scales_once);
    test("Beta zero ignores input C", test_beta_zero_ignores_input_c);
    test("Beta one accumulates into C", test_beta_one_accumulates_into_c);
    test("Negative alpha and beta", test_negative_alpha_and_beta);

    // Shape tests
    test("Rectangular tall skinny", test_rectangular_tall_skinny);
    test("Rectangular short fat", test_rectangular_short_fat);
    test("Single row times single column (scalar)", test_single_row_times_single_column);
    test("Row vector times matrix", test_row_vector_times_matrix);
    test("Matrix times column vector", test_matrix_times_column_vector);

    // General correctness tests
    test("General random compare reference", test_general_random_compare_reference);
    test("Not multiple of block sizes", test_not_multiple_of_block_sizes);
    test("Block sizes one matches naive", test_block_sizes_one_matches_naive);
    test("Block sizes larger than dims", test_block_sizes_larger_than_dims);

    // Validation tests
    test("Dimension mismatch raises", test_dimension_mismatch_raises);
    test("Invalid C shape raises", test_invalid_c_shape_raises);
    test("Ragged A rejected", test_ragged_a_rejected);
    test("Ragged B rejected", test_ragged_b_rejected);

    // Special values
    test("NaN propagation", test_nan_propagation);
    test("Infinity propagation", test_infinity_propagation);

    // Accumulation tests
    test("Repeat calls accumulate with beta=1", test_repeat_calls_accumulate_with_beta_one);
    test("Alpha scaling is linear", test_alpha_scaling_linear);

    // Performance test
    test("Performance speed test", test_performance_speed);

    // Summary
    unsafe {
        println!("\n========================================");
        println!("Results: {} passed, {} failed, {} total", PASSED, FAILED, PASSED + FAILED);
        println!("========================================");

        if FAILED > 0 {
            std::process::exit(1);
        }
    }
}

fn test<F>(name: &str, test_fn: F)
where
    F: FnOnce() -> Result<(), String>,
{
    match test_fn() {
        Ok(()) => {
            println!("[PASS] {}", name);
            unsafe { PASSED += 1; }
        }
        Err(msg) => {
            println!("[FAIL] {}", name);
            println!("       {}", msg);
            unsafe { FAILED += 1; }
        }
    }
}

// ==================== Helpers ====================

fn make_matrix(rows: usize, cols: usize, fill: f64) -> Matrix {
    vec![vec![fill; cols]; rows]
}

fn make_random_matrix(rows: usize, cols: usize, lo: f64, hi: f64, seed: u64) -> Matrix {
    let mut state = seed;
    let mut result = vec![vec![0.0; cols]; rows];
    for i in 0..rows {
        for j in 0..cols {
            // Simple LCG random number generator
            state = state.wrapping_mul(6364136223846793005).wrapping_add(1);
            let rand_val = ((state >> 33) as f64) / (u32::MAX as f64);
            result[i][j] = lo + rand_val * (hi - lo);
        }
    }
    result
}

fn make_identity(n: usize) -> Matrix {
    let mut result = make_matrix(n, n, 0.0);
    for i in 0..n {
        result[i][i] = 1.0;
    }
    result
}

fn deep_copy(matrix: &Matrix) -> Matrix {
    matrix.clone()
}

fn mat_almost_equal(x: &Matrix, y: &Matrix, tol: f64) -> Result<(), String> {
    if x.len() != y.len() {
        return Err(format!("Row count mismatch: {} vs {}", x.len(), y.len()));
    }
    if x[0].len() != y[0].len() {
        return Err(format!("Column count mismatch: {} vs {}", x[0].len(), y[0].len()));
    }
    for i in 0..x.len() {
        for j in 0..x[0].len() {
            let xv = x[i][j];
            let yv = y[i][j];
            if xv.is_nan() || yv.is_nan() {
                if !(xv.is_nan() && yv.is_nan()) {
                    return Err(format!("NaN mismatch at [{}][{}]: {} vs {}", i, j, xv, yv));
                }
            } else if (xv - yv).abs() > tol {
                return Err(format!(
                    "Value mismatch at [{}][{}]: {} vs {} (diff={})",
                    i, j, xv, yv, (xv - yv).abs()
                ));
            }
        }
    }
    Ok(())
}

fn naive_gemm(a: &Matrix, b: &Matrix, alpha: f64, c: Option<Matrix>, beta: f64) -> Matrix {
    let m = a.len();
    let k = a[0].len();
    let n = b[0].len();

    let mut c = match c {
        None => make_matrix(m, n, 0.0),
        Some(mut c_matrix) => {
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
        return c;
    }

    for i in 0..m {
        for kk in 0..k {
            let a_val = alpha * a[i][kk];
            if a_val == 0.0 {
                continue;
            }
            for j in 0..n {
                c[i][j] += a_val * b[kk][j];
            }
        }
    }
    c
}

// ==================== Tests ====================

fn test_identity_left() -> Result<(), String> {
    let m = 3;
    let n = 4;
    let i = make_identity(m);
    let b = make_random_matrix(m, n, -1.0, 1.0, 1);
    let out = gemm(&i, &b, 1.0, None, 0.0, 64, 64, 64).map_err(|e| e.to_string())?;
    mat_almost_equal(&out, &b, 1e-9)
}

fn test_identity_right() -> Result<(), String> {
    let m = 3;
    let k = 5;
    let n = k;
    let a = make_random_matrix(m, k, -1.0, 1.0, 2);
    let i = make_identity(n);
    let out = gemm(&a, &i, 1.0, None, 0.0, 64, 64, 64).map_err(|e| e.to_string())?;
    mat_almost_equal(&out, &a, 1e-9)
}

fn test_zero_matrices_yield_zero() -> Result<(), String> {
    let (m, k, n) = (4, 3, 5);
    let a = make_matrix(m, k, 0.0);
    let b = make_matrix(k, n, 0.0);
    let out = gemm(&a, &b, 1.0, None, 0.0, 64, 64, 64).map_err(|e| e.to_string())?;
    mat_almost_equal(&out, &make_matrix(m, n, 0.0), 1e-9)
}

fn test_alpha_zero_with_c_none() -> Result<(), String> {
    let (m, k, n) = (2, 3, 4);
    let a = make_random_matrix(m, k, -1.0, 1.0, 3);
    let b = make_random_matrix(k, n, -1.0, 1.0, 4);
    let out = gemm(&a, &b, 0.0, None, 0.0, 64, 64, 64).map_err(|e| e.to_string())?;
    mat_almost_equal(&out, &make_matrix(m, n, 0.0), 1e-9)
}

fn test_alpha_zero_with_c_beta_one_preserves_c() -> Result<(), String> {
    let (m, k, n) = (3, 3, 2);
    let a = make_random_matrix(m, k, -1.0, 1.0, 5);
    let b = make_random_matrix(k, n, -1.0, 1.0, 6);
    let c = make_random_matrix(m, n, -1.0, 1.0, 7);
    let c_copy = deep_copy(&c);
    let out = gemm(&a, &b, 0.0, Some(c), 1.0, 64, 64, 64).map_err(|e| e.to_string())?;
    mat_almost_equal(&out, &c_copy, 1e-9)
}

fn test_alpha_zero_with_beta_scales_once() -> Result<(), String> {
    let (m, k, n) = (3, 7, 4);
    let a = make_random_matrix(m, k, -1.0, 1.0, 8);
    let b = make_random_matrix(k, n, -1.0, 1.0, 9);
    let c = make_random_matrix(m, n, -1.0, 1.0, 10);
    let c_copy = deep_copy(&c);
    let beta = 2.5;
    let out = gemm(&a, &b, 0.0, Some(c), beta, 2, 3, 1).map_err(|e| e.to_string())?;
    let expected: Matrix = c_copy.iter().map(|row| row.iter().map(|&v| beta * v).collect()).collect();
    mat_almost_equal(&out, &expected, 1e-9)
}

fn test_beta_zero_ignores_input_c() -> Result<(), String> {
    let (m, k, n) = (4, 3, 5);
    let a = make_random_matrix(m, k, -1.0, 1.0, 11);
    let b = make_random_matrix(k, n, -1.0, 1.0, 12);
    let c = make_matrix(m, n, 7.0);
    let out = gemm(&a, &b, 1.0, Some(c), 0.0, 64, 64, 64).map_err(|e| e.to_string())?;
    let ref_mat = naive_gemm(&a, &b, 1.0, Some(make_matrix(m, n, 0.0)), 0.0);
    mat_almost_equal(&out, &ref_mat, 1e-9)
}

fn test_beta_one_accumulates_into_c() -> Result<(), String> {
    let (m, k, n) = (3, 4, 2);
    let a = make_random_matrix(m, k, -1.0, 1.0, 13);
    let b = make_random_matrix(k, n, -1.0, 1.0, 14);
    let c = make_random_matrix(m, n, -1.0, 1.0, 15);
    let c_ref = deep_copy(&c);
    let out = gemm(&a, &b, 0.5, Some(c), 1.0, 64, 64, 64).map_err(|e| e.to_string())?;
    let ref_mat = naive_gemm(&a, &b, 0.5, Some(c_ref), 1.0);
    mat_almost_equal(&out, &ref_mat, 1e-9)
}

fn test_negative_alpha_and_beta() -> Result<(), String> {
    let (m, k, n) = (2, 3, 2);
    let a = make_random_matrix(m, k, -1.0, 1.0, 16);
    let b = make_random_matrix(k, n, -1.0, 1.0, 17);
    let c = make_random_matrix(m, n, -1.0, 1.0, 18);
    let c_ref = deep_copy(&c);
    let out = gemm(&a, &b, -1.0, Some(c), -0.5, 64, 64, 64).map_err(|e| e.to_string())?;
    let ref_mat = naive_gemm(&a, &b, -1.0, Some(c_ref), -0.5);
    mat_almost_equal(&out, &ref_mat, 1e-9)
}

fn test_rectangular_tall_skinny() -> Result<(), String> {
    let (m, k, n) = (10, 2, 7);
    let a = make_random_matrix(m, k, -1.0, 1.0, 19);
    let b = make_random_matrix(k, n, -1.0, 1.0, 20);
    let out = gemm(&a, &b, 1.0, None, 0.0, 64, 64, 64).map_err(|e| e.to_string())?;
    let ref_mat = naive_gemm(&a, &b, 1.0, None, 0.0);
    mat_almost_equal(&out, &ref_mat, 1e-9)
}

fn test_rectangular_short_fat() -> Result<(), String> {
    let (m, k, n) = (3, 8, 20);
    let a = make_random_matrix(m, k, -1.0, 1.0, 21);
    let b = make_random_matrix(k, n, -1.0, 1.0, 22);
    let out = gemm(&a, &b, 1.0, None, 0.0, 2, 7, 3).map_err(|e| e.to_string())?;
    let ref_mat = naive_gemm(&a, &b, 1.0, None, 0.0);
    mat_almost_equal(&out, &ref_mat, 1e-9)
}

fn test_single_row_times_single_column() -> Result<(), String> {
    let (m, k, n) = (1, 5, 1);
    let a = make_random_matrix(m, k, -1.0, 1.0, 23);
    let b = make_random_matrix(k, n, -1.0, 1.0, 24);
    let out = gemm(&a, &b, 1.0, None, 0.0, 64, 64, 64).map_err(|e| e.to_string())?;
    let ref_mat = naive_gemm(&a, &b, 1.0, None, 0.0);
    mat_almost_equal(&out, &ref_mat, 1e-9)
}

fn test_row_vector_times_matrix() -> Result<(), String> {
    let (m, k, n) = (1, 6, 4);
    let a = make_random_matrix(m, k, -1.0, 1.0, 25);
    let b = make_random_matrix(k, n, -1.0, 1.0, 26);
    let out = gemm(&a, &b, 1.0, None, 0.0, 1, 3, 2).map_err(|e| e.to_string())?;
    let ref_mat = naive_gemm(&a, &b, 1.0, None, 0.0);
    mat_almost_equal(&out, &ref_mat, 1e-9)
}

fn test_matrix_times_column_vector() -> Result<(), String> {
    let (m, k, n) = (7, 5, 1);
    let a = make_random_matrix(m, k, -1.0, 1.0, 27);
    let b = make_random_matrix(k, n, -1.0, 1.0, 28);
    let out = gemm(&a, &b, 1.0, None, 0.0, 4, 1, 3).map_err(|e| e.to_string())?;
    let ref_mat = naive_gemm(&a, &b, 1.0, None, 0.0);
    mat_almost_equal(&out, &ref_mat, 1e-9)
}

fn test_general_random_compare_reference() -> Result<(), String> {
    let (m, k, n) = (9, 11, 8);
    let a = make_random_matrix(m, k, -1.0, 1.0, 29);
    let b = make_random_matrix(k, n, -1.0, 1.0, 30);
    let c = make_random_matrix(m, n, -1.0, 1.0, 31);
    let out = gemm(&a, &b, 1.2, Some(deep_copy(&c)), 0.7, 4, 5, 3).map_err(|e| e.to_string())?;
    let ref_mat = naive_gemm(&a, &b, 1.2, Some(c), 0.7);
    mat_almost_equal(&out, &ref_mat, 1e-9)
}

fn test_not_multiple_of_block_sizes() -> Result<(), String> {
    let (m, k, n) = (13, 17, 19);
    let a = make_random_matrix(m, k, -1.0, 1.0, 32);
    let b = make_random_matrix(k, n, -1.0, 1.0, 33);
    let out = gemm(&a, &b, 1.0, None, 0.0, 5, 6, 7).map_err(|e| e.to_string())?;
    let ref_mat = naive_gemm(&a, &b, 1.0, None, 0.0);
    mat_almost_equal(&out, &ref_mat, 1e-9)
}

fn test_block_sizes_one_matches_naive() -> Result<(), String> {
    let (m, k, n) = (5, 6, 4);
    let a = make_random_matrix(m, k, -1.0, 1.0, 34);
    let b = make_random_matrix(k, n, -1.0, 1.0, 35);
    let out = gemm(&a, &b, 1.0, None, 0.0, 1, 1, 1).map_err(|e| e.to_string())?;
    let ref_mat = naive_gemm(&a, &b, 1.0, None, 0.0);
    mat_almost_equal(&out, &ref_mat, 1e-9)
}

fn test_block_sizes_larger_than_dims() -> Result<(), String> {
    let (m, k, n) = (4, 3, 2);
    let a = make_random_matrix(m, k, -1.0, 1.0, 36);
    let b = make_random_matrix(k, n, -1.0, 1.0, 37);
    let out = gemm(&a, &b, 1.0, None, 0.0, 128, 128, 128).map_err(|e| e.to_string())?;
    let ref_mat = naive_gemm(&a, &b, 1.0, None, 0.0);
    mat_almost_equal(&out, &ref_mat, 1e-9)
}

fn test_dimension_mismatch_raises() -> Result<(), String> {
    let a = make_random_matrix(3, 4, -1.0, 1.0, 43);
    let b = make_random_matrix(5, 2, -1.0, 1.0, 44);
    match gemm(&a, &b, 1.0, None, 0.0, 64, 64, 64) {
        Err(_) => Ok(()),
        Ok(_) => Err("Expected error for dimension mismatch".to_string()),
    }
}

fn test_invalid_c_shape_raises() -> Result<(), String> {
    let a = make_random_matrix(3, 2, -1.0, 1.0, 45);
    let b = make_random_matrix(2, 4, -1.0, 1.0, 46);
    let c = make_random_matrix(2, 4, -1.0, 1.0, 47);
    match gemm(&a, &b, 1.0, Some(c), 0.0, 64, 64, 64) {
        Err(_) => Ok(()),
        Ok(_) => Err("Expected error for invalid C shape".to_string()),
    }
}

fn test_ragged_a_rejected() -> Result<(), String> {
    let a = vec![vec![1.0, 2.0], vec![3.0]];
    let b = make_random_matrix(2, 2, -1.0, 1.0, 48);
    match gemm(&a, &b, 1.0, None, 0.0, 64, 64, 64) {
        Err(_) => Ok(()),
        Ok(_) => Err("Expected error for ragged A".to_string()),
    }
}

fn test_ragged_b_rejected() -> Result<(), String> {
    let a = make_random_matrix(2, 2, -1.0, 1.0, 49);
    let b = vec![vec![1.0], vec![2.0, 3.0]];
    match gemm(&a, &b, 1.0, None, 0.0, 64, 64, 64) {
        Err(_) => Ok(()),
        Ok(_) => Err("Expected error for ragged B".to_string()),
    }
}

fn test_nan_propagation() -> Result<(), String> {
    let a = vec![vec![f64::NAN, 1.0], vec![2.0, 3.0]];
    let b = vec![vec![4.0, 5.0], vec![6.0, 7.0]];
    let out = gemm(&a, &b, 1.0, None, 0.0, 64, 64, 64).map_err(|e| e.to_string())?;
    if !out[0][0].is_nan() || !out[0][1].is_nan() {
        return Err("NaN should propagate".to_string());
    }
    Ok(())
}

fn test_infinity_propagation() -> Result<(), String> {
    let a = vec![vec![f64::INFINITY, 0.0], vec![0.0, 1.0]];
    let b = vec![vec![1.0, 2.0], vec![3.0, 4.0]];
    let out = gemm(&a, &b, 1.0, None, 0.0, 64, 64, 64).map_err(|e| e.to_string())?;
    if !out[0][0].is_infinite() || !out[0][1].is_infinite() {
        return Err("Infinity should propagate".to_string());
    }
    Ok(())
}

fn test_repeat_calls_accumulate_with_beta_one() -> Result<(), String> {
    let (m, k, n) = (3, 3, 3);
    let a = make_random_matrix(m, k, -1.0, 1.0, 51);
    let b = make_random_matrix(k, n, -1.0, 1.0, 52);
    let c = zeros(m, n);
    let c = gemm(&a, &b, 1.0, Some(c), 1.0, 64, 64, 64).map_err(|e| e.to_string())?;
    let c = gemm(&a, &b, 1.0, Some(c), 1.0, 64, 64, 64).map_err(|e| e.to_string())?;
    let ref_once = naive_gemm(&a, &b, 1.0, Some(make_matrix(m, n, 0.0)), 1.0);
    let ref_twice = naive_gemm(&a, &b, 1.0, Some(ref_once), 1.0);
    mat_almost_equal(&c, &ref_twice, 1e-9)
}

fn test_alpha_scaling_linear() -> Result<(), String> {
    let (m, k, n) = (4, 5, 3);
    let a = make_random_matrix(m, k, -1.0, 1.0, 53);
    let b = make_random_matrix(k, n, -1.0, 1.0, 54);
    let c1 = gemm(&a, &b, 1.0, None, 0.0, 64, 64, 64).map_err(|e| e.to_string())?;
    let s = 2.75;
    let c2 = gemm(&a, &b, s, None, 0.0, 64, 64, 64).map_err(|e| e.to_string())?;
    let scaled: Matrix = c1.iter().map(|row| row.iter().map(|&v| s * v).collect()).collect();
    mat_almost_equal(&c2, &scaled, 1e-9)
}

fn test_performance_speed() -> Result<(), String> {
    let (m, k, n) = (1024, 1024, 1024);
    let a = make_random_matrix(m, k, -1.0, 1.0, 10);
    let b = make_random_matrix(k, n, -1.0, 1.0, 12);

    // Warmup
    let _ = gemm(&a, &b, 1.0, None, 0.0, 32, 32, 32);

    let iters = 5;
    let reps = 3;
    let mut times = Vec::with_capacity(reps);

    for _ in 0..reps {
        let start = Instant::now();
        for _ in 0..iters {
            let _ = gemm(&a, &b, 1.0, None, 0.0, 32, 32, 128);
        }
        let duration = start.elapsed();
        times.push(duration.as_secs_f64() * 1000.0 / iters as f64);
    }

    let avg: f64 = times.iter().sum::<f64>() / times.len() as f64;
    let variance: f64 = times.iter().map(|t| (t - avg).powi(2)).sum::<f64>() / times.len() as f64;
    let sd = variance.sqrt();

    let avg_s = avg / 1000.0;
    let gflops = (2.0 * m as f64 * n as f64 * k as f64) / (avg_s * 1e9);

    println!("       (GEMM {}x{}x{}: {:.2} ms/run +/- {:.2}, {:.3} GFLOPs)", m, n, k, avg, sd, gflops);
    Ok(())
}
