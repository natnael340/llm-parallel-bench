// Sequential implementation module
mod scc_sequential {
    use std::collections::HashSet;

    pub struct Graph {
        v: usize,
        adj: Vec<Vec<usize>>,
        rev_adj: Vec<Vec<usize>>,
        verbose: bool,
    }

    impl Graph {
        pub fn new(v: usize) -> Self {
            Self::with_verbose(v, false)
        }

        pub fn with_verbose(v: usize, verbose: bool) -> Self {
            Graph {
                v,
                adj: vec![Vec::new(); v],
                rev_adj: vec![Vec::new(); v],
                verbose,
            }
        }

        pub fn add_edge(&mut self, v: usize, w: usize) {
            self.adj[v].push(w);
            self.rev_adj[w].push(v);
        }

        fn tarjan_dfs(
            &self,
            u: usize,
            disc: &mut [i32],
            low: &mut [i32],
            stack: &mut Vec<usize>,
            in_stack: &mut [bool],
            timer: &mut i32,
            scc_list: &mut Vec<Vec<usize>>,
        ) {
            *timer += 1;
            disc[u] = *timer;
            low[u] = *timer;
            stack.push(u);
            in_stack[u] = true;

            for &v in &self.adj[u] {
                if disc[v] == -1 {
                    self.tarjan_dfs(v, disc, low, stack, in_stack, timer, scc_list);
                    low[u] = low[u].min(low[v]);
                } else if in_stack[v] {
                    low[u] = low[u].min(disc[v]);
                }
            }

            if low[u] == disc[u] {
                let mut scc = Vec::new();
                loop {
                    let w = stack.pop().unwrap();
                    in_stack[w] = false;
                    scc.push(w);
                    if w == u {
                        break;
                    }
                }
                scc_list.push(scc);
            }
        }

        fn build_spanning_tree_edges(
            &self,
            start: usize,
            graph: &[Vec<usize>],
            nodes: &HashSet<usize>,
        ) -> Vec<(usize, usize)> {
            let mut edges = Vec::new();
            let mut visited = HashSet::new();
            let mut st = vec![start];
            visited.insert(start);

            while let Some(node) = st.pop() {
                for &nb in &graph[node] {
                    if nodes.contains(&nb) && !visited.contains(&nb) {
                        edges.push((node, nb));
                        visited.insert(nb);
                        st.push(nb);
                    }
                }
            }
            edges
        }

        pub fn find_sccs(&self) -> Vec<Vec<usize>> {
            let mut disc = vec![-1i32; self.v];
            let mut low = vec![-1i32; self.v];
            let mut in_stack = vec![false; self.v];
            let mut stack = Vec::new();
            let mut scc_list = Vec::new();
            let mut timer = 0i32;

            for i in 0..self.v {
                if disc[i] == -1 {
                    self.tarjan_dfs(i, &mut disc, &mut low, &mut stack, &mut in_stack, &mut timer, &mut scc_list);
                }
            }
            scc_list
        }

        pub fn minimize_edges_in_scc(&self, scc: &[usize]) -> Vec<(usize, usize)> {
            let nodes: HashSet<usize> = scc.iter().copied().collect();
            let mut essential_edges = Vec::new();

            let forward_tree = self.build_spanning_tree_edges(scc[0], &self.adj, &nodes);
            let reverse_tree = self.build_spanning_tree_edges(scc[0], &self.rev_adj, &nodes);

            essential_edges.extend(forward_tree);
            essential_edges.extend(reverse_tree);

            essential_edges
        }

        pub fn reduce_edges(&self) -> Vec<(usize, usize)> {
            let sccs = self.find_sccs();
            if self.verbose {
                println!("Found {} SCC(s).", sccs.len());
            }

            let mut reduced_edges = Vec::new();
            for scc in &sccs {
                let min_edges = self.minimize_edges_in_scc(scc);
                reduced_edges.extend(min_edges);
            }

            if self.verbose {
                println!("Reduced SCC edges: {}", reduced_edges.len());
            }
            reduced_edges
        }
    }
}

// Parallel implementation module
mod scc_parallel {
    use std::collections::HashSet;
    use std::sync::{Arc, Mutex};
    use std::thread;

    pub struct Graph {
        v: usize,
        adj: Vec<Vec<usize>>,
        rev_adj: Vec<Vec<usize>>,
        verbose: bool,
    }

