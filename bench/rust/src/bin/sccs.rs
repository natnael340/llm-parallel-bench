use bench_rust::bench_utils;
use bench_rust::staged::{bench_reduce_edges, Graph};
use std::collections::HashSet;

// Correctness: SCC strong-check heuristic (mirrors the Go harness).
// For SCC of size k>1: (k-1) <= internal edges <= 2*(k-1), and every SCC
// node appears in at least one kept internal edge.
fn is_scc_strong(scc: &[usize], edges: &[(usize, usize)]) -> bool {
    let node_set: HashSet<usize> = scc.iter().copied().collect();
    let k = scc.len();
    if k <= 1 {
        return true;
    }
    let mut internal = 0;
    let mut touched: HashSet<usize> = HashSet::new();
    for &(u, v) in edges {
        if node_set.contains(&u) && node_set.contains(&v) {
            internal += 1;
            touched.insert(u);
            touched.insert(v);
        }
    }
    internal >= k - 1 && internal <= 2 * (k - 1) && touched.len() >= k
}

fn check_all(g: &Graph) -> bool {
    let edges = bench_reduce_edges(g);
    g.find_sccs().iter().all(|scc| is_scc_strong(scc, &edges))
}

// Random multi-SCC graph; reduce_edges must return byte-identical output across runs.
fn check_determinism() -> bool {
    let (num_scc, scc_size, runs) = (24usize, 40usize, 5);
    let seed = std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .map_or(1, |d| d.as_nanos() as u64)
        | 1;
    let mut state = seed;
    let mut pick = || {
        state ^= state << 13;
        state ^= state >> 7;
        state ^= state << 17;
        (state % scc_size as u64) as usize
    };

    let mut g = Graph::new(num_scc * scc_size);
    for s in 0..num_scc {
        let start = s * scc_size;
        for u in start..start + scc_size {
            g.add_edge(u, start + (u - start + 1) % scc_size);
        }
        for _ in 0..scc_size * 3 {
            let (u, v) = (start + pick(), start + pick());
            if u != v {
                g.add_edge(u, v);
            }
        }
    }
    for s in 0..num_scc - 1 {
        for _ in 0..6 {
            let (u, v) = (s * scc_size + pick(), (s + 1) * scc_size + pick());
            g.add_edge(u, v);
        }
    }

    let sccs = g.find_sccs();
    let mut first: Option<Vec<(usize, usize)>> = None;
    for r in 0..runs {
        let edges = bench_reduce_edges(&g);
        if !sccs.iter().all(|scc| is_scc_strong(scc, &edges)) {
            println!("determinism run {}: reduced edges broke SCC (seed={})", r, seed);
            return false;
        }
        match &first {
            None => first = Some(edges),
            Some(f) if *f != edges => {
                println!("determinism run {}: output differs from run 0 (seed={})", r, seed);
                return false;
            }
            _ => {}
        }
    }
    true
}

fn check(ok: bool, name: &str, failures: &mut i32) {
    println!("{} {}", name, if ok { "passed" } else { "failed" });
    if !ok {
        *failures += 1;
    }
}

fn ring_scc(start: usize, end: usize, g: &mut Graph) {
    for i in start..end {
        let mut v = (i + 1) % end;
        if v == 0 {
            v = start;
        }
        if i == v {
            continue;
        }
        g.add_edge(i, v);
    }
}

fn main() {
    let mut failures = 0;

    // simple 3-cycle
    {
        let mut g = Graph::new(3);
        g.add_edge(0, 1);
        g.add_edge(1, 2);
        g.add_edge(2, 0);
        check(check_all(&g), "test_scc_3cycle", &mut failures);
    }
    // two-node mutual SCC
    {
        let mut g = Graph::new(2);
        g.add_edge(0, 1);
        g.add_edge(1, 0);
        check(check_all(&g), "test_scc_2node_mutual", &mut failures);
    }
    // multiple SCCs with a cross edge
    {
        let mut g = Graph::new(5);
        g.add_edge(0, 1);
        g.add_edge(1, 2);
        g.add_edge(2, 0);
        g.add_edge(3, 4);
        g.add_edge(4, 3);
        g.add_edge(2, 3);
        check(check_all(&g), "test_scc_multiple", &mut failures);
    }
    // 7-node example graph
    {
        let mut g = Graph::new(7);
        for &(u, v) in &[
            (0usize, 1usize), (1, 2), (1, 3), (1, 4), (2, 0), (2, 3),
            (3, 5), (5, 3), (5, 4), (5, 6), (6, 4), (4, 6),
        ] {
            g.add_edge(u, v);
        }
        check(check_all(&g), "test_scc_7node", &mut failures);
    }
    check(check_determinism(), "test_scc_determinism", &mut failures);

    let rc = if failures > 0 {
        println!("{} test(s) failed — benchmarking anyway", failures);
        1
    } else {
        0
    };

    // Perf: clustered graph (shared with all languages).
    let graph_size = 100_000usize;
    let cluster_size = 300usize;
    let no_cluster_in_group = 3usize;

    let mut g = Graph::new(graph_size);
    let mut i = 0;
    while i < graph_size {
        ring_scc(i, (i + cluster_size).min(graph_size), &mut g);
        let current_cluster = i / cluster_size;
        if current_cluster / no_cluster_in_group == (current_cluster + 1) / no_cluster_in_group
            && (i + cluster_size) < graph_size
        {
            let end_a = (i + cluster_size).min(graph_size);
            let end_b = (i + 2 * cluster_size).min(graph_size);
            // Deterministic pick within range (no RNG dependency).
            let u = i + ((i * 2654435761) % (end_a - i));
            let v = end_a + ((i * 40503) % (end_b - end_a));
            g.add_edge(u, v);
        }
        i += cluster_size;
    }

    if bench_utils::digest_out().is_some() {
        let edges = bench_reduce_edges(&g);
        let mut out = String::new();
        for scc in g.find_sccs() {
            let nodes: Vec<String> = scc.iter().map(|v| v.to_string()).collect();
            out.push_str(&format!("S {}\n", nodes.join(" ")));
        }
        for (u, v) in &edges {
            out.push_str(&format!("E {} {}\n", u, v));
        }
        bench_utils::write_digest(&out);
        std::process::exit(rc);
    }

    let reps = bench_utils::reps(5);
    let iters = bench_utils::iters(20);
    let r = bench_utils::run_benchmark(|| { bench_reduce_edges(&g); }, reps, iters, 1);

    println!("{}", bench_utils::format_result(&format!("SCC ReduceEdges | graph_size={}", graph_size), &r));
    let params = format!(
        "{{\"graph_size\": {}, \"cluster_size\": {}, \"no_cluster_in_group\": {}}}",
        graph_size, cluster_size, no_cluster_in_group
    );
    bench_utils::write_result(&r, "sccs", &bench_utils::impl_name(), &params);
    std::process::exit(rc);
}
