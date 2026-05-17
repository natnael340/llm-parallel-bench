mod algo_parallel;

use std::collections::hash_map::DefaultHasher;
use std::hash::{Hash, Hasher};
use std::time::Instant;
use algo_parallel::SmithWaterman;


fn get_hash<T: Hash>(t: &T) -> u64 {
    let mut s = DefaultHasher::new();
    t.hash(&mut s);
    s.finish()
}

// Custom comparison for AlignmentResult, ignoring float differences for correctness check
fn compare_results(res1: &algo_parallel::AlignmentResult, res2: &algo_parallel::AlignmentResult) -> bool {
    res1.score == res2.score &&
    res1.aligned_a == res2.aligned_a &&
    res1.aligned_b == res2.aligned_b
}

// Hash implementation for parallel result to check determinism
impl Hash for algo_parallel::AlignmentResult {
    fn hash<H: Hasher>(&self, state: &mut H) {
        self.aligned_a.hash(state);
        self.aligned_b.hash(state);
        self.score.hash(state);
        // Do not hash the float for determinism check
    }
}


fn main() {
    let sw = SmithWaterman::new(3, -3, -2);

    let test_cases = vec![
        ("".to_string(), "".to_string(), "Empty"),
        ("A".to_string(), "".to_string(), "Empty B"),
        ("".to_string(), "B".to_string(), "Empty A"),
        ("A".to_string(), "A".to_string(), "Single Match"),
        ("A".to_string(), "B".to_string(), "Single Mismatch"),
        ("AGCT".to_string(), "AGCT".to_string(), "Small Exact"),
        ("AGCT".to_string(), "TGCA".to_string(), "Small Mismatch"),
        ("GATTACA".to_string(), "GCATGCU".to_string(), "Medium"),
        ("THISISALONGERSEQUENCE".to_string(), "THISISABETTERSEQUENCE".to_string(), "Longer"),
        ("THEQUICKBROWNFOXJUMPSOVERTHELAZYDOG".to_string(), "THEFASTREDFOXJUMPSOVERTHELAZYCAT".to_string(), "Large"),
    ];

    let mut all_correct = true;
    let mut all_deterministic = true;
    let mut summary = String::new();
    summary.push_str("--- Differential Test Summary ---\n");

    for (query, reference, name) in &test_cases {
        println!("--- Testing Case: {} ---", name);
        summary.push_str(&format!("\n--- Case: {} ---\n", name));
        summary.push_str(&format!("Query: '{}', Reference: '{}'\n", query, reference));

        // Correctness Check
        let seq_result = sw.find_alignment_sequential(query, reference);
        let par_result1 = sw.find_alignment_parallel(query, reference);

        let is_correct = compare_results(&seq_result, &par_result1);
        if is_correct {
            println!("✅ Correctness: PASS");
            summary.push_str("Correctness: PASS\n");
        } else {
            println!("❌ Correctness: FAIL");
            summary.push_str("Correctness: FAIL\n");
            all_correct = false;
        }

        // Determinism Check
        let par_result2 = sw.find_alignment_parallel(query, reference);
        let hash1 = get_hash(&par_result1);
        let hash2 = get_hash(&par_result2);
        
        if hash1 == hash2 {
            println!("✅ Determinism: PASS (Hash: {})", hash1);
            summary.push_str(&format!("Determinism: PASS (Hash1: {}, Hash2: {})\n", hash1, hash2));
        } else {
            println!("❌ Determinism: FAIL (Hash1: {}, Hash2: {})", hash1, hash2);
            summary.push_str(&format!("Determinism: FAIL (Hash1: {}, Hash2: {})\n", hash1, hash2));
            all_deterministic = false;
        }
    }

    // Performance Check on a large-enough case
    let perf_query = "THEQUICKBROWNFOXJUMPSOVERTHELAZYDOG".repeat(10);
    let perf_ref = "THEFASTREDFOXJUMPSOVERTHELAZYCAT".repeat(10);
    let perf_summary: String;

    if perf_query.len() > 100 {
        println!("\n--- Performance Check ---");
        
        let start_seq = Instant::now();
        sw.find_alignment_sequential(&perf_query, &perf_ref);
        let dur_seq = start_seq.elapsed();

        let start_par = Instant::now();
        sw.find_alignment_parallel(&perf_query, &perf_ref);
        let dur_par = start_par.elapsed();
        
        let speedup = if dur_par.as_nanos() > 0 {
            dur_seq.as_secs_f64() / dur_par.as_secs_f64()
        } else {
            f64::INFINITY
        };

        println!("Sequential time: {:?}", dur_seq);
        println!("Parallel time:   {:?}", dur_par);
        println!("Speedup:         {:.2}x", speedup);
        
        perf_summary = format!(
            "--- Performance Summary ---\n\
             N_query: {}\n\
             N_reference: {}\n\
             t_seq: {:?}\n\
             t_par: {:?}\n\
             speedup: {:.2}x\n\
             cores: {}\n",
            perf_query.len(),
            perf_ref.len(),
            dur_seq,
            dur_par,
            speedup,
            rayon::current_num_threads()
        );
    } else {
        perf_summary = "--- Performance Summary ---\nSkipped: Input size is too small.\n".to_string();
    }

    std::fs::write("run_summary.txt", summary).expect("Unable to write summary file");
    std::fs::write("perf.txt", perf_summary).expect("Unable to write perf file");

    if !all_correct || !all_deterministic {
        println!("\n❌ Some tests failed.");
        std::process::exit(1);
    } else {
        println!("\n✅ All tests passed.");
    }
}
