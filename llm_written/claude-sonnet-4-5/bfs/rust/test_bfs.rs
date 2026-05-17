use std::collections::hash_map::DefaultHasher;
use std::hash::{Hash, Hasher};
use std::time::Instant;

mod bfs_parallel;
use bfs_parallel::{BfsParallel, BfsSequential, Graph};

fn calculate_hash<T: Hash>(t: &T) -> u64 {
    let mut hasher = DefaultHasher::new();
    t.hash(&mut hasher);
    hasher.finish()
}

// Test graph builders
fn create_empty_graph() -> Graph {
    Graph::new()
}

fn create_single_vertex_graph() -> Graph {
    let mut graph = Graph::new();
    graph.vertices().clone().insert(1, Vec::new());
    // Use add_edge to properly initialize
    let mut g = Graph::new();
    g.add_edge(1, 1); // self-loop
    g
}

fn create_small_graph() -> Graph {
    let mut graph = Graph::new();
    // Tree structure
    //     1
    //    / \
    //   2   3
    //  / \   \
    // 4   5   6
    graph.add_edge(1, 2);
    graph.add_edge(1, 3);
    graph.add_edge(2, 4);
    graph.add_edge(2, 5);
    graph.add_edge(3, 6);
    graph
}

fn create_medium_graph() -> Graph {
    let mut graph = Graph::new();
    // Create a grid-like graph: 10x10 = 100 vertices
    for i in 0..10 {
        for j in 0..10 {
            let vertex = i * 10 + j;
            // Connect to right neighbor
            if j < 9 {
                graph.add_edge(vertex, vertex + 1);
            }
            // Connect to bottom neighbor
            if i < 9 {
                graph.add_edge(vertex, vertex + 10);
            }
        }
    }
    graph
}

fn create_large_graph() -> Graph {
    let mut graph = Graph::new();
    // Create a larger grid: 100x100 = 10,000 vertices
    for i in 0..100 {
        for j in 0..100 {
            let vertex = i * 100 + j;
            // Connect to right neighbor
            if j < 99 {
                graph.add_edge(vertex, vertex + 1);
            }
            // Connect to bottom neighbor
            if i < 99 {
                graph.add_edge(vertex, vertex + 100);
            }
            // Add diagonal for more interesting structure
            if i < 99 && j < 99 {
                graph.add_edge(vertex, vertex + 101);
            }
        }
    }
    graph
}

fn create_disconnected_graph() -> Graph {
    let mut graph = Graph::new();
    // Component 1: vertices 1-3
    graph.add_edge(1, 2);
    graph.add_edge(2, 3);
    // Component 2: vertices 4-6
    graph.add_edge(4, 5);
    graph.add_edge(5, 6);
    graph
}

fn create_star_graph(n: i32) -> Graph {
    let mut graph = Graph::new();
    // Center vertex 0 connected to all others
    for i in 1..n {
        graph.add_edge(0, i);
    }
    graph
}

struct TestCase {
    name: &'static str,
    graph: Graph,
    start_vertex: i32,
}

fn run_correctness_tests() -> (usize, usize) {
    let test_cases = vec![
        TestCase {
            name: "empty_graph",
            graph: create_empty_graph(),
            start_vertex: 1,
        },
        TestCase {
            name: "single_vertex",
            graph: create_single_vertex_graph(),
            start_vertex: 1,
        },
        TestCase {
            name: "small_tree",
            graph: create_small_graph(),
            start_vertex: 1,
        },
        TestCase {
            name: "medium_grid",
            graph: create_medium_graph(),
            start_vertex: 0,
        },
        TestCase {
            name: "large_grid",
            graph: create_large_graph(),
            start_vertex: 0,
        },
        TestCase {
            name: "disconnected_component1",
            graph: create_disconnected_graph(),
            start_vertex: 1,
        },
        TestCase {
            name: "disconnected_component2",
            graph: create_disconnected_graph(),
            start_vertex: 4,
        },
        TestCase {
            name: "star_small",
            graph: create_star_graph(50),
            start_vertex: 0,
        },
        TestCase {
            name: "star_large",
            graph: create_star_graph(1000),
            start_vertex: 0,
        },
    ];

    let mut passed = 0;
    let mut failed = 0;

    println!("=== CORRECTNESS TESTS ===\n");

    for test in test_cases {
        let seq_result = BfsSequential::run(&test.graph, test.start_vertex);
        let par_result = BfsParallel::run(&test.graph, test.start_vertex);

        let matches = seq_result == par_result;
        
        if matches {
            println!("✓ {}: PASS (size: {})", test.name, seq_result.len());
            passed += 1;
        } else {
            println!("✗ {}: FAIL", test.name);
            println!("  Sequential: {:?}", seq_result);
            println!("  Parallel:   {:?}", par_result);
            failed += 1;
        }
    }

    println!("\nCorrectness: {}/{} passed\n", passed, passed + failed);
    (passed, failed)
}

