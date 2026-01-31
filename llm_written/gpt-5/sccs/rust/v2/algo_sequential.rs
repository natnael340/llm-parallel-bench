use std::collections::HashSet;

pub mod seq {
    use super::*;

    pub struct Graph {
        v: usize,
        pub(crate) adj: Vec<Vec<usize>>, // crate-visible for runner wiring
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
        pub fn vertex_count(&self) -> usize { self.v }
        pub fn neighbors(&self, u: usize) -> &[usize] { &self.adj[u] }

        // Tarjan's SCC DFS
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

        // Build a DFS spanning tree over 'graph' restricted to membership mask
        fn build_spanning_tree_edges_mask(
            &self,
            start: usize,
            graph: &[Vec<usize>],
            in_scc: &[u8],
        ) -> Vec<(usize, usize)> {
            let mut edges = Vec::new();
            let mut visited: HashSet<usize> = HashSet::new();
            if in_scc.get(start).copied().unwrap_or(0) == 0 { return edges; }
            let mut st = vec![start];
            visited.insert(start);

            while let Some(node) = st.pop() {
                for &nb in &graph[node] {
                    if in_scc[nb] != 0 && !visited.contains(&nb) {
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
            // Build membership mask for O(1) checks
            let mut mask = vec![0u8; self.v];
            for &u in scc { mask[u] = 1; }

            // At most (|SCC|-1) edges per tree
            let mut essential_edges = Vec::with_capacity(2 * scc.len().saturating_sub(1));

            // Step 1: forward spanning tree using DFS
            let forward_tree = self.build_spanning_tree_edges_mask(scc[0], &self.adj, &mask);
            // Step 2: reverse spanning tree using DFS on the reversed graph
            let reverse_tree = self.build_spanning_tree_edges_mask(scc[0], &self.rev_adj, &mask);
            // Step 3: Merge both trees (fixed order for determinism)
            essential_edges.extend(forward_tree);
            essential_edges.extend(reverse_tree);
            essential_edges
        }

        pub fn reduce_edges(&self) -> Vec<(usize, usize)> {
            let sccs = self.find_sccs();
            if self.verbose { println!("Found {} SCC(s).", sccs.len()); }
            let mut reduced_edges = Vec::new();
            for scc in &sccs {
                let min_edges = self.minimize_edges_in_scc(scc);
                reduced_edges.extend(min_edges);
            }
            if self.verbose { println!("Reduced SCC edges: {}", reduced_edges.len()); }
            reduced_edges
        }
    }
}
