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

    // Tarjan's SCC DFS (kept sequential - inherently serial algorithm)
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

    // Build a DFS spanning tree over 'graph' restricted to 'nodes'
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

    // Tarjan's SCC (O(V+E)) - kept sequential
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

    // Minimal SCC Edge Reduction (O(V+E))
    pub fn minimize_edges_in_scc(&self, scc: &[usize]) -> Vec<(usize, usize)> {
        let nodes: HashSet<usize> = scc.iter().copied().collect();
        let mut essential_edges = Vec::new();

        // Step 1: forward spanning tree using DFS
        let forward_tree = self.build_spanning_tree_edges(scc[0], &self.adj, &nodes);

        // Step 2: reverse spanning tree using DFS on the reversed graph
        let reverse_tree = self.build_spanning_tree_edges(scc[0], &self.rev_adj, &nodes);

        // Step 3: Merge both trees
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
        // This ensures same processing order every time
        sccs.sort_by_key(|scc| *scc.iter().min().unwrap_or(&usize::MAX));

        // Threshold for parallelization: use parallel only if enough work
        const MIN_VERTICES_FOR_PARALLEL: usize = 1000;
        const MIN_SCCS_FOR_PARALLEL: usize = 4;

        let use_parallel = self.v >= MIN_VERTICES_FOR_PARALLEL && sccs.len() >= MIN_SCCS_FOR_PARALLEL;

        let reduced_edges = if use_parallel {
            // Parallel path: process each SCC independently using bounded thread pool
            let num_threads = thread::available_parallelism()
                .map(|n| n.get())
                .unwrap_or(4);
            
            let chunk_size = (sccs.len() + num_threads - 1) / num_threads;
            
            // Pre-allocate results vector with correct size
            let results = Arc::new(Mutex::new(vec![Vec::new(); sccs.len()]));
            
            let mut handles = vec![];
            
            for thread_id in 0..num_threads {
                let start_idx = thread_id * chunk_size;
                if start_idx >= sccs.len() {
                    break;
                }
                let end_idx = ((thread_id + 1) * chunk_size).min(sccs.len());
                
                // Clone data needed for this thread
                let sccs_chunk: Vec<Vec<usize>> = sccs[start_idx..end_idx].to_vec();
                let adj_clone = self.adj.clone();
                let rev_adj_clone = self.rev_adj.clone();
                let results_clone = Arc::clone(&results);
                
                let handle = thread::spawn(move || {
                    // Create a temporary graph for this thread
                    let temp_graph = Graph {
                        v: adj_clone.len(),
                        adj: adj_clone,
                        rev_adj: rev_adj_clone,
                        verbose: false,
                    };
                    
                    // Process each SCC in this chunk
                    for (local_idx, scc) in sccs_chunk.iter().enumerate() {
                        let global_idx = start_idx + local_idx;
                        let edges = temp_graph.minimize_edges_in_scc(scc);
                        
                        // Store result at the correct index
                        let mut res = results_clone.lock().unwrap();
                        res[global_idx] = edges;
                    }
                });
                
                handles.push(handle);
            }
            
            // Wait for all threads to complete
            for handle in handles {
                handle.join().unwrap();
            }
            
            // Flatten results in deterministic order (same order as sorted SCCs)
            let results = Arc::try_unwrap(results).unwrap().into_inner().unwrap();
            let mut reduced = Vec::new();
            for edges in results {
                reduced.extend(edges);
            }
            reduced
        } else {
            // Sequential fallback for small inputs
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