fn run_determinism_tests() -> (usize, usize) {
    println!("=== DETERMINISM TESTS ===\n");

    let test_graphs = vec![
        ("small_tree", create_small_graph(), 1),
        ("medium_grid", create_medium_graph(), 0),
        ("large_grid", create_large_graph(), 0),
        ("star_graph", create_star_graph(500), 0),
    ];

    let mut passed = 0;
    let mut failed = 0;

    for (name, graph, start) in test_graphs {
        // Run parallel BFS 3 times
        let run1 = BfsParallel::run(&graph, start);
        let run2 = BfsParallel::run(&graph, start);
        let run3 = BfsParallel::run(&graph, start);

        let hash1 = calculate_hash(&run1);
        let hash2 = calculate_hash(&run2);
        let hash3 = calculate_hash(&run3);

        if hash1 == hash2 && hash2 == hash3 {
            println!("✓ {}: DETERMINISTIC", name);
            println!("  Hash: {:016x}", hash1);
            println!("  All 3 runs match");
            passed += 1;
        } else {
            println!("✗ {}: NON-DETERMINISTIC", name);
            println!("  Hash 1: {:016x}", hash1);
            println!("  Hash 2: {:016x}", hash2);
            println!("  Hash 3: {:016x}", hash3);
            failed += 1;
        }
        println!();
    }

    println!("Determinism: {}/{} passed\n", passed, passed + failed);
    (passed, failed)
}

fn run_performance_tests() {
    println!("=== PERFORMANCE TESTS ===\n");

    let test_cases = vec![
        ("grid_100x100", create_large_graph(), 0),
        ("star_5000", create_star_graph(5000), 0),
    ];

    for (name, graph, start) in test_cases {
        println!("Test: {}", name);
        println!("Vertices: {}", graph.vertices().len());

        // Warmup
        let _ = BfsSequential::run(&graph, start);
        let _ = BfsParallel::run(&graph, start);

        // Sequential timing
        let seq_start = Instant::now();
        let seq_result = BfsSequential::run(&graph, start);
        let seq_duration = seq_start.elapsed();

        // Parallel timing (average of 3 runs)
        let mut par_durations = Vec::new();
        for _ in 0..3 {
            let par_start = Instant::now();
            let _ = BfsParallel::run(&graph, start);
            par_durations.push(par_start.elapsed());
        }
        let par_duration = par_durations.iter().sum::<std::time::Duration>() / 3;

        let speedup = seq_duration.as_secs_f64() / par_duration.as_secs_f64();
        let num_threads = rayon::current_num_threads();
        let efficiency = speedup / num_threads as f64;

        println!("  Sequential: {:.2} ms", seq_duration.as_secs_f64() * 1000.0);
        println!("  Parallel:   {:.2} ms", par_duration.as_secs_f64() * 1000.0);
        println!("  Speedup:    {:.2}×", speedup);
        println!("  Threads:    {}", num_threads);
        println!("  Efficiency: {:.1}%", efficiency * 100.0);
        println!("  Result size: {}", seq_result.len());
        println!();
    }
}

fn main() {
    println!("BFS Parallel Implementation Test Suite\n");
    println!("========================================\n");

    // Run all tests
    let (corr_pass, corr_fail) = run_correctness_tests();
    let (det_pass, det_fail) = run_determinism_tests();
    run_performance_tests();

    // Summary
    println!("=== SUMMARY ===");
    println!("Correctness: {}/{} passed", corr_pass, corr_pass + corr_fail);
    println!("Determinism: {}/{} passed", det_pass, det_pass + det_fail);

    let total_pass = corr_pass + det_pass;
    let total_fail = corr_fail + det_fail;
    println!("Total:       {}/{} passed", total_pass, total_pass + total_fail);

    // Exit code
    if total_fail > 0 {
        std::process::exit(1);
    }
}
