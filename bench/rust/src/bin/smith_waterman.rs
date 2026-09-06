use bench_rust::bench_utils;
use bench_rust::staged::{bench_find_alignment, SmithWaterman};
use std::env;
use std::fs;

fn check(ok: bool, name: &str, failures: &mut i32) {
    println!("{} {}", name, if ok { "passed" } else { "failed" });
    if !ok {
        *failures += 1;
    }
}

fn test_case(name: &str, query: &str, reference: &str, exp_a: &str, exp_b: &str,
             exp_score: i32, exp_identity: f64, failures: &mut i32) {
    let sw = SmithWaterman::new(2, -1, -1);
    let (a, b, score, identity) = bench_find_alignment(&sw, query, reference);
    let ok = a == exp_a && b == exp_b && score == exp_score && (identity - exp_identity).abs() <= 1e-6;
    if !ok {
        println!("  got: a={} b={} score={} identity={}", a, b, score, identity);
    }
    check(ok, name, failures);
}

fn read_sw_input() -> Option<(String, String, i32, f64)> {
    let path = env::var("SW_INPUT").ok()?;
    let content = fs::read_to_string(&path).ok()?;
    let lines: Vec<&str> = content.lines().collect();
    if lines.len() < 4 {
        return None;
    }
    let score = lines[2].trim().parse().ok()?;
    let identity = lines[3].trim().parse().ok()?;
    Some((lines[0].trim().to_string(), lines[1].trim().to_string(), score, identity))
}

fn main() {
    let mut failures = 0;

    test_case("test_perfect_match", "ACGT", "ACGT", "ACGT", "ACGT", 8, 100.0, &mut failures);
    test_case("test_no_match", "AAAA", "TTTT", "", "", 0, 0.0, &mut failures);
    test_case("test_partial_match", "ACGTACGT", "TACGTGCA", "TACGT", "TACGT", 10, 100.0, &mut failures);
    test_case("test_gap_in_query", "ACGT", "ACAGT", "AC-GT", "ACAGT", 7, 80.0, &mut failures);
    test_case("test_gap_in_reference", "ACAGT", "ACGT", "ACAGT", "AC-GT", 7, 80.0, &mut failures);
    test_case("test_single_char_match", "A", "A", "A", "A", 2, 100.0, &mut failures);

    let input = read_sw_input();
    if let Some((ref query, ref reference, exp_score, exp_identity)) = input {
        let sw = SmithWaterman::new(2, -1, -1);
        let (a, b, score, identity) = bench_find_alignment(&sw, query, reference);
        let ok = a.len() == b.len() && score == exp_score && (identity - exp_identity).abs() <= 1e-6;
        check(ok, "test_large_sequences_from_file", &mut failures);
    }

    if failures > 0 {
        println!("{} test(s) failed — skipping benchmark", failures);
        std::process::exit(1);
    }

    let (query, reference) = match input {
        Some((q, r, _, _)) => (q, r),
        None => {
            println!("SW_INPUT not set — skipping benchmark");
            return;
        }
    };

    let sw = SmithWaterman::new(2, -1, -1);
    let reps = bench_utils::reps(5);
    let iters = bench_utils::iters(1);
    let r = bench_utils::run_benchmark(|| { bench_find_alignment(&sw, &query, &reference); }, reps, iters, 1);

    println!("{}", bench_utils::format_result("SW large sequences", &r));
    let params = format!("{{\"query_len\": {}, \"reference_len\": {}}}", query.len(), reference.len());
    bench_utils::write_result(&r, "smith-waterman", &bench_utils::impl_name(), &params);
}
