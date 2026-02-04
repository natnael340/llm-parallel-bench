use std::collections::{HashMap, HashSet};
use std::collections::hash_map::DefaultHasher;
use std::hash::{Hash, Hasher};
use std::time::Instant;
use std::fs::File;
use std::io::Write;
use rayon::prelude::*;

// Graph structure
pub struct Graph {
    vertices: HashMap<i32, Vec<i32>>,
}

impl Graph {
    pub fn new() -> Self {
        Graph {
            vertices: HashMap::new(),
        }
    }

    pub fn add_edge(&mut self, from_vertex: i32, to_vertex: i32) {
        self.vertices.entry(from_vertex).or_insert_with(Vec::new);
        self.vertices.entry(to_vertex).or_insert_with(Vec::new);

        self.vertices.get_mut(&from_vertex).unwrap().push(to_vertex);
        self.vertices.get_mut(&to_vertex).unwrap().push(from_vertex);
    }

    pub fn vertices(&self) -> &HashMap<i32, Vec<i32>> {
        &self.vertices
    }
}

// Sequential BFS baseline
pub struct BfsSequential;

impl BfsSequential {
    pub fn run(graph: &Graph, start_vertex: i32) -> Vec<i32> {
        if !graph.vertices().contains_key(&start_vertex) {
            return Vec::new();
        }

        let mut visited = HashSet::new();
        let mut result = Vec::new();
        let mut current_level = vec![start_vertex];

        visited.insert(start_vertex);

        while !current_level.is_empty() {
            // Add current level to result in sorted order for determinism
            let mut sorted_level = current_level.clone();
            sorted_level.sort_unstable();
            result.extend(sorted_level.iter());

            let mut next_level = Vec::new();

            for &vertex in &current_level {
                if let Some(neighbors) = graph.vertices().get(&vertex) {
                    for &neighbor in neighbors {
                        if !visited.contains(&neighbor) {
                            visited.insert(neighbor);
                            next_level.push(neighbor);
                        }
                    }
                }
            }

            // Sort next level for deterministic ordering
            next_level.sort_unstable();
            next_level.dedup();
            current_level = next_level;
        }

        result
    }
}

// Parallel BFS implementation using level-synchronous approach
pub struct BfsParallel;

impl BfsParallel {
    const SMALL_GRAPH_THRESHOLD: usize = 100;
    const SMALL_LEVEL_THRESHOLD: usize = 50;

    pub fn run(graph: &Graph, start_vertex: i32) -> Vec<i32> {
        if !graph.vertices().contains_key(&start_vertex) {
            return Vec::new();
        }

        // Use sequential for small graphs
        if graph.vertices().len() < Self::SMALL_GRAPH_THRESHOLD {
            return BfsSequential::run(graph, start_vertex);
        }

        let mut visited = HashSet::new();
        let mut result = Vec::new();
        let mut current_level = vec![start_vertex];

        visited.insert(start_vertex);

        while !current_level.is_empty() {
            // Add current level to result in sorted order
            let mut sorted_level = current_level.clone();
            sorted_level.sort_unstable();
            result.extend(sorted_level.iter());

            // Use sequential processing for small levels
            let next_level = if current_level.len() < Self::SMALL_LEVEL_THRESHOLD {
                Self::process_level_sequential(graph, &current_level, &visited)
            } else {
                Self::process_level_parallel(graph, &current_level, &visited)
            };

            // Update visited set with new vertices
            for &vertex in &next_level {
                visited.insert(vertex);
            }

            current_level = next_level;
        }

        result
    }

    fn process_level_sequential(
        graph: &Graph,
        current_level: &[i32],
        visited: &HashSet<i32>,
    ) -> Vec<i32> {
        let mut next_level = Vec::new();
        let mut seen_in_level = HashSet::new();

        for &vertex in current_level {
            if let Some(neighbors) = graph.vertices().get(&vertex) {
                for &neighbor in neighbors {
                    if !visited.contains(&neighbor) && !seen_in_level.contains(&neighbor) {
                        seen_in_level.insert(neighbor);
                        next_level.push(neighbor);
                    }
                }
            }
        }

        next_level.sort_unstable();
        next_level
    }

    fn process_level_parallel(
        graph: &Graph,
        current_level: &[i32],
        visited: &HashSet<i32>,
    ) -> Vec<i32> {
        // Process vertices in parallel
        let neighbor_sets: Vec<Vec<i32>> = current_level
            .par_iter()
            .map(|&vertex| {
                let mut neighbors = Vec::new();
                if let Some(adj) = graph.vertices().get(&vertex) {
                    for &neighbor in adj {
                        if !visited.contains(&neighbor) {
                            neighbors.push(neighbor);
                        }
                    }
                }
                neighbors
            })
            .collect();

        // Merge deterministically
        let mut next_level = Vec::new();
        for neighbors in neighbor_sets {
            next_level.extend(neighbors);
        }

        next_level.sort_unstable();
        next_level.dedup();
        next_level
    }
}

// Test utilities
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

fn create_empty_graph() -> Graph {
    Graph::new()
}

fn create_disconnected_graph() -> Graph {
    let mut graph = Graph::new();
    graph.add_edge(1, 2);
    graph.add_edge(2, 3);
    graph.add_edge(4, 5);
    graph.add_edge(5, 6);
    graph
}

fn main() {
    let mut summary = String::new();
    let mut perf = String::new();

    summary.push_str("BFS Parallel Implementation - Test Results\n");
    summary.push_str("==========================================\n\n");

    // Edge cases
    summary.push_str("EDGE CASE TESTS\n");
    summary.push_str("---------------\n");

    let empty_graph = create_empty_graph();
    let seq_empty = BfsSequential::run(&empty_graph, 1);
    let par_empty = BfsParallel::run(&empty_graph, 1);
    if seq_empty == par_empty && seq_empty.is_empty() {
        summary.push_str("✓ empty_graph: PASS\n");
    } else {
        summary.push_str("✗ empty_graph: FAIL\n");
    }

    let disconnected = create_disconnected_graph();
    let seq_disc = BfsSequential::run(&disconnected, 1);
    let par_disc = BfsParallel::run(&disconnected, 1);
    if seq_disc == par_disc {
        summary.push_str(&format!("✓ disconnected_graph: PASS (size: {})\n", seq_disc.len()));
    } else {
        summary.push_str("✗ disconnected_graph: FAIL\n");
    }

    summary.push_str("\n");

    // Correctness tests
    summary.push_str("CORRECTNESS TESTS\n");
    summary.push_str("-----------------\n");

    let test_cases = vec![
        ("small_tree", create_small_graph(), 1),
        ("medium_grid", create_medium_graph(), 0),
        ("large_grid", create_large_graph(), 0),
        ("star_500", create_star_graph(500), 0),
        ("star_2000", create_star_graph(2000), 0),
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
    if let Ok(mut summary_file) = File::create("run_summary.txt") {
        let _ = summary_file.write_all(summary.as_bytes());
    }

    if let Ok(mut perf_file) = File::create("perf.txt") {
        let _ = perf_file.write_all(perf.as_bytes());
    }

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
