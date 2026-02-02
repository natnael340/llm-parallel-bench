use std::time::Instant;
use bfs::{BfsParallel as Bfs, Graph};
use rand::rngs::StdRng;
use rand::seq::SliceRandom;
use rand::SeedableRng;
use std::collections::VecDeque;

static mut PASSED: u32 = 0;
static mut FAILED: u32 = 0;

fn main() {
    println!("Running BFS Tests...\n");

    // Basic Tests
    test("Empty graph returns empty list", test_empty_graph);
    test("Single node with self-loop returns single node", test_single_node);
    test("Linear graph returns nodes in order", test_linear_graph);

    // Graph Structure Tests
    test("Complete graph returns correct BFS order", test_complete_graph);
    test("Star graph returns center then leaves", test_star_graph);
    test("Cycle is handled correctly", test_cycle);
    test("Tree structure returns level order", test_tree_structure);
    test("Complex graph returns correct order", test_complex_graph);

    // Edge Cases
    test("Disconnected components only visits connected component", test_disconnected_components);
    test("Duplicate edges are handled correctly", test_duplicate_edges);
    test("Nonexistent start vertex returns empty list", test_nonexistent_start);
    test("Negative vertex numbers work correctly", test_negative_vertices);
    test("Large vertex numbers work correctly", test_large_vertices);
    test("Single isolated node", test_single_isolated_node);
    test("Binary tree structure", test_binary_tree);
    test("Grid graph traversal", test_grid_graph);
    test("Hub and spoke with chains", test_hub_and_spoke);
    test("Multiple parallel edges between same nodes", test_parallel_edges);

    // Consistency Tests
    test("Order consistency is maintained across runs", test_order_consistency);
    test("Different starting vertices produce valid orderings", test_different_start_vertices);
    test("Unordered edge insertion produces correct BFS", test_unordered_edges);

    // Performance Tests
    test("Performance stress test with large linear graph", test_large_linear_graph);
    test("Performance with wide graph (many neighbors)", test_wide_graph);
    test("Performance with deep graph (long chain)", test_deep_graph);
    test("Performance speed test with complete graph", test_performance_speed_test);

    // Summary
    unsafe {
        println!("\n========================================");
        println!("Results: {} passed, {} failed, {} total", PASSED, FAILED, PASSED + FAILED);
        println!("========================================");

        if FAILED > 0 {
            std::process::exit(1);
        }
    }
}

fn test<F>(name: &str, test_fn: F)
where
    F: FnOnce() -> Result<(), String>,
{
    match test_fn() {
        Ok(()) => {
            println!("[PASS] {}", name);
            unsafe { PASSED += 1; }
        }
        Err(msg) => {
            println!("[FAIL] {}", name);
            println!("       {}", msg);
            unsafe { FAILED += 1; }
        }
    }
}

fn assert_eq<T: PartialEq + std::fmt::Debug>(expected: T, actual: T) -> Result<(), String> {
    if expected != actual {
        Err(format!("Expected {:?} but got {:?}", expected, actual))
    } else {
        Ok(())
    }
}

fn assert_true(condition: bool, message: &str) -> Result<(), String> {
    if !condition {
        Err(message.to_string())
    } else {
        Ok(())
    }
}

// ==================== Basic Tests ====================

fn test_empty_graph() -> Result<(), String> {
    let graph = Graph::new();
    let result = Bfs::run(&graph, 0);
    assert_eq(Vec::<i32>::new(), result)
}

fn test_single_node() -> Result<(), String> {
    let mut graph = Graph::new();
    graph.add_edge(1, 1);
    let result = Bfs::run(&graph, 1);
    assert_eq(vec![1], result)
}

fn test_linear_graph() -> Result<(), String> {
    let mut graph = Graph::new();
    graph.add_edge(1, 2);
    graph.add_edge(2, 3);
    graph.add_edge(3, 4);
    let result = Bfs::run(&graph, 1);
    assert_eq(vec![1, 2, 3, 4], result)
}

