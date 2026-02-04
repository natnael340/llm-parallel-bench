use std::collections::{HashMap, HashSet, VecDeque};
use std::thread;
use std::sync::Mutex;
use rayon::prelude::*;

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

impl Default for Graph {
    fn default() -> Self {
        Self::new()
    }
}

pub struct BfsSequential;

impl BfsSequential {
    pub fn run(graph: &Graph, start_vertex: i32) -> Vec<i32> {
        if !graph.vertices().contains_key(&start_vertex) {
            return Vec::new();
        }

        let mut visited = HashSet::new();
        let mut result = Vec::new();
        let mut queue = VecDeque::new();

        queue.push_back(start_vertex);

        while let Some(current) = queue.pop_front() {
            if !visited.contains(&current) {
                visited.insert(current);
                result.push(current);

                if let Some(neighbors) = graph.vertices().get(&current) {
                    for &neighbor in neighbors {
                        if !visited.contains(&neighbor) {
                            queue.push_back(neighbor);
                        }
                    }
                }
            }
        }

        result
    }
}

// Parallel BFS implementation

pub struct BfsParallel;

impl BfsParallel {
    /// Graphs smaller than this use sequential BFS
    const SMALL_GRAPH_THRESHOLD: usize = 100;
    
    /// Levels smaller than this are processed sequentially
    const SMALL_LEVEL_THRESHOLD: usize = 50;

    pub fn run(graph: &Graph, start_vertex: i32) -> Vec<i32> {
        // Handle edge cases
        if !graph.vertices().contains_key(&start_vertex) {
            return Vec::new();
        }

        // Use sequential for small graphs to avoid thread overhead
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

            // Choose sequential or parallel processing based on level size
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

    /// Process a BFS level sequentially
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

        // Sort for deterministic ordering
        next_level.sort_unstable();
        next_level
    }

    /// Process a BFS level in parallel
    /// 
    /// Each vertex in the current level is processed by a worker thread,
    /// which collects its unvisited neighbors into a private buffer.
    /// After all workers complete, the buffers are merged and deduplicated
    /// in a deterministic order (sorted by vertex ID).
    fn process_level_parallel(
        graph: &Graph,
        current_level: &[i32],
        visited: &HashSet<i32>,
    ) -> Vec<i32> {
        // Process vertices in parallel, each collecting neighbors
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

        // Merge all neighbor sets deterministically
        let mut next_level = Vec::new();
        for neighbors in neighbor_sets {
            next_level.extend(neighbors);
        }

        // Sort and deduplicate for deterministic ordering
        next_level.sort_unstable();
        next_level.dedup();
        next_level
    }
}


