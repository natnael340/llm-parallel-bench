use std::fs::File;
use std::io::Write;
use std::time::{Duration, Instant};

use crate::algo_parallel::par::Graph as ParGraph;
use crate::algo_sequential::seq::Graph as SeqGraph;

pub fn main() {
    // Edge/small/medium/large cases
    let cases = vec![
        (0usize, 0.0, 42u64),
        (1, 0.0, 123),
        (8, 0.2, 7),
        (200, 0.05, 111),
        (2000, 0.02, 999),
    ];

    let mut all_ok = true;
    let mut summary_lines: Vec<String> = Vec::new();

    for (n, _dens, _seed) in cases {
        println!("\nCASE n={}", n);
        let mut g_seq = SeqGraph::with_verbose(n, false);
        // Keep simple ring to ensure every node is in one SCC
        for i in 0..n { let j = (i + 1) % n; if n > 0 { g_seq.add_edge(i, j); } }
        let base = Instant::now();
        let seq_edges = g_seq.reduce_edges();
        let t_seq = base.elapsed();

        // Mirror to parallel graph
        let mut g_par = ParGraph::with_verbose(n, false);
        for u in 0..n { for &v in g_seq.neighbors(u) { g_par.add_edge(u, v); } }

        // Determinism: run 3 times
        let mut hashes = Vec::new();
        let mut t_par = Duration::from_millis(0);
        for _ in 0..3 {
            let st = Instant::now();
            let par_edges = g_par.reduce_edges_parallel();
            t_par += st.elapsed();
            hashes.push(hash_edges(&par_edges));
            assert_eq!(seq_edges, par_edges, "Mismatch vs baseline for n={}", n);
        }
        let h0 = hashes[0];
        let det_ok = hashes.iter().all(|&h| h == h0);
        println!("determinism hash: {:x} -> {}", h0, det_ok);
        println!("t_seq={:?} t_par_avg={:?}", t_seq, t_par/3);
        all_ok &= det_ok;
        summary_lines.push(format!("n={} det_ok={} t_seq_ms={:.3} t_par_avg_ms={:.3} hash={:x}",
                                   n, det_ok, dur_ms(t_seq), dur_ms(t_par/3), h0));
    }

    // Perf large benchmark
    let n = 5000; // keep below recursion limits of Tarjan
    println!("\nPERF n={}", n);
    let mut g_seq = SeqGraph::with_verbose(n, false);
    for i in 0..n { g_seq.add_edge(i, (i+1)%n); }
    let seq_t0 = Instant::now();
    let seq_edges = g_seq.reduce_edges();
    let t_seq = seq_t0.elapsed();

    let mut g_par = ParGraph::with_verbose(n, false);
    for u in 0..n { for &v in g_seq.neighbors(u) { g_par.add_edge(u, v); } }
    let par_t0 = Instant::now();
    let par_edges = g_par.reduce_edges_parallel();
    let t_par = par_t0.elapsed();
    assert_eq!(seq_edges, par_edges);
    let speedup = t_seq.as_secs_f64() / t_par.as_secs_f64();
    println!("speedup: {:.3}x", speedup);

    // Write summaries
    let mut run_summary = File::create("run_summary.txt").unwrap();
    writeln!(run_summary, "cases:").unwrap();
    for line in &summary_lines { writeln!(run_summary, "{}", line).unwrap(); }
    writeln!(run_summary, "ALL_OK={}", all_ok).unwrap();

    let mut perf = File::create("perf.txt").unwrap();
    writeln!(perf, "n={} t_seq_ms={:.3} t_par_ms={:.3} speedup={:.3}", n, dur_ms(t_seq), dur_ms(t_par), speedup).unwrap();

    if all_ok { println!("ALL TESTS PASSED"); }
}

fn dur_ms(d: Duration) -> f64 { d.as_secs_f64() * 1000.0 }

fn hash_edges(edges: &[(usize, usize)]) -> u64 {
    // Order-sensitive simple hash (FNV-1a style)
    let mut h: u64 = 1469598103934665603;
    for &(a, b) in edges {
        h ^= a as u64; h = h.wrapping_mul(1099511628211);
        h ^= b as u64; h = h.wrapping_mul(1099511628211);
    }
    h
}