// ==================== Graph Structure Tests ====================

fn test_complete_graph() -> Result<(), String> {
    let mut graph = Graph::new();
    let nodes = vec![1, 2, 3, 4];
    for &i in &nodes {
        for &j in &nodes {
            if i != j {
                graph.add_edge(i, j);
            }
        }
    }
    let result = Bfs::run(&graph, 3);
    assert_eq(vec![3, 1, 2, 4], result)
}

fn test_star_graph() -> Result<(), String> {
    let mut graph = Graph::new();
    let center = 1;
    let leaves = vec![2, 3, 4, 5];
    for &leaf in &leaves {
        graph.add_edge(center, leaf);
    }
    let result = Bfs::run(&graph, center);
    let mut expected = vec![center];
    expected.extend(&leaves);
    assert_eq(expected, result)
}

fn test_cycle() -> Result<(), String> {
    let mut graph = Graph::new();
    let edges = vec![(1, 2), (2, 3), (3, 4), (4, 1)];
    for (from, to) in edges {
        graph.add_edge(from, to);
    }
    let result = Bfs::run(&graph, 1);
    assert_eq(vec![1, 2, 4, 3], result)
}

fn test_tree_structure() -> Result<(), String> {
    let mut graph = Graph::new();
    let edges = vec![(1, 2), (1, 3), (2, 4), (2, 5), (3, 6), (3, 7)];
    for (from, to) in edges {
        graph.add_edge(from, to);
    }
    let result = Bfs::run(&graph, 1);
    assert_eq(vec![1, 2, 3, 4, 5, 6, 7], result)
}

fn test_complex_graph() -> Result<(), String> {
    let mut graph = Graph::new();
    let edges = vec![
        (1, 2), (1, 3), (2, 4), (3, 4), (4, 5),
        (5, 6), (6, 7), (5, 7), (7, 8), (3, 8),
    ];
    for (from, to) in edges {
        graph.add_edge(from, to);
    }
    let result = Bfs::run(&graph, 1);
    assert_eq(vec![1, 2, 3, 4, 8, 5, 7, 6], result)
}

// ==================== Edge Cases ====================

fn test_disconnected_components() -> Result<(), String> {
    let mut graph = Graph::new();
    graph.add_edge(1, 2);
    graph.add_edge(2, 3);
    graph.add_edge(4, 5);
    graph.add_edge(4, 6);

    let result1 = Bfs::run(&graph, 1);
    assert_eq(vec![1, 2, 3], result1)?;

    let result2 = Bfs::run(&graph, 4);
    assert_eq(vec![4, 5, 6], result2)
}

fn test_duplicate_edges() -> Result<(), String> {
    let mut graph = Graph::new();
    graph.add_edge(1, 2);
    graph.add_edge(1, 2);
    graph.add_edge(2, 3);
    let result = Bfs::run(&graph, 1);
    assert_eq(vec![1, 2, 3], result)
}

fn test_nonexistent_start() -> Result<(), String> {
    let mut graph = Graph::new();
    graph.add_edge(1, 2);
    let result = Bfs::run(&graph, 999);
    assert_eq(Vec::<i32>::new(), result)
}

fn test_negative_vertices() -> Result<(), String> {
    let mut graph = Graph::new();
    graph.add_edge(-1, -2);
    graph.add_edge(-2, -3);
    graph.add_edge(-1, 0);
    let result = Bfs::run(&graph, -1);
    assert_eq(vec![-1, -2, 0, -3], result)
}

fn test_large_vertices() -> Result<(), String> {
    let mut graph = Graph::new();
    graph.add_edge(i32::MAX - 1, i32::MAX);
    graph.add_edge(i32::MAX, 0);
    let result = Bfs::run(&graph, i32::MAX - 1);
    assert_eq(vec![i32::MAX - 1, i32::MAX, 0], result)
}