    impl Graph {
        pub fn new(v: usize) -> Self {
            Self::with_verbose(v, false)
        }

        pub fn with_verbose(v: usize, verbose: bool) -> Self {
            Graph {
                v,
                adj: vec![Vec::new(); v],
                rev_adj: vec![Vec::new(); v],
                verbose,
            }
        }

        pub fn add_edge(&mut self, v: usize, w: usize) {
            self.adj[v].push(w);
            self.rev_adj[w].push(v);
        }

        fn tarjan_dfs(
            &self,
            u: usize,
            disc: &mut [i32],
            low: &mut [i32],
            stack: &mut Vec<usize>,
            in_stack: &mut [bool],
            timer: &mut i32,
            scc_list: &mut Vec<Vec<usize>>,
        ) {
            *timer += 1;
            disc[u] = *timer;
            low[u] = *timer;
            stack.push(u);
            in_stack[u] = true;

            for &v in &self.adj[u] {
                if disc[v] == -1 {
                    self.tarjan_dfs(v, disc, low, stack, in_stack, timer, scc_list);
                    low[u] = low[u].min(low[v]);
                } else if in_stack[v] {
                    low[u] = low[u].min(disc[v]);
                }
            }

            if low[u] == disc[u] {
                let mut scc = Vec::new();
                loop {
                    let w = stack.pop().unwrap();
                    in_stack[w] = false;
                    scc.push(w);
                    if w == u {
                        break;
                    }
                }
                scc_list.push(scc);
            }
        }

        fn build_spanning_tree_edges(
            &self,
            start: usize,
            graph: &[Vec<usize>],
            nodes: &HashSet<usize>,
        ) -> Vec<(usize, usize)> {
            let mut edges = Vec::new();
            let mut visited = HashSet::new();
            let mut st = vec![start];
            visited.insert(start);

            while let Some(node) = st.pop() {
                for &nb in &graph[node] {
                    if nodes.contains(&nb) && !visited.contains(&nb) {
                        edges.push((node, nb));
                        visited.insert(nb);
                        st.push(nb);
                    }
                }
            }
            edges
        }

        pub fn find_sccs(&self) -> Vec<Vec<usize>> {
            let mut disc = vec![-1i32; self.v];
            let mut low = vec![-1i32; self.v];
            let mut in_stack = vec![false; self.v];
            let mut stack = Vec::new();
            let mut scc_list = Vec::new();
            let mut timer = 0i32;

            for i in 0..self.v {
                if disc[i] == -1 {
                    self.tarjan_dfs(i, &mut disc, &mut low, &mut stack, &mut in_stack, &mut timer, &mut scc_list);
                }
            }
            scc_list
        }

        pub fn minimize_edges_in_scc(&self, scc: &[usize]) -> Vec<(usize, usize)> {
            let nodes: HashSet<usize> = scc.iter().copied().collect();
            let mut essential_edges = Vec::new();

            let forward_tree = self.build_spanning_tree_edges(scc[0], &self.adj, &nodes);
            let reverse_tree = self.build_spanning_tree_edges(scc[0], &self.rev_adj, &nodes);

            essential_edges.extend(forward_tree);
            essential_edges.extend(reverse_tree);

            essential_edges
        }

