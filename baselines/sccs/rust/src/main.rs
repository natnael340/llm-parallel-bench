mod seq;

use std::env;
use std::fs;
use std::time::Instant;

use serde::Serialize;

use seq::Graph;

#[derive(Serialize)]
struct BenchmarkResult {
    elapsed_ms: Vec<f64>,
    mean: f64,
    sd: f64,
    iterations: usize,
}

fn ring_scc(start: usize, end: usize, g: &mut Graph) {
    for i in start..end {
        let mut v = (i + 1) % end;
        if v == 0 {
            v = start;
        }
        if i == v {
            continue;
        }
        g.add_edge(i, v);
    }
}

fn build_graph(graph_size: usize, cluster_size: usize, no_cluster_in_group: usize) -> Graph {
    let mut g = Graph::new(graph_size);

    // Simple LCG random number generator seeded with 43 to match C/C++ srand(43)
    let mut rng_state: u64 = 43;
    let mut next_rand = || -> usize {
        rng_state = rng_state.wrapping_mul(1103515245).wrapping_add(12345) & 0x7fff_ffff;
        rng_state as usize
    };

    let mut i = 0;
    while i < graph_size {
        ring_scc(i, std::cmp::min(i + cluster_size, graph_size), &mut g);

        let current_cluster = i / cluster_size;
        if current_cluster / no_cluster_in_group == (current_cluster + 1) / no_cluster_in_group {
            if (i + cluster_size) < graph_size {
                let end_a = std::cmp::min(i + cluster_size, graph_size);
                let end_b = std::cmp::min(i + 2 * cluster_size, graph_size);

                let u = i + (next_rand() % (end_a - i));
                let v = end_a + (next_rand() % (end_b - end_a));
                g.add_edge(u, v);
            }
        }
        i += cluster_size;
    }
    g
}

fn benchmark_reduce_edges(reps: usize, iters: usize, filename: &str) {
    let graph_size = 100_000;
    let cluster_size = 300;
    let no_cluster_in_group = 3;

    let g = build_graph(graph_size, cluster_size, no_cluster_in_group);

    // warmup
    g.reduce_edges();

    let mut per_repeat_ms = Vec::with_capacity(reps);

    for _ in 0..reps {
        let start = Instant::now();
        for _ in 0..iters {
            g.reduce_edges();
        }
        let elapsed = start.elapsed();
        per_repeat_ms.push(elapsed.as_secs_f64() * 1000.0 / iters as f64);
    }

    let mean = per_repeat_ms.iter().sum::<f64>() / reps as f64;
    let sq_sum: f64 = per_repeat_ms.iter().map(|t| (t - mean) * (t - mean)).sum();
    let stddev = (sq_sum / reps as f64).sqrt();

    let result = BenchmarkResult {
        elapsed_ms: per_repeat_ms,
        mean,
        sd: stddev,
        iterations: reps,
    };

    match serde_json::to_string_pretty(&result) {
        Ok(json) => {
            if let Err(e) = fs::write(filename, &json) {
                eprintln!("Error writing JSON to file: {}\n{}", filename, e);
            }
        }
        Err(e) => {
            eprintln!("Error serializing JSON: {}", e);
        }
    }

    println!("SCC FindSCCs | graph_size={graph_size} | {mean:.4} ms/run \u{00b1} {stddev:.4} (n={reps})");
}

fn parse_args() -> std::collections::HashMap<String, String> {
    let args: Vec<String> = env::args().collect();
    let mut flags = std::collections::HashMap::new();
    let mut i = 1;
    while i < args.len().saturating_sub(1) {
        if args[i].starts_with("--") {
            flags.insert(args[i][2..].to_string(), args[i + 1].clone());
            i += 2;
        } else {
            i += 1;
        }
    }
    flags
}

fn main() {
    let flags = parse_args();

    let reps: usize = flags
        .get("reps")
        .and_then(|s| s.parse().ok())
        .unwrap_or(5);

    let iters: usize = flags
        .get("iters")
        .and_then(|s| s.parse().ok())
        .unwrap_or(20);

    let filename = match flags.get("out") {
        Some(f) => f.clone(),
        None => {
            eprintln!("Error: Output file not specified. Use --out <filename>");
            std::process::exit(1);
        }
    };

    println!("Starting BenchmarkFindSCCs...");
    benchmark_reduce_edges(reps, iters, &filename);
}
