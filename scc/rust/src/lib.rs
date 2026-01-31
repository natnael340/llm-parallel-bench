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

#[cfg(test)]
mod tests {
    use super::*;
    use rand::{Rng, SeedableRng};
    use rand::rngs::StdRng;

    fn sort_edges(edges: &mut [(usize, usize)]) {
        edges.sort_by(|a, b| {
            if a.0 != b.0 {
                a.0.cmp(&b.0)
            } else {
                a.1.cmp(&b.1)
            }
        });
    }

    fn expect_same_multiset(mut a: Vec<(usize, usize)>, mut b: Vec<(usize, usize)>, test_name: &str) {
        sort_edges(&mut a);
        sort_edges(&mut b);

        if a != b {
            eprintln!("\n--- Multiset mismatch in {} ---", test_name);
            eprintln!("left (got)  size={}", a.len());
            for e in a.iter().take(20) {
                eprintln!("  {},{}", e.0, e.1);
            }
            if a.len() > 20 {
                eprintln!("  ...({} more)", a.len() - 20);
            }

            eprintln!("right (exp) size={}", b.len());
            for e in b.iter().take(20) {
                eprintln!("  {},{}", e.0, e.1);
            }
            if b.len() > 20 {
                eprintln!("  ...({} more)", b.len() - 20);
            }

            if a.len() == b.len() {
                for i in 0..a.len() {
                    if a[i] != b[i] {
                        eprintln!(
                            "first diff at idx {} got=({},{}) exp=({},{})",
                            i, a[i].0, a[i].1, b[i].0, b[i].1
                        );
                        break;
                    }
                }
            }
            eprintln!("-------------------------");
            panic!("multiset equality failed in {}", test_name);
        }
    }

    #[test]
    fn test_empty_graph() {
        let g = Graph::new(0);
        assert!(g.find_sccs().is_empty());
        assert!(g.reduce_edges().is_empty());
    }

    #[test]
    fn test_singleton_no_edges() {
        let g = Graph::new(1);
        assert_eq!(g.find_sccs(), vec![vec![0]]);
        assert!(g.reduce_edges().is_empty());
    }

    #[test]
    fn test_singleton_self_loop() {
        let mut g = Graph::new(1);
        g.add_edge(0, 0);
        assert_eq!(g.find_sccs(), vec![vec![0]]);
        assert!(g.reduce_edges().is_empty());
    }

    #[test]
    fn test_simple_cycle_3() {
        let mut g = Graph::new(3);
        g.add_edge(0, 1);
        g.add_edge(1, 2);
        g.add_edge(2, 0);
        assert_eq!(g.find_sccs(), vec![vec![2, 1, 0]]);

        let expected = vec![(2, 0), (0, 1), (2, 1), (1, 0)];
        expect_same_multiset(g.reduce_edges(), expected, "test_simple_cycle_3");
    }

    #[test]
    fn test_two_node_mutual_scc() {
        let mut g = Graph::new(2);
        g.add_edge(0, 1);
        g.add_edge(1, 0);
        assert_eq!(g.find_sccs(), vec![vec![1, 0]]);

        let expected = vec![(1, 0), (1, 0)];
        expect_same_multiset(g.reduce_edges(), expected, "test_two_node_mutual_scc");
    }

    #[test]
    fn test_dense_three_node_scc() {
        let mut g = Graph::new(3);
        for (u, v) in [(0, 1), (1, 2), (2, 0), (0, 2), (2, 1), (1, 0)] {
            g.add_edge(u, v);
        }
        assert_eq!(g.find_sccs(), vec![vec![2, 1, 0]]);

        let expected = vec![(2, 0), (2, 1), (2, 0), (2, 1)];
        expect_same_multiset(g.reduce_edges(), expected, "test_dense_three_node_scc");
    }

