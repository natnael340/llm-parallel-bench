
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
        if scc.is_empty() || scc.len() == 1 {
            return Vec::new();
        }
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
