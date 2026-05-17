// Simple differential tester and perf runner for Smith-Waterman (sequential vs parallel)
use std::time::Instant;

mod algo_seq { include!("algo_sequential.rs"); }
mod algo_par { include!("algo_parallel.rs"); }

fn random_dna(n: usize) -> String {
    // simple deterministic generator
    let bases = ['A','C','G','T'];
    let mut s = String::with_capacity(n);
    let mut x: u64 = 0x9E3779B97F4A7C15; // golden ratio seed
    for i in 0..n { x ^= x << 7; x ^= x >> 9; x ^= 0xA5A5A5A5A5A5A5A5; s.push(bases[(x as usize + i) & 3]); }
    s
}

fn hash_matrix(h: &Vec<Vec<i32>>) -> u64 {
    // simple mixing for determinism check
    let mut x: u64 = 1469598103934665603; // FNV offset
    for row in h {
        for &v in row {
            x ^= v as u64; x = x.wrapping_mul(1099511628211);
        }
    }
    x
}

fn main() {
    let sw_seq = algo_seq::SmithWaterman::new(2, -1, -1);
    let sw_par = algo_par::SmithWaterman::new(2, -1, -1);

    let cases = vec![
        ("", ""),
        ("A", ""),
        ("", "G"),
        ("A", "A"),
        ("ACGT", "ACCT"),
        ("GATTACA", "GCATGCU"),
        (random_dna(200), random_dna(210)),
        (random_dna(1200), random_dna(1300)),
    ];

    let mut all_ok = true;
    let mut summary = String::new();

    for (idx, (a,b)) in cases.iter().enumerate() {
        let h_seq = sw_seq.construct_matrix(a, b);
        let r_seq = sw_seq.traceback(&h_seq, a, b);

        let h_par1 = sw_par.construct_matrix(a, b);
        let r_par1 = sw_par.traceback(&h_par1, a, b);

        let h_par2 = sw_par.construct_matrix(a, b);
        let r_par2 = sw_par.traceback(&h_par2, a, b);

        let ok = h_seq == h_par1 && r_seq.aligned_a == r_par1.aligned_a && r_seq.aligned_b == r_par1.aligned_b && r_seq.score == r_par1.score && ((r_seq.identity - r_par1.identity).abs() < 1e-12);
        let det_ok = h_par1 == h_par2 && r_par1.aligned_a == r_par2.aligned_a && r_par1.aligned_b == r_par2.aligned_b && r_par1.score == r_par2.score && ((r_par1.identity - r_par2.identity).abs() < 1e-12);

        all_ok &= ok && det_ok;
        summary.push_str(&format!("Case {}: parity={} determinism={}\n", idx, ok, det_ok));
    }

    // Perf check on bigger input
    let big_a = random_dna(4000); let big_b = random_dna(4000);
    let t0 = Instant::now(); let _ = sw_seq.construct_matrix(&big_a, &big_b); let dt_seq = t0.elapsed().as_secs_f64();
    let t1 = Instant::now(); let _ = sw_par.construct_matrix(&big_a, &big_b); let dt_par = t1.elapsed().as_secs_f64();
    let speedup = dt_seq / dt_par.max(1e-9);

    summary.push_str(&format!("Perf N=4000x4000: t_seq={:.3}s t_par={:.3}s speedup={:.2}x\n", dt_seq, dt_par, speedup));

    std::fs::create_dir_all("evidence").ok();
    std::fs::write("evidence/run_summary.txt", &summary).ok();
    std::fs::write("evidence/perf.txt", format!("N=4000x4000 t_seq={:.6} t_par={:.6} speedup={:.3}", dt_seq, dt_par, speedup)).ok();

    println!("{}", summary);

    if !all_ok { std::process::exit(1); }
    // soft perf gate; do not fail run if no speedup (e.g., sandbox)
}
