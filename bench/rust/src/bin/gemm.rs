use bench_rust::bench_utils;
use bench_rust::staged::{bench_gemm, Matrix};

fn make_matrix(rows: usize, cols: usize, fill: f64) -> Matrix {
    vec![vec![fill; cols]; rows]
}

fn make_random_matrix(rows: usize, cols: usize, seed: u64) -> Matrix {
    // Simple deterministic LCG in [-1, 1); no external RNG dependency.
    let mut state = seed.wrapping_mul(6364136223846793005).wrapping_add(1442695040888963407);
    let mut next = || {
        state = state.wrapping_mul(6364136223846793005).wrapping_add(1442695040888963407);
        ((state >> 11) as f64 / (1u64 << 53) as f64) * 2.0 - 1.0
    };
    (0..rows).map(|_| (0..cols).map(|_| next()).collect()).collect()
}

fn naive_gemm(a: &Matrix, b: &Matrix) -> Matrix {
    let m = a.len();
    let k = a[0].len();
    let n = b[0].len();
    let mut c = make_matrix(m, n, 0.0);
    for i in 0..m {
        for kk in 0..k {
            let aik = a[i][kk];
            for j in 0..n {
                c[i][j] += aik * b[kk][j];
            }
        }
    }
    c
}

fn mat_almost_equal(x: &Matrix, y: &Matrix, tol: f64) -> bool {
    if x.len() != y.len() || x[0].len() != y[0].len() {
        return false;
    }
    for i in 0..x.len() {
        for j in 0..x[0].len() {
            if (x[i][j] - y[i][j]).abs() > tol {
                return false;
            }
        }
    }
    true
}

fn check(ok: bool, name: &str, failures: &mut i32) {
    println!("{} {}", name, if ok { "passed" } else { "failed" });
    if !ok {
        *failures += 1;
    }
}

fn main() {
    let mut failures = 0;

    // Identity left
    {
        let m = 3usize;
        let n = 4usize;
        let mut id = make_matrix(m, m, 0.0);
        for i in 0..m {
            id[i][i] = 1.0;
        }
        let b = make_random_matrix(m, n, 1);
        let out = bench_gemm(&id, &b, 1.0, None, 0.0, 64, 64, 64).expect("gemm failed");
        check(mat_almost_equal(&out, &b, 1e-9), "test_identity_left", &mut failures);
    }
    // Zero matrices
    {
        let (m, k, n) = (4usize, 3usize, 5usize);
        let a = make_matrix(m, k, 0.0);
        let b = make_matrix(k, n, 0.0);
        let out = bench_gemm(&a, &b, 1.0, None, 0.0, 64, 64, 64).expect("gemm failed");
        check(mat_almost_equal(&out, &make_matrix(m, n, 0.0), 1e-9), "test_zero", &mut failures);
    }
    // General random vs naive
    {
        let (m, k, n) = (9usize, 11usize, 8usize);
        let a = make_random_matrix(m, k, 29);
        let b = make_random_matrix(k, n, 30);
        let out = bench_gemm(&a, &b, 1.0, None, 0.0, 4, 5, 3).expect("gemm failed");
        check(mat_almost_equal(&out, &naive_gemm(&a, &b), 1e-9), "test_general_random", &mut failures);
    }
    // Block sizes larger than dims
    {
        let (m, k, n) = (4usize, 3usize, 2usize);
        let a = make_random_matrix(m, k, 36);
        let b = make_random_matrix(k, n, 37);
        let out = bench_gemm(&a, &b, 1.0, None, 0.0, 128, 128, 128).expect("gemm failed");
        check(mat_almost_equal(&out, &naive_gemm(&a, &b), 1e-9), "test_block_larger", &mut failures);
    }

    if failures > 0 {
        println!("{} test(s) failed — skipping benchmark", failures);
        std::process::exit(1);
    }

    // Perf: 1024x1024x1024.
    let (m, k, n) = (1024usize, 1024usize, 1024usize);
    // Per-language sweep-tuned tile sizes (see analysis/data/gemm sweep CSVs).
    let (mb, nb, kb) = (32usize, 32usize, 64usize);
    let a = make_random_matrix(m, k, 10);
    let b = make_random_matrix(k, n, 12);

    let reps = bench_utils::reps(5);
    let iters = bench_utils::iters(5);
    let r = bench_utils::run_benchmark(
        || {
            bench_gemm(&a, &b, 1.0, None, 0.0, mb, nb, kb).expect("gemm failed");
        },
        reps,
        iters,
        1,
    );

    let gflops = (2.0 * m as f64 * n as f64 * k as f64) / ((r.mean / 1000.0) * 1e9);
    println!(
        "{}",
        bench_utils::format_result(&format!("GEMM {}x{}x{} ({:.3} GFLOPs)", m, n, k, gflops), &r)
    );
    let params = format!(
        "{{\"m\": {}, \"n\": {}, \"k\": {}, \"MB\": {}, \"NB\": {}, \"KB\": {}}}",
        m, n, k, mb, nb, kb
    );
    bench_utils::write_result(&r, "gemm", &bench_utils::impl_name(), &params);
}
