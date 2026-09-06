use bench_rust::bench_utils;
use bench_rust::staged::{bench_bfs, Graph};

fn check(ok: bool, name: &str, failures: &mut i32) {
    println!("{} {}", name, if ok { "passed" } else { "failed" });
    if !ok {
        *failures += 1;
    }
}

fn main() {
    let mut failures = 0;

    // Empty graph
    {
        let g = Graph::new();
        check(bench_bfs(&g, 1).is_empty(), "test_bfs_empty", &mut failures);
    }
    // Linear
    {
        let mut g = Graph::new();
        g.add_edge(1, 2);
        g.add_edge(2, 3);
        g.add_edge(3, 4);
        check(bench_bfs(&g, 1) == vec![1, 2, 3, 4], "test_bfs_linear", &mut failures);
    }
    // Complete graph of 4
    {
        let mut g = Graph::new();
        let nodes = [1, 2, 3, 4];
        for &i in &nodes {
            for &j in &nodes {
                if i != j {
                    g.add_edge(i, j);
                }
            }
        }
        check(bench_bfs(&g, 3) == vec![3, 1, 2, 4], "test_bfs_complete", &mut failures);
    }
    // Disconnected components
    {
        let mut g = Graph::new();
        g.add_edge(1, 2);
        g.add_edge(2, 3);
        g.add_edge(4, 5);
        g.add_edge(4, 6);
        check(bench_bfs(&g, 1) == vec![1, 2, 3], "test_bfs_disconnected", &mut failures);
    }
    // Nonexistent start
    {
        let mut g = Graph::new();
        g.add_edge(1, 2);
        check(bench_bfs(&g, 999).is_empty(), "test_bfs_nonexistent_start", &mut failures);
    }

    if failures > 0 {
        println!("{} test(s) failed — skipping benchmark", failures);
        std::process::exit(1);
    }

    // Perf: complete graph, size 2000.
    let size: i32 = 2000;
    let mut g = Graph::new();
    for i in 1..=size {
        for j in (i + 1)..=size {
            g.add_edge(i, j);
            g.add_edge(j, i);
        }
    }

    let reps = bench_utils::reps(5);
    let iters = bench_utils::iters(20);
    let r = bench_utils::run_benchmark(|| { bench_bfs(&g, 1); }, reps, iters, 1);

    println!("{}", bench_utils::format_result("BFS complete graph", &r));
    let params = format!("{{\"graph_size\": {}, \"graph_kind\": \"complete\"}}", size);
    bench_utils::write_result(&r, "bfs", &bench_utils::impl_name(), &params);
}
