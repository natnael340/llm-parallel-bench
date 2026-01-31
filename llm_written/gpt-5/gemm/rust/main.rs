mod algo_seq;
mod algo_parallel;

use std::fs::File;
use std::io::Write;
use std::time::Instant;

use algo_seq as seq;
use algo_parallel as par;

type Matrix = Vec<Vec<f64>>;

struct PRNG { state: u64 }
impl PRNG {
    fn new(seed: u64) -> Self { Self { state: seed | 1 } }
    fn next_u64(&mut self) -> u64 {
        // xorshift64*
        let mut x = self.state;
        x ^= x >> 12;
        x ^= x << 25;
        x ^= x >> 27;
        self.state = x;
        x.wrapping_mul(2685821657736338717)
    }
    fn next_f64(&mut self) -> f64 {
        // Map to [-1, 1]
        let v = self.next_u64() >> 11; // 53 bits
        let f = (v as f64) / ((1u64 << 53) as f64); // [0,1)
        2.0 * f - 1.0
    }
}

fn gen_matrix(m: usize, n: usize, seed: u64) -> Matrix {
    let mut rng = PRNG::new(seed);
    let mut a = Vec::with_capacity(m);
    for _ in 0..m {
        let mut row = Vec::with_capacity(n);
        for _ in 0..n {
            row.push(rng.next_f64());
        }
        a.push(row);
    }
    a
}

fn fnv1a_hash_matrix(mat: &Matrix) -> u64 {
    let mut h: u64 = 1469598103934665603;
    const P: u64 = 1099511628211;
    for row in mat {
        for &x in row {
            let bits = x.to_bits();
            h ^= bits;
            h = h.wrapping_mul(P);
        }
        // row separator to avoid ambiguity
        h ^= 0x9e3779b97f4a7c15;
        h = h.wrapping_mul(P);
    }
    h
}

fn check_equal(a: &Matrix, b: &Matrix) -> bool {
    if a.len() != b.len() { return false; }
    for (ra, rb) in a.iter().zip(b.iter()) {
        if ra.len() != rb.len() { return false; }
        for (&xa, &xb) in ra.iter().zip(rb.iter()) {
            if xa.to_bits() != xb.to_bits() { return false; }
        }
    }
    true
}

struct Case { m: usize, k: usize, n: usize, alpha: f64, with_c: bool, beta: f64 }

fn run_case(case: &Case, repeat: usize) -> Result<(bool, String), String> {
    let a = gen_matrix(case.m, case.k, 123);
    let b = gen_matrix(case.k, case.n, 456);

    let c_init = if case.with_c { Some(gen_matrix(case.m, case.n, 789)) } else { None };

    let seq_start = Instant::now();
    let seq_out = seq::gemm(&a, &b, case.alpha, c_init.clone(), case.beta, 64, 64, 64)
        .map_err(|e| e.to_string())?;
    let t_seq = seq_start.elapsed();

    // First parallel run
    let par_start = Instant::now();
    let par_out1 = par::gemm(&a, &b, case.alpha, c_init.clone(), case.beta, 64, 64, 64)
        .map_err(|e| e.to_string())?;
    let t_par1 = par_start.elapsed();

    if !check_equal(&seq_out, &par_out1) {
        return Ok((false, format!("Mismatch on first run: seq_hash={} par_hash={}", fnv1a_hash_matrix(&seq_out), fnv1a_hash_matrix(&par_out1))));
    }

    let mut det_ok = true;
    let hash_ref = fnv1a_hash_matrix(&par_out1);
    let mut last_time = t_par1;
    for _ in 1..repeat {
        let start = Instant::now();
        let out = par::gemm(&a, &b, case.alpha, c_init.clone(), case.beta, 64, 64, 64)
            .map_err(|e| e.to_string())?;
        last_time = start.elapsed();
        if fnv1a_hash_matrix(&out) != hash_ref { det_ok = false; break; }
        if !check_equal(&par_out1, &out) { det_ok = false; break; }
    }

    let summary = format!(
        "m={} k={} n={} alpha={} with_c={} beta={} | t_seq={:.3} ms, t_par≈{:.3} ms, det={}",
        case.m, case.k, case.n, case.alpha, case.with_c, case.beta, 
        t_seq.as_secs_f64()*1000.0, last_time.as_secs_f64()*1000.0, det_ok
    );
    Ok((det_ok, summary))
}

fn main() {
    let mut summary = String::new();

    let cases = vec![
        Case{ m:1, k:1, n:1, alpha:1.0, with_c:false, beta:0.0 },
        Case{ m:1, k:3, n:2, alpha:1.0, with_c:true, beta:0.5 },
        Case{ m:4, k:5, n:3, alpha:0.7, with_c:false, beta:0.0 },
        Case{ m:64, k:64, n:64, alpha:1.0, with_c:false, beta:0.0 },
    ];

    let mut all_ok = true;
    for case in &cases {
        match run_case(case, 3) {
            Ok((det_ok, line)) => {
                summary.push_str(&format!("{}\n", line));
                all_ok &= det_ok;
            },
            Err(e) => {
                summary.push_str(&format!("Case failed: {:?}\n", e));
                all_ok = false;
            }
        }
    }

    // Performance smoke test on a larger size (may be adjusted in CI)
    let perf_case = Case{ m:256, k:256, n:256, alpha:1.0, with_c:false, beta:0.0 };
    // warmup
    let _ = run_case(&perf_case, 1);
    // timed
    let a = gen_matrix(perf_case.m, perf_case.k, 42);
    let b = gen_matrix(perf_case.k, perf_case.n, 43);

    let t0 = Instant::now();
    let _ = seq::gemm(&a, &b, 1.0, None, 0.0, 64, 64, 64).unwrap();
    let t_seq = t0.elapsed();

    let t1 = Instant::now();
    let _ = par::gemm(&a, &b, 1.0, None, 0.0, 64, 64, 64).unwrap();
    let t_par = t1.elapsed();

    let speedup = t_seq.as_secs_f64() / t_par.as_secs_f64();

    let perf_str = format!(
        "perf N=256: t_seq={:.3} ms, t_par={:.3} ms, speedup={:.2}x\n",
        t_seq.as_secs_f64()*1000.0, t_par.as_secs_f64()*1000.0, speedup
    );

    // Write files
    let mut f = File::create("run_summary.txt").expect("write summary");
    f.write_all(summary.as_bytes()).unwrap();
    f.flush().ok();

    let mut p = File::create("perf.txt").expect("write perf");
    p.write_all(perf_str.as_bytes()).unwrap();
    p.flush().ok();

    println!("Test summary:\n{}\n{}\nAll OK: {}", summary, perf_str, all_ok);

    if !all_ok {
        std::process::exit(1);
    }
}
