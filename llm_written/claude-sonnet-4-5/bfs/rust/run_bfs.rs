use std::collections::hash_map::DefaultHasher;
use std::hash::{Hash, Hasher};
use std::time::Instant;
use std::fs::File;
use std::io::Write;

mod bfs_parallel;
use bfs_parallel::{BfsParallel, BfsSequential, Graph};

fn calculate_hash<T: Hash>(t: &T) -> u64 {
    let mut hasher = DefaultHasher::new();
    t.hash(&mut hasher);
    hasher.finish()
}

fn create_small_graph() -> Graph {
    let mut graph = Graph::new();
    graph.add_edge(1, 2);
    graph.add_edge(1, 3);
    graph.add_edge(2, 4);
    graph.add_edge(2, 5);
    graph.add_edge(3, 6);
    graph
}

fn create_medium_graph() -> Graph {
    let mut graph = Graph::new();
    for i in 0..10 {
        for j in 0..10 {
            let vertex = i * 10 + j;
            if j < 9 {
                graph.add_edge(vertex, vertex + 1);
            }
            if i < 9 {
                graph.add_edge(vertex, vertex + 10);
            }
        }
    }
    graph
}

fn create_large_graph() -> Graph {
    let mut graph = Graph::new();
    for i in 0..100 {
        for j in 0..100 {
            let vertex = i * 100 + j;
            if j < 99 {
                graph.add_edge(vertex, vertex + 1);
            }
            if i < 99 {
                graph.add_edge(vertex, vertex + 100);
            }
            if i < 99 && j < 99 {
                graph.add_edge(vertex, vertex + 101);
            }
        }
    }
    graph
}

fn create_star_graph(n: i32) -> Graph {
    let mut graph = Graph::new();
    for i in 1..n {
        graph.add_edge(0, i);
    }
    graph
}

fn main() {
    let mut summary = String::new();
    let mut perf = String::new();

    summary.push_str("BFS Parallel Implementation - Test Results\n");
    summary.push_str("==========================================\n\n");

    // Correctness tests
    summary.push_str("CORRECTNESS TESTS\n");
    summary.push_str("-----------------\n");

    let test_cases = vec![
        ("small_tree", create_small_graph(), 1),
        ("medium_grid", create_medium_graph(), 0),
        ("large_grid", create_large_graph(), 0),
        ("star_500", create_star_graph(500), 0),
    ];

    let mut all_pass = true;

    for (name, graph, start) in &test_cases {
        let seq = BfsSequential::run(graph, *start);
        let par = BfsParallel::run(graph, *start);
        let matches = seq == par;
        
        if matches {
            summary.push_str(&format!("✓ {}: PASS (size: {})\n", name, seq.len()));
        } else {
            summary.push_str(&format!("✗ {}: FAIL\n", name));
            all_pass = false;
        }
    }

    summary.push_str("\n");

    // Determinism tests
    summary.push_str("DETERMINISM TESTS\n");
    summary.push_str("-----------------\n");

    for (name, graph, start) in &test_cases {
        let run1 = BfsParallel::run(graph, *start);
        let run2 = BfsParallel::run(graph, *start);
        let run3 = BfsParallel::run(graph, *start);

        let hash1 = calculate_hash(&run1);
        let hash2 = calculate_hash(&run2);
        let hash3 = calculate_hash(&run3);

        if hash1 == hash2 && hash2 == hash3 {
            summary.push_str(&format!("✓ {}: DETERMINISTIC\n", name));
            summary.push_str(&format!("  Hash: {:016x}\n", hash1));
        } else {
            summary.push_str(&format!("✗ {}: NON-DETERMINISTIC\n", name));
            summary.push_str(&format!("  Hashes: {:016x}, {:016x}, {:016x}\n", hash1, hash2, hash3));
            all_pass = false;
        }
    }

    summary.push_str("\n");

    // Performance tests
    perf.push_str("BFS Performance Results\n");
    perf.push_str("=======================\n\n");

    let perf_cases = vec![
        ("grid_100x100", create_large_graph(), 0),
        ("star_5000", create_star_graph(5000), 0),
    ];

    for (name, graph, start) in perf_cases {
        perf.push_str(&format!("Test: {}\n", name));
        perf.push_str(&format!("Vertices: {}\n", graph.vertices().len()));

        // Warmup
        let _ = BfsSequential::run(&graph, start);
        let _ = BfsParallel::run(&graph, start);

        // Sequential
        let seq_start = Instant::now();
        let seq_result = BfsSequential::run(&graph, start);
        let seq_time = seq_start.elapsed();

        // Parallel (3 runs)
        let mut par_times = Vec::new();
        for _ in 0..3 {
            let par_start = Instant::now();
            let _ = BfsParallel::run(&graph, start);
            par_times.push(par_start.elapsed());
        }
        let par_time = par_times.iter().sum::<std::time::Duration>() / 3;

        let speedup = seq_time.as_secs_f64() / par_time.as_secs_f64();
        let threads = rayon::current_num_threads();
        let efficiency = speedup / threads as f64;

        perf.push_str(&format!("  Sequential: {:.2} ms\n", seq_time.as_secs_f64() * 1000.0));
        perf.push_str(&format!("  Parallel:   {:.2} ms\n", par_time.as_secs_f64() * 1000.0));
        perf.push_str(&format!("  Speedup:    {:.2}×\n", speedup));
        perf.push_str(&format!("  Threads:    {}\n", threads));
        perf.push_str(&format!("  Efficiency: {:.1}%\n", efficiency * 100.0));
        perf.push_str(&format!("  Result size: {}\n\n", seq_result.len()));
    }

    // Write files
    let mut summary_file = File::create("run_summary.txt").unwrap();
    summary_file.write_all(summary.as_bytes()).unwrap();

    let mut perf_file = File::create("perf.txt").unwrap();
    perf_file.write_all(perf.as_bytes()).unwrap();

    // Print to console
    println!("{}", summary);
    println!("{}", perf);

    if all_pass {
        println!("✓ All tests passed!");
        std::process::exit(0);
    } else {
        println!("✗ Some tests failed!");
        std::process::exit(1);
    }
}
