mod gemm_sequential;
mod gemm_parallel;

use std::collections::hash_map::DefaultHasher;
use std::hash::{Hash, Hasher};
use std::time::Instant;
use std::fs::File;
use std::io::Write;
use std::thread;

type Matrix = Vec<Vec<f64>>;

fn hash_matrix(m: &Matrix) -> u64 {
    let mut hasher = DefaultHasher::new();
    for row in m {
        for &val in row {
            val.to_bits().hash(&mut hasher);
        }
    }
    hasher.finish()
}

fn matrices_equal(a: &Matrix, b: &Matrix) -> bool {
    if a.len() != b.len() {
        return false;
    }
    for i in 0..a.len() {
        if a[i].len() != b[i].len() {
            return false;
        }
        for j in 0..a[i].len() {
            if a[i][j] != b[i][j] {
                return false;
            }
        }
    }
    true
}

fn make_matrix(rows: usize, cols: usize, seed: u64) -> Matrix {
    let mut m = vec![vec![0.0; cols]; rows];
    let mut val = seed as f64;
    for i in 0..rows {
        for j in 0..cols {
            m[i][j] = (val % 100.0) / 10.0;
            val = (val * 1103515245.0 + 12345.0) % 2147483648.0;
        }
    }
    m
}

struct TestCase {
    name: String,
    m: usize,
    n: usize,
    k: usize,
    alpha: f64,
    beta: f64,
    mb: usize,
    nb: usize,
    kb: usize,
    use_c: bool,
}

fn run_test(tc: &TestCase) -> Result<(bool, Option<(u64, u64, u64)>), String> {
    let a = make_matrix(tc.m, tc.k, 42);
    let b = make_matrix(tc.k, tc.n, 123);
    let c_init = if tc.use_c {
        Some(make_matrix(tc.m, tc.n, 999))
    } else {
        None
    };

    // Sequential run
    let c_seq = gemm_sequential::gemm(
        &a,
        &b,
        tc.alpha,
        c_init.clone(),
        tc.beta,
        tc.mb,
        tc.nb,
        tc.kb,
    )
    .map_err(|e| format!("Sequential error: {}", e))?;

    // Parallel run 1
    let c_par1 = gemm_parallel::gemm(
        &a,
        &b,
        tc.alpha,
        c_init.clone(),
        tc.beta,
        tc.mb,
        tc.nb,
        tc.kb,
    )
    .map_err(|e| format!("Parallel error: {}", e))?;

    // Parallel run 2
    let c_par2 = gemm_parallel::gemm(
        &a,
        &b,
        tc.alpha,
        c_init.clone(),
        tc.beta,
        tc.mb,
        tc.nb,
        tc.kb,
    )
    .map_err(|e| format!("Parallel error: {}", e))?;

    // Parallel run 3
    let c_par3 = gemm_parallel::gemm(&a, &b, tc.alpha, c_init, tc.beta, tc.mb, tc.nb, tc.kb)
        .map_err(|e| format!("Parallel error: {}", e))?;

    // Check correctness
    let correct = matrices_equal(&c_seq, &c_par1);

    // Check determinism
    let h1 = hash_matrix(&c_par1);
    let h2 = hash_matrix(&c_par2);
    let h3 = hash_matrix(&c_par3);

    Ok((correct, Some((h1, h2, h3))))
}

fn run_perf_test(m: usize, n: usize, k: usize) -> Result<(f64, f64, f64), String> {
    let a = make_matrix(m, k, 42);
    let b = make_matrix(k, n, 123);
    let mb = 64;
    let nb = 64;
    let kb = 64;

    // Warmup
    let _ = gemm_sequential::gemm(&a, &b, 1.0, None, 0.0, mb, nb, kb);
    let _ = gemm_parallel::gemm(&a, &b, 1.0, None, 0.0, mb, nb, kb);

    // Sequential timing
    let start = Instant::now();
    let _ = gemm_sequential::gemm(&a, &b, 1.0, None, 0.0, mb, nb, kb)
        .map_err(|e| format!("Sequential error: {}", e))?;
    let t_seq = start.elapsed().as_secs_f64();

    // Parallel timing
    let start = Instant::now();
    let _ = gemm_parallel::gemm(&a, &b, 1.0, None, 0.0, mb, nb, kb)
        .map_err(|e| format!("Parallel error: {}", e))?;
    let t_par = start.elapsed().as_secs_f64();

    let speedup = t_seq / t_par;

    Ok((t_seq, t_par, speedup))
}