fn test_single_isolated_node() -> Result<(), String> {
    let mut graph = Graph::new();
    graph.add_edge(42, 42);
    let result = Bfs::run(&graph, 42);
    assert_eq(vec![42], result)
}

fn test_binary_tree() -> Result<(), String> {
    let mut graph = Graph::new();
    graph.add_edge(1, 2);
    graph.add_edge(1, 3);
    graph.add_edge(2, 4);
    graph.add_edge(2, 5);
    graph.add_edge(3, 6);
    graph.add_edge(3, 7);
    let result = Bfs::run(&graph, 1);
    assert_eq(vec![1, 2, 3, 4, 5, 6, 7], result)
}

fn test_grid_graph() -> Result<(), String> {
    let mut graph = Graph::new();
    graph.add_edge(1, 2);
    graph.add_edge(1, 3);
    graph.add_edge(2, 4);
    graph.add_edge(3, 4);
    let result = Bfs::run(&graph, 1);
    assert_eq(4, result.len())?;
    assert_eq(1, result[0])?;
    let level1: Vec<i32> = result[1..3].to_vec();
    assert_true(level1.contains(&2) && level1.contains(&3), "Level 1 should contain 2 and 3")?;
    assert_eq(4, result[3])
}

fn test_hub_and_spoke() -> Result<(), String> {
    let mut graph = Graph::new();
    graph.add_edge(0, 1);
    graph.add_edge(0, 2);
    graph.add_edge(0, 3);
    graph.add_edge(1, 4);
    graph.add_edge(2, 5);
    graph.add_edge(3, 6);
    let result = Bfs::run(&graph, 0);
    assert_eq(7, result.len())?;
    assert_eq(0, result[0])?;
    let level1: Vec<i32> = result[1..4].to_vec();
    assert_true(
        level1.contains(&1) && level1.contains(&2) && level1.contains(&3),
        "Level 1 should contain 1, 2, 3",
    )?;
    let level2: Vec<i32> = result[4..7].to_vec();
    assert_true(
        level2.contains(&4) && level2.contains(&5) && level2.contains(&6),
        "Level 2 should contain 4, 5, 6",
    )
}

fn test_parallel_edges() -> Result<(), String> {
    let mut graph = Graph::new();
    graph.add_edge(1, 2);
    graph.add_edge(1, 2);
    graph.add_edge(1, 2);
    graph.add_edge(2, 3);
    let result = Bfs::run(&graph, 1);
    assert_eq(vec![1, 2, 3], result)
}

// ==================== Consistency Tests ====================

fn test_order_consistency() -> Result<(), String> {
    let mut graph = Graph::new();
    graph.add_edge(1, 3);
    graph.add_edge(1, 2);

    let first = Bfs::run(&graph, 1);
    for _ in 0..5 {
        let result = Bfs::run(&graph, 1);
        assert_eq(first.clone(), result)?;
    }
    Ok(())
}

fn test_different_start_vertices() -> Result<(), String> {
    let mut graph = Graph::new();
    graph.add_edge(1, 2);
    graph.add_edge(2, 3);
    graph.add_edge(3, 4);
    graph.add_edge(4, 5);

    assert_eq(vec![1, 2, 3, 4, 5], Bfs::run(&graph, 1))?;
    assert_eq(vec![3, 2, 4, 1, 5], Bfs::run(&graph, 3))?;
    assert_eq(vec![5, 4, 3, 2, 1], Bfs::run(&graph, 5))
}