    #[test]
    fn test_multiple_sccs_with_cross() {
        // SCC1: 0->1->2->0; SCC2: 3<->4; cross 2->3
        let mut g = Graph::new(5);
        g.add_edge(0, 1);
        g.add_edge(1, 2);
        g.add_edge(2, 0);
        g.add_edge(3, 4);
        g.add_edge(4, 3);
        g.add_edge(2, 3);

        let expected_sccs = vec![vec![4, 3], vec![2, 1, 0]];
        assert_eq!(g.find_sccs(), expected_sccs);

        let expected = vec![(4, 3), (4, 3), (2, 0), (0, 1), (2, 1), (1, 0)];
        let reduced = g.reduce_edges();
        assert_eq!(reduced.len(), expected.len());
        expect_same_multiset(reduced, expected, "test_multiple_sccs_with_cross");
    }

    #[test]
    fn test_disconnected_with_dag_component() {
        // SCC: 0,1,2 ; DAG piece: 3->4->5
        let mut g = Graph::new(6);
        g.add_edge(0, 1);
        g.add_edge(1, 2);
        g.add_edge(2, 0);
        g.add_edge(3, 4);
        g.add_edge(4, 5);

        let expected_sccs = vec![vec![2, 1, 0], vec![5], vec![4], vec![3]];
        assert_eq!(g.find_sccs(), expected_sccs);

        let expected = vec![(2, 0), (0, 1), (2, 1), (1, 0)];
        let reduced = g.reduce_edges();
        assert_eq!(reduced.len(), expected.len());
        expect_same_multiset(reduced, expected, "test_disconnected_with_dag_component");
    }

    #[test]
    fn test_star_like_scc() {
        // 0 connected both ways with leaves => single SCC
        let n = 7;
        let mut g = Graph::new(n);
        for i in 1..n {
            g.add_edge(0, i);
            g.add_edge(i, 0);
        }

        let scc: Vec<usize> = (0..n).rev().collect();
        assert_eq!(g.find_sccs(), vec![scc]);

        let expected = vec![
            (6, 0), (6, 0), (0, 1), (0, 2), (0, 3), (0, 4), (0, 5),
            (0, 1), (0, 2), (0, 3), (0, 4), (0, 5),
        ];
        let reduced = g.reduce_edges();
        assert_eq!(reduced.len(), expected.len());
        expect_same_multiset(reduced, expected, "test_star_like_scc");
    }

    #[test]
    fn test_large_ring_scc() {
        let n = 300;
        let mut g = Graph::new(n);
        let mut expected = Vec::new();

        for i in 0..n {
            g.add_edge(i, (i + 1) % n);
            if (i + 1) != n - 1 {
                expected.push((i, (i + 1) % n));
            }
            if i != 0 {
                expected.push((i, (i + n - 1) % n));
            }
        }

        let scc: Vec<usize> = (0..n).rev().collect();
        assert_eq!(g.find_sccs(), vec![scc]);

        let reduced = g.reduce_edges();
        assert_eq!(reduced.len(), expected.len());
        expect_same_multiset(reduced, expected, "test_large_ring_scc");
    }

    #[test]
    fn test_random_sccs() {
        for trial in 0..5 {
            let n = 80;
            let mut g = Graph::new(n);
            let mut expected = Vec::new();

            for i in 0..n {
                g.add_edge(i, (i + 1) % n);
                if (i + 1) != n - 1 {
                    expected.push((i, (i + 1) % n));
                }
                if i != 0 {
                    expected.push((i, (i + n - 1) % n));
                }
            }

            let mut rng = StdRng::seed_from_u64(2025 + trial as u64);
            for _ in 0..(n * 2) {
                let u = rng.gen_range(0..n);
                let v = rng.gen_range(0..n);
                if u != v {
                    g.add_edge(u, v);
                }
            }

            let scc: Vec<usize> = (0..n).rev().collect();
            assert_eq!(g.find_sccs(), vec![scc], "trial {}: SCC mismatch", trial);

            let reduced = g.reduce_edges();
            assert_eq!(reduced.len(), expected.len(), "trial {}: size mismatch", trial);
        }
    }
}
