use std::collections::HashSet;

pub mod par {
    use super::*;
    use rayon::prelude::*;

    pub struct Graph {
        v: usize,
        adj: Vec<Vec<usize>>,
        rev_adj: Vec<Vec<usize>>,
        pub verbose: bool,
    }

    impl Graph {
        pub fn new(v: usize) -> Self { Self::with_verbose(v, false) }
        pub fn with_verbose(v: usize, verbose: bool) -> Self {
            Graph { v, adj: vec![Vec::new(); v], rev_adj: vec![Vec::new(); v], verbose }
        }
        pub fn add_edge(&mut self, v: usize, w: usize) {
            self.adj[v].push(w);
            self.rev_adj[w].push(v);
        }

        // Tarjan's SCC DFS (sequential)
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
                } else if in_stack[v] { low[u] = low[u].min(disc[v]); }
            }

            if low[u] == disc[u] {
                let mut scc = Vec::new();
                loop {
                    let w = stack.pop().unwrap();
                    in_stack[w] = false;
                    scc.push(w);
                    if w == u { break; }
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
            let mut visited: HashSet<usize> = HashSet::new();
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

        // Tarjan's SCC (O(V+E))
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
            if scc.is_empty() { return Vec::new(); }
            let nodes: HashSet<usize> = scc.iter().copied().collect();
            let mut essential_edges = Vec::new();
            let forward_tree = self.build_spanning_tree_edges(scc[0], &self.adj, &nodes);
            let reverse_tree = self.build_spanning_tree_edges(scc[0], &self.rev_adj, &nodes);
            essential_edges.extend(forward_tree);
            essential_edges.extend(reverse_tree);
            essential_edges
        }

        fn edge_count(&self) -> usize { self.adj.iter().map(|v| v.len()).sum() }

        pub fn reduce_edges_parallel(&self) -> Vec<(usize, usize)> {
            // Always compute SCCs sequentially for correctness and determinism
            let sccs = self.find_sccs();
            if self.verbose { println!("Found {} SCC(s).", sccs.len()); }

            // Small-N fallback to avoid parallel overhead
            let small = self.v <= 1024 || sccs.len() <= 2;
            if small {
                let mut reduced_edges = Vec::new();
                for scc in &sccs { reduced_edges.extend(self.minimize_edges_in_scc(scc)); }
                if self.verbose { println!("Reduced SCC edges: {}", reduced_edges.len()); }
                return reduced_edges;
            }

            // Parallel over SCCs but collect in original order for determinism
            let per_scc: Vec<Vec<(usize, usize)>> = sccs
                .par_iter()
                .map(|scc| self.minimize_edges_in_scc(scc))
                .collect(); // IndexedParallelIterator preserves order

            let total_len: usize = per_scc.iter().map(|v| v.len()).sum();
            let mut reduced_edges = Vec::with_capacity(total_len);
            for v in per_scc { reduced_edges.extend(v); }
            if self.verbose { println!("Reduced SCC edges: {}", reduced_edges.len()); }
            reduced_edges
        }
    }
}