        pub fn reduce_edges(&self) -> Vec<(usize, usize)> {
            let mut sccs = self.find_sccs();
            if self.verbose {
                println!("Found {} SCC(s).", sccs.len());
            }

            // Sort SCCs deterministically by their minimum node index
            sccs.sort_by_key(|scc| *scc.iter().min().unwrap_or(&usize::MAX));

            // Threshold for parallelization
            const MIN_VERTICES_FOR_PARALLEL: usize = 1000;
            const MIN_SCCS_FOR_PARALLEL: usize = 4;

            let use_parallel = self.v >= MIN_VERTICES_FOR_PARALLEL && sccs.len() >= MIN_SCCS_FOR_PARALLEL;

            let reduced_edges = if use_parallel {
                // Parallel path using threads
                let num_threads = thread::available_parallelism()
                    .map(|n| n.get())
                    .unwrap_or(4);
                
                let chunk_size = (sccs.len() + num_threads - 1) / num_threads;
                let results = Arc::new(Mutex::new(vec![Vec::new(); sccs.len()]));
                
                let mut handles = vec![];
                
                for thread_id in 0..num_threads {
                    let start_idx = thread_id * chunk_size;
                    if start_idx >= sccs.len() {
                        break;
                    }
                    let end_idx = ((thread_id + 1) * chunk_size).min(sccs.len());
                    
                    let sccs_chunk: Vec<Vec<usize>> = sccs[start_idx..end_idx].to_vec();
                    let adj_clone = self.adj.clone();
                    let rev_adj_clone = self.rev_adj.clone();
                    let results_clone = Arc::clone(&results);
                    
                    let handle = thread::spawn(move || {
                        let temp_graph = Graph {
                            v: adj_clone.len(),
                            adj: adj_clone,
                            rev_adj: rev_adj_clone,
                            verbose: false,
                        };
                        
                        for (local_idx, scc) in sccs_chunk.iter().enumerate() {
                            let global_idx = start_idx + local_idx;
                            let edges = temp_graph.minimize_edges_in_scc(scc);
                            let mut res = results_clone.lock().unwrap();
                            res[global_idx] = edges;
                        }
                    });
                    
                    handles.push(handle);
                }
                
                for handle in handles {
                    handle.join().unwrap();
                }
                
                let results = Arc::try_unwrap(results).unwrap().into_inner().unwrap();
                let mut reduced = Vec::new();
                for edges in results {
                    reduced.extend(edges);
                }
                reduced
            } else {
                // Sequential fallback
                let mut reduced = Vec::new();
                for scc in &sccs {
                    let min_edges = self.minimize_edges_in_scc(scc);
                    reduced.extend(min_edges);
                }
                reduced
            };

            if self.verbose {
                println!("Reduced SCC edges: {}", reduced_edges.len());
            }
            reduced_edges
        }
    }
}

// Test harness
use std::collections::hash_map::DefaultHasher;
use std::hash::{Hash, Hasher};
use std::time::Instant;

fn hash_edges(edges: &[(usize, usize)]) -> u64 {
    let mut sorted = edges.to_vec();
    sorted.sort_unstable();
    let mut hasher = DefaultHasher::new();
    sorted.hash(&mut hasher);
    hasher.finish()
}

fn test_case_1_simple_cycle() -> (String, bool, bool) {
    let mut g_seq = scc_sequential::Graph::new(3);
    g_seq.add_edge(0, 1);
    g_seq.add_edge(1, 2);
    g_seq.add_edge(2, 0);

    let mut g_par = scc_parallel::Graph::new(3);
    g_par.add_edge(0, 1);
    g_par.add_edge(1, 2);
    g_par.add_edge(2, 0);

    let edges_seq = g_seq.reduce_edges();
    let edges_par1 = g_par.reduce_edges();
    let edges_par2 = g_par.reduce_edges();

    let hash_seq = hash_edges(&edges_seq);
    let hash_par1 = hash_edges(&edges_par1);
    let hash_par2 = hash_edges(&edges_par2);

    let correctness = hash_seq == hash_par1;
    let determinism = hash_par1 == hash_par2;

    (format!("simple_cycle: seq={:x} par1={:x} par2={:x}", hash_seq, hash_par1, hash_par2), correctness, determinism)
}

fn test_case_2_two_sccs() -> (String, bool, bool) {
    let mut g_seq = scc_sequential::Graph::new(4);
    g_seq.add_edge(0, 1);
    g_seq.add_edge(1, 0);
    g_seq.add_edge(2, 3);
    g_seq.add_edge(3, 2);

    let mut g_par = scc_parallel::Graph::new(4);
    g_par.add_edge(0, 1);
    g_par.add_edge(1, 0);
    g_par.add_edge(2, 3);
    g_par.add_edge(3, 2);

    let edges_seq = g_seq.reduce_edges();
    let edges_par1 = g_par.reduce_edges();
    let edges_par2 = g_par.reduce_edges();

    let hash_seq = hash_edges(&edges_seq);
    let hash_par1 = hash_edges(&edges_par1);
    let hash_par2 = hash_edges(&edges_par2);

    let correctness = hash_seq == hash_par1;
    let determinism = hash_par1 == hash_par2;

    (format!("two_sccs: seq={:x} par1={:x} par2={:x}", hash_seq, hash_par1, hash_par2), correctness, determinism)
}

