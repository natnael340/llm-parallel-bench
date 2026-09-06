pub mod seq;

#[cfg(test)]
mod tests {
    use crate::seq::Graph;

    use rand::{Rng, SeedableRng};
    use rand::rngs::StdRng;
    use std::collections::HashSet;

    fn equal_nested(a: &[Vec<usize>], b: &[Vec<usize>]) -> bool {
        if a.len() != b.len() {
            return false;
        }
        let set_a: HashSet<Vec<usize>> = a.iter().map(|s| {
            let mut v = s.clone();
            v.sort();
            v
        }).collect();
        let set_b: HashSet<Vec<usize>> = b.iter().map(|s| {
            let mut v = s.clone();
            v.sort();
            v
        }).collect();
        set_a == set_b
    }

    fn sort_edges(edges: &mut [(usize, usize)]) {
        edges.sort_by(|a, b| a.0.cmp(&b.0).then(a.1.cmp(&b.1)));
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
        assert!(equal_nested(&g.find_sccs(), &[vec![0]]));
        assert!(g.reduce_edges().is_empty());
    }

    #[test]
    fn test_singleton_self_loop() {
        let mut g = Graph::new(1);
        g.add_edge(0, 0);
        assert!(equal_nested(&g.find_sccs(), &[vec![0]]));
        assert!(g.reduce_edges().is_empty());
    }

    #[test]
    fn test_simple_cycle_3() {
        // 0->1->2->0
        // Tarjan gives SCC=[2,1,0], scc[0]=2
        //   forward from 2: (2,0),(0,1)
        //   reverse from 2: (2,1),(1,0)
        let mut g = Graph::new(3);
        g.add_edge(0, 1);
        g.add_edge(1, 2);
        g.add_edge(2, 0);
        assert!(equal_nested(&g.find_sccs(), &[vec![0, 1, 2]]));

        let expected = vec![(2, 0), (0, 1), (2, 1), (1, 0)];
        expect_same_multiset(g.reduce_edges(), expected, "test_simple_cycle_3");
    }

    #[test]
    fn test_two_node_mutual_scc() {
        // 0<->1
        // Tarjan gives SCC=[1,0], scc[0]=1
        //   forward from 1: (1,0)
        //   reverse from 1: (1,0)
        let mut g = Graph::new(2);
        g.add_edge(0, 1);
        g.add_edge(1, 0);
        assert!(equal_nested(&g.find_sccs(), &[vec![0, 1]]));

        let expected = vec![(1, 0), (1, 0)];
        expect_same_multiset(g.reduce_edges(), expected, "test_two_node_mutual_scc");
    }

    #[test]
    fn test_dense_three_node_scc() {
        // All 6 edges among {0,1,2} (added: 0->1,1->2,2->0,0->2,2->1,1->0)
        // adj[2]=[0,1], Tarjan gives SCC=[2,1,0], scc[0]=2
        //   forward from 2: (2,0),(2,1)  [adj[2]=[0,1], both unvisited from node 2]
        //   reverse from 2: (2,1),(2,0)  [rev_adj[2]=[1,0], same pattern]
        let mut g = Graph::new(3);
        for (u, v) in [(0, 1), (1, 2), (2, 0), (0, 2), (2, 1), (1, 0)] {
            g.add_edge(u, v);
        }
        assert!(equal_nested(&g.find_sccs(), &[vec![0, 1, 2]]));

        let expected = vec![(2, 0), (2, 1), (2, 1), (2, 0)];
        expect_same_multiset(g.reduce_edges(), expected, "test_dense_three_node_scc");
    }

    #[test]
    fn test_multiple_sccs_with_cross() {
        // SCC1: 0->1->2->0  Tarjan root=2: forward (2,0),(0,1); reverse (2,1),(1,0)
        // SCC2: 3<->4        Tarjan root=4: forward (4,3);       reverse (4,3)
        // cross: 2->3
        let mut g = Graph::new(5);
        g.add_edge(0, 1); g.add_edge(1, 2); g.add_edge(2, 0);
        g.add_edge(3, 4); g.add_edge(4, 3);
        g.add_edge(2, 3);

        assert!(equal_nested(&g.find_sccs(), &[vec![0, 1, 2], vec![3, 4]]));

        let expected = vec![(4, 3), (4, 3), (2, 0), (0, 1), (2, 1), (1, 0)];
        let reduced = g.reduce_edges();
        assert_eq!(reduced.len(), expected.len());
        expect_same_multiset(reduced, expected, "test_multiple_sccs_with_cross");
    }