fn test_unordered_edges() -> Result<(), String> {
    // Edges added in non-sorted, scrambled order
    let seed = 42;
    let mut graph = Graph::new();
    let mut rng = StdRng::seed_from_u64(seed);
    
    let num_nodes = 100;
    
    for from in 1..=num_nodes {
        let mut neighbors: Vec<i32> = (1..=num_nodes).filter(|&to| to != from).collect();

        neighbors.shuffle(&mut rng);
        
        for to in neighbors {
            graph.add_edge(from, to);
        }
    }
    let expected = [
        1,100,46,64,4,3,22,27,94,62,36,63,92,45,5,81,90,25,85,50,6,7,
        73,28,13,48,75,65,44,93,82,74,99,60,52,83,70,37,9,31,78,11,69,
        41,89,18,96,80,55,42,34,97,95,16,98,88,8,59,79,57,10,76,20,86,
        53,87,71,15,29,19,68,38,54,40,77,21,17,12,32,51,30,47,2,56,33,
        66,91,43,61,84,67,58,35,24,23,26,39,49,14,72
    ];
    let result =  Bfs::run(&graph, 1);
    // BFS from node 1 should still produce valid level-order traversal
    assert_eq(expected.to_vec(), result)

}

// ==================== Performance Tests ====================

fn test_large_linear_graph() -> Result<(), String> {
    let mut graph = Graph::new();
    let size = 1000;
    for i in 1..size {
        graph.add_edge(i, i + 1);
    }
    let result = Bfs::run(&graph, 1);
    assert_eq(size as usize, result.len())?;
    assert_eq(1, result[0])?;
    assert_eq(size, result[result.len() - 1])
}

fn test_wide_graph() -> Result<(), String> {
    let mut graph = Graph::new();
    let center = 0;
    let num_neighbors = 5000;
    for i in 1..=num_neighbors {
        graph.add_edge(center, i);
    }

    let start = Instant::now();
    let result = Bfs::run(&graph, center);
    let duration = start.elapsed();

    assert_eq((num_neighbors + 1) as usize, result.len())?;
    assert_eq(center, result[0])?;

    println!("       (Wide graph: center + {} neighbors in {:.2} ms)", num_neighbors, duration.as_secs_f64() * 1000.0);
    Ok(())
}

fn test_deep_graph() -> Result<(), String> {
    let mut graph = Graph::new();
    let depth = 10000;
    for i in 0..depth - 1 {
        graph.add_edge(i, i + 1);
    }

    let start = Instant::now();
    let result = Bfs::run(&graph, 0);
    let duration = start.elapsed();

    assert_eq(depth as usize, result.len())?;
    assert_eq(0, result[0])?;
    assert_eq(depth - 1, result[result.len() - 1])?;

    println!("       (Deep graph: depth={} in {:.2} ms)", depth, duration.as_secs_f64() * 1000.0);
    Ok(())
}

fn test_performance_speed_test() -> Result<(), String> {
    let mut graph = Graph::new();
    let size: i32 = 2000;
    for i in 1..=size {
        for j in (i + 1)..=size {
            graph.add_edge(i, j);
            graph.add_edge(j, i);
        }
    }

    // Warm-up
    let _ = Bfs::run(&graph, 1);

    let reps = 5;
    let iters = 20;
    let mut times: Vec<f64> = Vec::with_capacity(reps);

    for _ in 0..reps {
        let start = Instant::now();
        for _ in 0..iters {
            let _ = Bfs::run(&graph, 1);
        }
        let duration = start.elapsed();
        times.push(duration.as_secs_f64() * 1000.0 / iters as f64);
    }

    let avg = average(&times);
    let sd = standard_deviation(&times);

    let directed_edges = size as i64 * (size as i64 - 1);
    println!(
        "       (BFS complete graph | nodes={}, undirected edges≈{} (directed≈{}) | {:.2} ms/run ± {:.2} (n={}))",
        size, directed_edges / 2, directed_edges, avg, sd, reps
    );
    Ok(())
}

fn average(values: &[f64]) -> f64 {
    values.iter().sum::<f64>() / values.len() as f64
}

fn standard_deviation(values: &[f64]) -> f64 {
    let avg = average(values);
    let sum_squares: f64 = values.iter().map(|v| (v - avg).powi(2)).sum();
    (sum_squares / values.len() as f64).sqrt()
}