fn test_case_3_empty() -> (String, bool, bool) {
    let g_seq = scc_sequential::Graph::new(0);
    let g_par = scc_parallel::Graph::new(0);

    let edges_seq = g_seq.reduce_edges();
    let edges_par1 = g_par.reduce_edges();
    let edges_par2 = g_par.reduce_edges();

    let hash_seq = hash_edges(&edges_seq);
    let hash_par1 = hash_edges(&edges_par1);
    let hash_par2 = hash_edges(&edges_par2);

    let correctness = hash_seq == hash_par1;
    let determinism = hash_par1 == hash_par2;

    (format!("empty: seq={:x} par1={:x} par2={:x}", hash_seq, hash_par1, hash_par2), correctness, determinism)
}

fn test_case_4_single_node() -> (String, bool, bool) {
    let g_seq = scc_sequential::Graph::new(1);
    let g_par = scc_parallel::Graph::new(1);

    let edges_seq = g_seq.reduce_edges();
    let edges_par1 = g_par.reduce_edges();
    let edges_par2 = g_par.reduce_edges();

    let hash_seq = hash_edges(&edges_seq);
    let hash_par1 = hash_edges(&edges_par1);
    let hash_par2 = hash_edges(&edges_par2);

    let correctness = hash_seq == hash_par1;
    let determinism = hash_par1 == hash_par2;

    (format!("single_node: seq={:x} par1={:x} par2={:x}", hash_seq, hash_par1, hash_par2), correctness, determinism)
}

fn test_case_5_medium() -> (String, bool, bool) {
    let n = 100;
    let mut g_seq = scc_sequential::Graph::new(n);
    let mut g_par = scc_parallel::Graph::new(n);

    for scc_id in 0..10 {
        let base = scc_id * 10;
        for i in 0..10 {
            let u = base + i;
            let v = base + ((i + 1) % 10);
            g_seq.add_edge(u, v);
            g_par.add_edge(u, v);
        }
    }

    let edges_seq = g_seq.reduce_edges();
    let edges_par1 = g_par.reduce_edges();
    let edges_par2 = g_par.reduce_edges();

    let hash_seq = hash_edges(&edges_seq);
    let hash_par1 = hash_edges(&edges_par1);
    let hash_par2 = hash_edges(&edges_par2);

    let correctness = hash_seq == hash_par1;
    let determinism = hash_par1 == hash_par2;

    (format!("medium: seq={:x} par1={:x} par2={:x}", hash_seq, hash_par1, hash_par2), correctness, determinism)
}

fn test_case_6_large() -> (String, bool, bool, f64, f64, f64) {
    let n = 5000;
    let mut g_seq = scc_sequential::Graph::new(n);
    let mut g_par = scc_parallel::Graph::new(n);

    for scc_id in 0..50 {
        let base = scc_id * 100;
        for i in 0..100 {
            let u = base + i;
            let v = base + ((i + 1) % 100);
            g_seq.add_edge(u, v);
            g_par.add_edge(u, v);
            if i % 3 == 0 {
                let w = base + ((i + 7) % 100);
                g_seq.add_edge(u, w);
                g_par.add_edge(u, w);
            }
        }
    }

    let start = Instant::now();
    let edges_seq = g_seq.reduce_edges();
    let t_seq = start.elapsed().as_secs_f64();

    let start = Instant::now();
    let edges_par1 = g_par.reduce_edges();
    let t_par1 = start.elapsed().as_secs_f64();

    let start = Instant::now();
    let edges_par2 = g_par.reduce_edges();
    let t_par2 = start.elapsed().as_secs_f64();

    let hash_seq = hash_edges(&edges_seq);
    let hash_par1 = hash_edges(&edges_par1);
    let hash_par2 = hash_edges(&edges_par2);

    let correctness = hash_seq == hash_par1;
    let determinism = hash_par1 == hash_par2;

    (format!("large: seq={:x} par1={:x} par2={:x}", hash_seq, hash_par1, hash_par2), correctness, determinism, t_seq, t_par1, t_par2)
}

