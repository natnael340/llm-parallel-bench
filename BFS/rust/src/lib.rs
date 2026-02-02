use std::collections::{HashMap, HashSet, VecDeque};
use std::thread;
use std::sync::Mutex;

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
    // Baseline sequential BFS (as provided), kept for differential testing
    pub fn run_seq(graph: &Graph, start_vertex: i32) -> Vec<i32> {
        if !graph.vertices().contains_key(&start_vertex) {
            return Vec::new();
        }

        let mut visited = HashSet::new();
        let mut result = Vec::new();
        let mut queue: std::collections::VecDeque<i32> = std::collections::VecDeque::new();

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

    // Parallel, deterministic, level-synchronous BFS
    pub fn run(graph: &Graph, start_vertex: i32) -> Vec<i32> {
        if !graph.vertices().contains_key(&start_vertex) {
            return Vec::new();
        }

        // Small-N fallback: for tiny frontiers, keep sequential behavior.
        const SMALL_FRONTIER: usize = 64;

        // visited/result/frontier
        let mut visited: HashSet<i32> = HashSet::new();
        let mut result: Vec<i32> = Vec::new();

        // Start vertex
        visited.insert(start_vertex);
        result.push(start_vertex);
        let mut frontier: Vec<i32> = vec![start_vertex];

        // Determine worker cap once
        let worker_cap: usize = match thread::available_parallelism() {
            Ok(n) => n.get(),
            Err(_) => 4,
        };

        while !frontier.is_empty() {
            // If frontier is small or only 1 worker, process sequentially in a way that matches baseline
            if frontier.len() <= SMALL_FRONTIER || worker_cap <= 1 {
                let mut next_frontier: Vec<i32> = Vec::new();
                for &v in &frontier {
                    if let Some(neighbors) = graph.vertices().get(&v) {
                        for &nbr in neighbors {
                            if !visited.contains(&nbr) {
                                visited.insert(nbr);
                                next_frontier.push(nbr);
                                result.push(nbr);
                            }
                        }
                    }
                }
                frontier = next_frontier;
                continue;
            }

            // Parallel path: process by level with fixed-order merge
            let current_frontier = frontier; // take ownership

            // Prepare chunks
            let len = current_frontier.len();
            let workers = worker_cap.min(len);
            let base = len / workers;
            let rem = len % workers;

            // Immutable snapshot references used in worker threads
            let graph_ref = graph;
            let visited_ref = &visited; // only read inside threads

            // Shared result slots (one per chunk), protected by a mutex
            let chunk_results: Vec<Mutex<Vec<i32>>> = (0..workers).map(|_| Mutex::new(Vec::new())).collect();

            // Spawn scoped threads to process chunks in parallel; write into their slot
            thread::scope(|s| {
                let mut start = 0usize;
                for i in 0..workers {
                    let size = base + if i < rem { 1 } else { 0 };
                    let end = start + size;
                    let chunk_slice = &current_frontier[start..end];
                    let slot = &chunk_results[i];

                    s.spawn(move || {
                        // Local dedup within this chunk
                        let mut local_seen: HashSet<i32> = HashSet::new();
                        let mut local_out: Vec<i32> = Vec::new();
                        for &v in chunk_slice {
                            if let Some(neighbors) = graph_ref.vertices().get(&v) {
                                for &nbr in neighbors {
                                    if !visited_ref.contains(&nbr) && local_seen.insert(nbr) {
                                        // Candidate for next frontier
                                        local_out.push(nbr);
                                    }
                                }
                            }
                        }
                        let mut guard = slot.lock().unwrap();
                        *guard = local_out;
                    });

                    start = end;
                }
            }); // scope ends => all threads joined

            // Fixed-order merge + global dedup against visited
            let mut next_frontier: Vec<i32> = Vec::new();
            for slot in chunk_results.into_iter() {
                let chunk = slot.into_inner().unwrap();
                for v in chunk.into_iter() {
                    if !visited.contains(&v) {
                        visited.insert(v);
                        next_frontier.push(v);
                        result.push(v);
                    }
                }
            }

            frontier = next_frontier;
        }

        result
    }
}