fn main() {
    let mut summary = String::new();
    let mut all_passed = true;

    println!("=== GEMM Differential Testing ===\n");

    let test_cases = vec![
        TestCase {
            name: "Empty edge case (1x1x1)".to_string(),
            m: 1,
            n: 1,
            k: 1,
            alpha: 1.0,
            beta: 0.0,
            mb: 32,
            nb: 32,
            kb: 32,
            use_c: false,
        },
        TestCase {
            name: "Small (4x4x4)".to_string(),
            m: 4,
            n: 4,
            k: 4,
            alpha: 1.0,
            beta: 0.0,
            mb: 2,
            nb: 2,
            kb: 2,
            use_c: false,
        },
        TestCase {
            name: "Small with beta (8x8x8)".to_string(),
            m: 8,
            n: 8,
            k: 8,
            alpha: 2.0,
            beta: 0.5,
            mb: 4,
            nb: 4,
            kb: 4,
            use_c: true,
        },
        TestCase {
            name: "Medium (64x64x64)".to_string(),
            m: 64,
            n: 64,
            k: 64,
            alpha: 1.0,
            beta: 0.0,
            mb: 16,
            nb: 16,
            kb: 16,
            use_c: false,
        },
        TestCase {
            name: "Medium rectangular (100x50x75)".to_string(),
            m: 100,
            n: 50,
            k: 75,
            alpha: 1.5,
            beta: 0.0,
            mb: 32,
            nb: 32,
            kb: 32,
            use_c: false,
        },
        TestCase {
            name: "Large (256x256x256)".to_string(),
            m: 256,
            n: 256,
            k: 256,
            alpha: 1.0,
            beta: 0.0,
            mb: 64,
            nb: 64,
            kb: 64,
            use_c: false,
        },
        TestCase {
            name: "Large rectangular (512x256x128)".to_string(),
            m: 512,
            n: 256,
            k: 128,
            alpha: 1.0,
            beta: 0.0,
            mb: 64,
            nb: 64,
            kb: 64,
            use_c: false,
        },
    ];

    summary.push_str("CORRECTNESS & DETERMINISM TESTS\n");
    summary.push_str("================================\n\n");

    for tc in &test_cases {
        print!("Testing: {} ... ", tc.name);
        match run_test(tc) {
            Ok((correct, hashes)) => {
                let (h1, h2, h3) = hashes.unwrap();
                let deterministic = h1 == h2 && h2 == h3;
                if correct && deterministic {
                    println!("✓ PASS");
                    summary.push_str(&format!(
                        "✓ {}\n  Correctness: PASS\n  Determinism: PASS (hash: {})\n\n",
                        tc.name, h1
                    ));
                } else {
                    println!("✗ FAIL");
                    all_passed = false;
                    if !correct {
                        summary.push_str(&format!(
                            "✗ {}\n  Correctness: FAIL (outputs differ)\n\n",
                            tc.name
                        ));
                    }
                    if !deterministic {
                        summary.push_str(&format!(
                            "✗ {}\n  Determinism: FAIL (hashes: {}, {}, {})\n\n",
                            tc.name, h1, h2, h3
                        ));
                    }
                }
            }
            Err(e) => {
                println!("✗ ERROR: {}", e);
                all_passed = false;
                summary.push_str(&format!("✗ {}\n  Error: {}\n\n", tc.name, e));
            }
        }
    }

    // Performance test
    println!("\n=== Performance Test ===\n");
    summary.push_str("\nPERFORMANCE TEST\n");
    summary.push_str("================\n\n");

    let perf_sizes = vec![(256, 256, 256), (512, 512, 512)];
    let num_cpus = thread::available_parallelism()
        .map(|n| n.get())
        .unwrap_or(4);

    for &(m, n, k) in &perf_sizes {
        print!("Performance test {}x{}x{} ... ", m, n, k);
        match run_perf_test(m, n, k) {
            Ok((t_seq, t_par, speedup)) => {
                println!("✓");
                println!("  Sequential: {:.4}s", t_seq);
                println!("  Parallel:   {:.4}s", t_par);
                println!("  Speedup:    {:.2}x", speedup);

                summary.push_str(&format!(
                    "Test {}x{}x{}:\n  t_seq: {:.4}s\n  t_par: {:.4}s\n  Speedup: {:.2}x\n\n",
                    m, n, k, t_seq, t_par, speedup
                ));

                // Write to perf.txt
                let mut perf_file = File::create("perf.txt").expect("Failed to create perf.txt");
                writeln!(
                    perf_file,
                    "GEMM Performance Test\n=====================\n"
                )
                .unwrap();
                writeln!(perf_file, "Matrix size: {}x{}x{}", m, n, k).unwrap();
                writeln!(perf_file, "Sequential time: {:.4}s", t_seq).unwrap();
                writeln!(perf_file, "Parallel time:   {:.4}s", t_par).unwrap();
                writeln!(perf_file, "Speedup:         {:.2}x", speedup).unwrap();
                writeln!(perf_file, "\nThreads: {} (bounded to CPU count)", num_cpus)
                    .unwrap();
            }
            Err(e) => {
                println!("✗ ERROR: {}", e);
                summary.push_str(&format!("✗ Performance test {}x{}x{}: {}\n\n", m, n, k, e));
            }
        }
    }

    // Write summary
    let mut summary_file = File::create("run_summary.txt").expect("Failed to create run_summary.txt");
    write!(summary_file, "{}", summary).unwrap();

    println!("\n=== Summary ===");
    if all_passed {
        println!("✓ All correctness and determinism tests PASSED");
        std::process::exit(0);
    } else {
        println!("✗ Some tests FAILED");
        std::process::exit(1);
    }
}