    #[test]
    fn test_disconnected_with_dag_component() {
        // SCC {0,1,2}: 0->1->2->0  Tarjan root=2: forward (2,0),(0,1); reverse (2,1),(1,0)
        // Singletons {3},{4},{5}: 3->4->5 (DAG, no SCC edges)
        let mut g = Graph::new(6);
        g.add_edge(0, 1); g.add_edge(1, 2); g.add_edge(2, 0);
        g.add_edge(3, 4); g.add_edge(4, 5);

        assert!(equal_nested(&g.find_sccs(), &[vec![0, 1, 2], vec![3], vec![4], vec![5]]));

        let expected = vec![(2, 0), (0, 1), (2, 1), (1, 0)];
        let reduced = g.reduce_edges();
        assert_eq!(reduced.len(), expected.len());
        expect_same_multiset(reduced, expected, "test_disconnected_with_dag_component");
    }

    #[test]
    fn test_star_like_scc() {
        // 0 connected both ways with 1..6 => single SCC
        // Tarjan gives SCC=[6,5,4,3,2,1,0], scc[0]=6
        //   forward from 6: (6,0),(0,1),(0,2),(0,3),(0,4),(0,5)
        //   reverse from 6: (6,0),(0,1),(0,2),(0,3),(0,4),(0,5)  [same structure]
        let n = 7;
        let mut g = Graph::new(n);
        for i in 1..n {
            g.add_edge(0, i);
            g.add_edge(i, 0);
        }

        assert!(equal_nested(&g.find_sccs(), &[(0..n).collect::<Vec<_>>()]));

        let mut expected = vec![(6usize, 0usize)];
        for i in 1..n - 1 { expected.push((0, i)); }
        expected.push((6, 0));
        for i in 1..n - 1 { expected.push((0, i)); }

        let reduced = g.reduce_edges();
        assert_eq!(reduced.len(), expected.len());
        expect_same_multiset(reduced, expected, "test_star_like_scc");
    }

    #[test]
    fn test_large_ring_scc() {
        // Ring 0->1->...->299->0
        // Tarjan gives SCC=[299,298,...,0], scc[0]=299
        //   forward from 299: (299,0),(0,1),(1,2),...,(297,298)   = n-1 edges
        //   reverse from 299: (299,298),(298,297),...,(1,0)         = n-1 edges
        let n = 300;
        let mut g = Graph::new(n);
        for i in 0..n {
            g.add_edge(i, (i + 1) % n);
        }

        assert!(equal_nested(&g.find_sccs(), &[(0..n).collect::<Vec<_>>()]));

        let mut expected = Vec::new();
        expected.push((n - 1, 0));                             // forward start: 299->0
        for i in 0..n - 2 { expected.push((i, i + 1)); }     // forward rest: 0->1,...,297->298
        for i in (1..n).rev() { expected.push((i, i - 1)); } // reverse: 299->298,...,1->0

        let reduced = g.reduce_edges();
        assert_eq!(reduced.len(), expected.len());
        expect_same_multiset(reduced, expected, "test_large_ring_scc");
    }

    #[test]
    fn test_random_sccs() {
        for trial in 0..5 {
            let n = 80;
            let mut g = Graph::new(n);
            for i in 0..n {
                g.add_edge(i, (i + 1) % n);
            }

            let mut rng = StdRng::seed_from_u64(2025 + trial as u64);
            for _ in 0..(n * 2) {
                let u = rng.gen_range(0..n);
                let v = rng.gen_range(0..n);
                if u != v {
                    g.add_edge(u, v);
                }
            }

            assert!(
                equal_nested(&g.find_sccs(), &[(0..n).collect::<Vec<_>>()]),
                "trial {}: SCC mismatch", trial
            );

            let reduced = g.reduce_edges();
            assert_eq!(reduced.len(), 2 * (n - 1), "trial {}: size mismatch", trial);
        }
    }

    #[test]
    fn test_determinism() {
        let num_scc = 24;
        let scc_size = 40;
        let n = num_scc * scc_size;
        let runs = 5;

        let seed: u64 = rand::thread_rng().gen();
        let mut rng = StdRng::seed_from_u64(seed);

        let mut g = Graph::new(n);
        for s in 0..num_scc {
            let start = s * scc_size;
            for u in start..start + scc_size {
                let nxt = start + (u - start + 1) % scc_size;
                g.add_edge(u, nxt);
            }
            for _ in 0..scc_size * 3 {
                let u = start + rng.gen_range(0..scc_size);
                let v = start + rng.gen_range(0..scc_size);
                if u != v {
                    g.add_edge(u, v);
                }
            }
        }
        for s in 0..num_scc - 1 {
            let a0 = s * scc_size;
            let b0 = (s + 1) * scc_size;
            for _ in 0..6 {
                let u = a0 + rng.gen_range(0..scc_size);
                let v = b0 + rng.gen_range(0..scc_size);
                g.add_edge(u, v);
            }
        }

        let baseline = g.reduce_edges();
        for r in 1..runs {
            let edges = g.reduce_edges();
            assert_eq!(
                edges, baseline,
                "run {r}: output differs from run 0 (seed={seed}, baseline_len={}, this_len={})",
                baseline.len(), edges.len()
            );
        }
    }
}
