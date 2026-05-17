// Runner and tests for parallel BFS
// It includes the implementation from algo_parallel.rs
include!("algo_parallel.rs");

use std::collections::{HashSet};
use std::hash::{Hash, Hasher};
use std::collections::hash_map::DefaultHasher;
use std::time::Instant;
use std::thread;

fn hash_vec(v: &Vec<i32>) -> u64 {
    let mut hasher = DefaultHasher::new();
    v.hash(&mut hasher);
    hasher.finish()
}

// Build some graphs for testing
fn graph_single_edge() -> (Graph, i32) {
    let mut g = Graph::new();
    g.add_edge(1, 2);
    (g, 1)
}

fn graph_chain(n: i32) -> (Graph, i32) {
    let mut g = Graph::new();
    for i in 0..(n-1) {
        g.add_edge(i, i+1);
    }
    (g, 0)
}

fn graph_star(center: i32, leaves: i32) -> (Graph, i32) {
    let mut g = Graph::new();
    for i in 1..=leaves { g.add_edge(center, i); }
    (g, center)
}

// Simple deterministic xorshift rng
#[derive(Clone)]
struct XorShift64 { state: u64 }
impl XorShift64 {
    fn new(seed: u64) -> Self { Self { state: seed.max(1) } }
    fn next_u32(&mut self) -> u32 {
        let mut x = self.state;
        x ^= x << 13; x ^= x >> 7; x ^= x << 17;
        self.state = x;
        (x >> 32) as u32
    }
    fn gen_range(&mut self, lo: i32, hi: i32) -> i32 { // [lo, hi)
        let range = (hi - lo) as u32;
        lo + (self.next_u32() % range) as i32
    }
}

fn make_random_graph(n: i32, extras_per_node: usize, seed: u64) -> (Graph, i32) {
    let mut g = Graph::new();
    let mut rng = XorShift64::new(seed);
    // Keep a set of edges to avoid duplicates (undirected)
    let mut edges: HashSet<(i32,i32)> = HashSet::new();

    // Ensure connectivity via ring
    for i in 0..n {
        let j = (i + 1) % n;
        let a = i.min(j); let b = i.max(j);
        if edges.insert((a,b)) { g.add_edge(i, j); }
    }

    // Add extra random edges
    for i in 0..n {
        let mut added = 0usize;
        while added < extras_per_node {
            let j = rng.gen_range(0, n);
            if j == i { continue; }
            let a = i.min(j); let b = i.max(j);
            if edges.insert((a,b)) { g.add_edge(i, j); added += 1; }
        }
    }

    (g, 0)
}

fn run_parity_and_determinism() -> Result<String, String> {
    let mut report = String::new();
    let mut case_id = 1;

    // Edge: empty graph
    {
        let g = Graph::new();
        let start = 42;
        let seq = Bfs::run_seq(&g, start);
        let par1 = Bfs::run(&g, start);
        let par2 = Bfs::run(&g, start);
        if seq != par1 || par1 != par2 { return Err(format!("Case {} failed: empty graph", case_id)); }
        report.push_str(&format!("case {}: empty ok, hash={}\n", case_id, hash_vec(&par1)));
        case_id += 1;
    }

    // Edge: start not present
    {
        let mut g = Graph::new();
        g.add_edge(1,2); g.add_edge(2,3);
        let start = 99;
        let seq = Bfs::run_seq(&g, start);
        let par1 = Bfs::run(&g, start);
        let par2 = Bfs::run(&g, start);
        if seq != par1 || par1 != par2 { return Err(format!("Case {} failed: start missing", case_id)); }
        report.push_str(&format!("case {}: start-missing ok, hash={}\n", case_id, hash_vec(&par1)));
        case_id += 1;
    }

    // Single edge
    {
        let (g, s) = graph_single_edge();
        let seq = Bfs::run_seq(&g, s);
        let par1 = Bfs::run(&g, s);
        let par2 = Bfs::run(&g, s);
        if seq != par1 || par1 != par2 { return Err(format!("Case {} failed: single edge", case_id)); }
        report.push_str(&format!("case {}: single-edge ok, hash={}\n", case_id, hash_vec(&par1)));
        case_id += 1;
    }

    // Chain
    {
        let (g, s) = graph_chain(10);
        let seq = Bfs::run_seq(&g, s);
        let par1 = Bfs::run(&g, s);
        let par2 = Bfs::run(&g, s);
        if seq != par1 || par1 != par2 { return Err(format!("Case {} failed: chain", case_id)); }
        report.push_str(&format!("case {}: chain ok, hash={}\n", case_id, hash_vec(&par1)));
        case_id += 1;
    }

    // Star
    {
        let (g, s) = graph_star(0, 20);
        let seq = Bfs::run_seq(&g, s);
        let par1 = Bfs::run(&g, s);
        let par2 = Bfs::run(&g, s);
        if seq != par1 || par1 != par2 { return Err(format!("Case {} failed: star", case_id)); }
        report.push_str(&format!("case {}: star ok, hash={}\n", case_id, hash_vec(&par1)));
        case_id += 1;
    }

    // Random small
    for trial in 0..5u64 {
        let (g, s) = make_random_graph(50, 3, 1234 + trial);
        let seq = Bfs::run_seq(&g, s);
        let par1 = Bfs::run(&g, s);
        let par2 = Bfs::run(&g, s);
        if seq != par1 || par1 != par2 { return Err(format!("Case {} failed: random small {}", case_id, trial)); }
        report.push_str(&format!("case {}: random-small-{} ok, hash={}\n", case_id, trial, hash_vec(&par1)));
        case_id += 1;
    }

    // Random medium
    for trial in 0..3u64 {
        let (g, s) = make_random_graph(1000, 4, 4321 + trial);
        let seq = Bfs::run_seq(&g, s);
        let par1 = Bfs::run(&g, s);
        let par2 = Bfs::run(&g, s);
        if seq != par1 || par1 != par2 { return Err(format!("Case {} failed: random medium {}", case_id, trial)); }
        report.push_str(&format!("case {}: random-medium-{} ok, hash={}\n", case_id, trial, hash_vec(&par1)));
        case_id += 1;
    }

    Ok(report)
}

fn run_perf() -> String {
    let mut out = String::new();
    let n = 20000i32;
    let extras_per_node = 4usize;

    let (g, s) = make_random_graph(n, extras_per_node, 7777);

    let workers = match thread::available_parallelism() { Ok(n) => n.get(), Err(_) => 4 };

    // Warmup runs
    let _ = Bfs::run_seq(&g, s);
    let _ = Bfs::run(&g, s);

    let t0 = Instant::now();
    let seq = Bfs::run_seq(&g, s);
    let t1 = Instant::now();
    let par = Bfs::run(&g, s);
    let t2 = Instant::now();

    let dt_seq = (t1 - t0).as_secs_f64();
    let dt_par = (t2 - t1).as_secs_f64();
    let speedup = dt_seq / dt_par.max(1e-9);

    out.push_str(&format!(
        "PERF n={} extras_per_node={} workers={} t_seq={:.6} t_par={:.6} speedup={:.3} equal={}\n",
        n, extras_per_node, workers, dt_seq, dt_par, speedup, (seq==par)
    ));
    out
}

fn main() {
    let mut any_error = false;

    match run_parity_and_determinism() {
        Ok(report) => {
            println!("TEST SUMMARY: PASS\n{}", report);
        }
        Err(e) => {
            any_error = true;
            eprintln!("TEST SUMMARY: FAIL\n{}", e);
        }
    }

    let perf = run_perf();
    println!("{}", perf);

    if any_error { std::process::exit(1); }
}
