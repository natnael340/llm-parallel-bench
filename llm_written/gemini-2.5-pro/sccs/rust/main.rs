
mod algo_sequential;
mod algo_parallel;

use rand::{Rng, SeedableRng};
use rand::rngs::StdRng;
use std::collections::hash_map::DefaultHasher;
use std::hash::{Hash, Hasher};
use std::time::Instant;

// Helper function to sort edges for consistent comparison
fn sort_edges(edges: &mut Vec<(usize, usize)>) {
    edges.sort_unstable();
}

// Helper function to compare two vectors of edges as multisets
fn compare_edge_multisets(mut seq_edges: Vec<(usize, usize)>, mut par_edges: Vec<(usize, usize)>) -> bool {
    sort_edges(&mut seq_edges);
    sort_edges(&mut par_edges);
    seq_edges == par_edges
}

// Helper to calculate hash of a vector of edges
fn hash_edges(edges: &mut Vec<(usize, usize)>) -> u64 {
    sort_edges(edges);
    let mut hasher = DefaultHasher::new();
    edges.hash(&mut hasher);
    hasher.finish()
}

struct TestResult {
    name: String,
    correctness: bool,
    determinism: Option<bool>,
    seq_time: f64,
    par_time: f64,
    par_time_2: Option<f64>,
    speedup: f64,
}

fn main() {
    let mut results = Vec::new();

    println!("Running correctness and determinism tests...");

    // Test 1: Empty graph
    let g_seq = algo_sequential::Graph::new(0);
    let g_par = algo_parallel::Graph::new(0);
    let seq_res = g_seq.reduce_edges();
    let par_res = g_par.reduce_edges();
    results.push(TestResult {
        name: "Empty Graph".to_string(),
        correctness: compare_edge_multisets(seq_res, par_res),
        determinism: None, seq_time: 0.0, par_time: 0.0, par_time_2: None, speedup: 1.0,
    });
    
    // Test 2: Simple cycle
    let mut g_seq = algo_sequential::Graph::new(3);
    let mut g_par = algo_parallel::Graph::new(3);
    g_seq.add_edge(0, 1); g_seq.add_edge(1, 2); g_seq.add_edge(2, 0);
    g_par.add_edge(0, 1); g_par.add_edge(1, 2); g_par.add_edge(2, 0);
    let seq_res = g_seq.reduce_edges();
    let par_res = g_par.reduce_edges();
    results.push(TestResult {
        name: "Simple Cycle".to_string(),
        correctness: compare_edge_multisets(seq_res, par_res),
        determinism: None, seq_time: 0.0, par_time: 0.0, par_time_2: None, speedup: 1.0,
    });

    // Test 3: Multiple SCCs
    let mut g_seq = algo_sequential::Graph::new(5);
    let mut g_par = algo_parallel::Graph::new(5);
    let edges = [(0, 1), (1, 2), (2, 0), (3, 4), (4, 3), (2, 3)];
    for &(u, v) in &edges {
        g_seq.add_edge(u, v);
        g_par.add_edge(u, v);
    }
    let seq_res = g_seq.reduce_edges();
    let par_res = g_par.reduce_edges();
    results.push(TestResult {
        name: "Multiple SCCs".to_string(),
        correctness: compare_edge_multisets(seq_res, par_res),
        determinism: None, seq_time: 0.0, par_time: 0.0, par_time_2: None, speedup: 1.0,
    });

    // Test 4: Large random graph for determinism and performance
    println!("\nRunning performance and determinism test on a large graph...");
    let n = 1_000;
    let m = 10_000;
    let mut g_seq = algo_sequential::Graph::new(n);
    let mut g_par = algo_parallel::Graph::new(n);
    let mut rng = StdRng::seed_from_u64(42);
    for _ in 0..m {
        let u = rng.gen_range(0..n);
        let v = rng.gen_range(0..n);
        g_seq.add_edge(u, v);
        g_par.add_edge(u, v);
    }
    // Add some cycles to create non-trivial SCCs
    for i in 0..(n / 10) {
        let start = rng.gen_range(0..n);
        let mut curr = start;
        for _ in 0..10 {
            let next = rng.gen_range(0..n);
            g_seq.add_edge(curr, next);
            g_par.add_edge(curr, next);
            curr = next;
        }
        g_seq.add_edge(curr, start);
        g_par.add_edge(curr, start);
    }

    let start = Instant::now();
    let mut seq_res_large = g_seq.reduce_edges();
    let seq_time = start.elapsed().as_secs_f64();

    let start = Instant::now();
    let mut par_res_large1 = g_par.reduce_edges();
    let par_time = start.elapsed().as_secs_f64();
    let hash1 = hash_edges(&mut par_res_large1);

    let start = Instant::now();
    let mut par_res_large2 = g_par.reduce_edges();
    let par_time_2 = start.elapsed().as_secs_f64();
    let hash2 = hash_edges(&mut par_res_large2);

    results.push(TestResult {
        name: "Large Random Graph".to_string(),
        correctness: compare_edge_multisets(seq_res_large, par_res_large1),
        determinism: Some(hash1 == hash2),
        seq_time,
        par_time,
        par_time_2: Some(par_time_2),
        speedup: seq_time / par_time,
    });

    // --- Summary ---
    let mut summary_str = String::new();
    let mut perf_str = String::new();
    let mut all_correct = true;
    let mut all_deterministic = true;

    summary_str.push_str("--- Test Summary ---\n");
    for res in &results {
        let correct_str = if res.correctness { "PASS" } else { "FAIL" };
        all_correct &= res.correctness;
        let determinism_str = match res.determinism {
            Some(true) => { all_deterministic &= true; "PASS" },
            Some(false) => { all_deterministic &= false; "FAIL" },
            None => "N/A",
        };
        summary_str.push_str(&format!(
            "Test: {:<20} | Correctness: {} | Determinism: {}\n",
            res.name, correct_str, determinism_str
        ));
    }
    
    let overall_status = if all_correct && all_deterministic { "PASSED" } else { "FAILED" };
    summary_str.push_str(&format!("\nOverall Status: {}\n", overall_status));
    println!("\n{}", summary_str);

    if let Some(res) = results.last() {
        perf_str.push_str("--- Performance Summary ---\n");
        perf_str.push_str(&format!("Graph Size: {} vertices, {} edges\n", n, m));
        perf_str.push_str(&format!("Sequential Time: {:.4}s\n", res.seq_time));
        perf_str.push_str(&format!("Parallel Time (run 1): {:.4}s\n", res.par_time));
        if let Some(pt2) = res.par_time_2 {
            perf_str.push_str(&format!("Parallel Time (run 2): {:.4}s\n", pt2));
        }
        perf_str.push_str(&format!("Speedup: {:.2}x\n", res.speedup));
        perf_str.push_str(&format!("Cores used (estimated by Rayon): {}\n", rayon::current_num_threads()));
        println!("{}", perf_str);
    }

    std::fs::write("run_summary.txt", summary_str).expect("Unable to write summary file.");
    std::fs::write("perf.txt", perf_str).expect("Unable to write perf file.");
    
    if !all_correct || !all_deterministic {
        std::process::exit(1);
    }
}
