
mod algo_sequential;
mod algo_parallel;

use std::collections::hash_map::DefaultHasher;
use std::hash::{Hash, Hasher};
use std::time::Instant;

fn create_graph(nodes: i32, edges_per_node: i32) -> algo_sequential::Graph {
    let mut graph = algo_sequential::Graph::new();
    for i in 0..nodes {
        for j in 1..=edges_per_node {
            graph.add_edge(i, (i + j) % nodes);
        }
    }
    graph
}

fn create_parallel_graph(nodes: i32, edges_per_node: i32) -> algo_parallel::Graph {
    let mut graph = algo_parallel::Graph::new();
    for i in 0..nodes {
        for j in 1..=edges_per_node {
            graph.add_edge(i, (i + j) % nodes);
        }
    }
    graph
}

fn calculate_hash<T: Hash>(t: &T) -> u64 {
    let mut s = DefaultHasher::new();
    t.hash(&mut s);
    s.finish()
}

fn main() {
    let scenarios = [
        ("edge_empty", 0, 0),
        ("edge_single", 1, 0),
        ("small", 100, 5),
        ("medium", 1000, 10),
        ("large", 10000, 20),
    ];

    let mut results = Vec::new();

    for &(name, nodes, edges_per_node) in &scenarios {
        println!("--- Running scenario: {} ---", name);

        // Sequential
        let seq_graph = create_graph(nodes, edges_per_node);
        let start_time = Instant::now();
        let seq_result = algo_sequential::Bfs::run(&seq_graph, 0);
        let seq_duration = start_time.elapsed();
        let seq_hash = calculate_hash(&seq_result);

        // Parallel
        let par_graph = create_parallel_graph(nodes, edges_per_node);
        let mut par_durations = Vec::new();
        let mut par_hashes = Vec::new();
        let mut par_results = Vec::new();

        for i in 0..3 {
            let start_time = Instant::now();
            let par_result = algo_parallel::Bfs::run(&par_graph, 0);
            let par_duration = start_time.elapsed();
            par_durations.push(par_duration);
            par_hashes.push(calculate_hash(&par_result));
            if i == 0 {
                par_results.push(par_result);
            }
        }

        let par_duration_avg = par_durations.iter().sum::<std::time::Duration>() / par_durations.len() as u32;

        let correctness = seq_result == par_results[0];
        let determinism = par_hashes.windows(2).all(|w| w[0] == w[1]);

        results.push(format!(
            "Scenario: {}\n\
             Correctness: {}\n\
             Determinism: {}\n\
             Sequential time: {:?}\n\
             Parallel time (avg): {:?}\n\
             Speedup: {:.2}x\n\
             Sequential Hash: {}\n\
             Parallel Hashes: {:?}\n",
            name,
            if correctness { "PASS" } else { "FAIL" },
            if determinism { "PASS" } else { "FAIL" },
            seq_duration,
            par_duration_avg,
            if par_duration_avg.as_nanos() > 0 { seq_duration.as_secs_f64() / par_duration_avg.as_secs_f64() } else { 0.0 },
            seq_hash,
            par_hashes
        ));

        if !correctness || !determinism {
            println!("Test failed for scenario: {}", name);
            std::process::exit(1);
        }
    }

    println!("\n--- All tests passed ---");
    let summary = results.join("\n");
    println!("{}", summary);
    std::fs::write("run_summary.txt", summary).expect("Unable to write summary file");
}