fn main() {
    println!("=== SCC Parallel Differential Testing ===\n");

    let mut all_pass = true;
    let mut results = Vec::new();

    let (msg, corr, det) = test_case_1_simple_cycle();
    println!("Test 1 - Simple Cycle:");
    println!("  {}", msg);
    println!("  Correctness: {}, Determinism: {}", if corr { "PASS" } else { "FAIL" }, if det { "PASS" } else { "FAIL" });
    results.push(format!("Test 1 - Simple Cycle: Correctness={} Determinism={}", corr, det));
    all_pass = all_pass && corr && det;

    let (msg, corr, det) = test_case_2_two_sccs();
    println!("\nTest 2 - Two SCCs:");
    println!("  {}", msg);
    println!("  Correctness: {}, Determinism: {}", if corr { "PASS" } else { "FAIL" }, if det { "PASS" } else { "FAIL" });
    results.push(format!("Test 2 - Two SCCs: Correctness={} Determinism={}", corr, det));
    all_pass = all_pass && corr && det;

    let (msg, corr, det) = test_case_3_empty();
    println!("\nTest 3 - Empty Graph:");
    println!("  {}", msg);
    println!("  Correctness: {}, Determinism: {}", if corr { "PASS" } else { "FAIL" }, if det { "PASS" } else { "FAIL" });
    results.push(format!("Test 3 - Empty Graph: Correctness={} Determinism={}", corr, det));
    all_pass = all_pass && corr && det;

    let (msg, corr, det) = test_case_4_single_node();
    println!("\nTest 4 - Single Node:");
    println!("  {}", msg);
    println!("  Correctness: {}, Determinism: {}", if corr { "PASS" } else { "FAIL" }, if det { "PASS" } else { "FAIL" });
    results.push(format!("Test 4 - Single Node: Correctness={} Determinism={}", corr, det));
    all_pass = all_pass && corr && det;

    let (msg, corr, det) = test_case_5_medium();
    println!("\nTest 5 - Medium Graph (100 nodes, 10 SCCs):");
    println!("  {}", msg);
    println!("  Correctness: {}, Determinism: {}", if corr { "PASS" } else { "FAIL" }, if det { "PASS" } else { "FAIL" });
    results.push(format!("Test 5 - Medium: Correctness={} Determinism={}", corr, det));
    all_pass = all_pass && corr && det;

    let (msg, corr, det, t_seq, t_par1, t_par2) = test_case_6_large();
    println!("\nTest 6 - Large Graph (5000 nodes, 50 SCCs):");
    println!("  {}", msg);
    println!("  Correctness: {}, Determinism: {}", if corr { "PASS" } else { "FAIL" }, if det { "PASS" } else { "FAIL" });
    println!("  Sequential time: {:.6}s", t_seq);
    println!("  Parallel time (run 1): {:.6}s", t_par1);
    println!("  Parallel time (run 2): {:.6}s", t_par2);
    let speedup = if t_par1 > 0.0 { t_seq / t_par1 } else { 0.0 };
    println!("  Speedup: {:.2}x", speedup);
    results.push(format!("Test 6 - Large: Correctness={} Determinism={} t_seq={:.6}s t_par={:.6}s speedup={:.2}x", corr, det, t_seq, t_par1, speedup));
    all_pass = all_pass && corr && det;

    println!("\n=== Summary ===");
    println!("All tests passed: {}", if all_pass { "YES" } else { "NO" });

    let mut summary = String::new();
    summary.push_str("=== SCC Parallel Test Summary ===\n\n");
    for result in &results {
        summary.push_str(&format!("{}\n", result));
    }
    summary.push_str(&format!("\nAll tests passed: {}\n", if all_pass { "YES" } else { "NO" }));
    
    if let Err(e) = std::fs::write("run_summary.txt", summary) {
        eprintln!("Failed to write run_summary.txt: {}", e);
    }

    let num_threads = std::thread::available_parallelism()
        .map(|n| n.get())
        .unwrap_or(4);
    
    let perf_data = format!(
        "=== Performance Results ===\n\
         Test: Large Graph (5000 nodes, 50 SCCs)\n\
         Sequential time: {:.6}s\n\
         Parallel time: {:.6}s\n\
         Speedup: {:.2}x\n\
         Threads: {}\n",
        t_seq, t_par1, speedup, num_threads
    );
    
    if let Err(e) = std::fs::write("perf.txt", perf_data) {
        eprintln!("Failed to write perf.txt: {}", e);
    }

    std::process::exit(if all_pass { 0 } else { 1 });
}
